import logging
from typing import Any, Callable, Dict, Optional

from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.workflow.workflow_utils import get_workflow

logger = logging.getLogger(__name__)


class UnifiedAgent(BaseAgent):
    """
    UnifiedAgent 모듈
    =================

    `UnifiedAgent` 는 DSPilot 의 **All-in-One 에이전트** 구현체입니다. 사용자가
    모델 모드( basic / workflow / mcp_tools / research 등) 를 지정하면 내부적으로
    알맞은 워크플로우를 선택하여 LLM 호출, MCP 도구 사용, 검색 등 복합 작업을
    수행합니다.

    디자인 포인트
    -------------
    1. **워크플로우 디스패치** : `mode` → `workflow_name` 매핑 후 `get_workflow()`
        메타 팩토리로 클래스를 가져와 인스턴스화.
    2. **캐싱** : 동일 파라미터로 재호출 시 생성 비용 절감.
    3. **Interaction Mode** : CLI/GUI 상의 *full-auto* 플래그와 연동해 도구 실행 전
        사용자 승인 여부를 워크플로우에 전파.

    시퀀스
    -------
    ```mermaid
    sequenceDiagram
        participant User
        participant UnifiedAgent
        participant Workflow
        participant LLMService
        User->>UnifiedAgent: generate_response(msg)
        UnifiedAgent->>Workflow: run(self, msg)
        Workflow->>LLMService: astream()/ainvoke
        Workflow-->>UnifiedAgent: result
        UnifiedAgent-->>User: formatted response
    ```

    확장 가이드
    -----------
    • 새 워크플로우를 추가하려면 `workflow/workflow_utils.py` 의 등록 함수나
      `get_workflow()` 팩토리에서 이름을 매핑하면 이 Agent 가 자동 인식합니다.
    """

    def __init__(self, config_manager: Any, mcp_tool_manager: Optional[Any] = None) -> None:
        super().__init__(config_manager, mcp_tool_manager)

        # 워크플로우 매핑 (확장 가능)
        self._mode_to_workflow = {
            "basic": "basic_chat",
            "mcp_tools": "agent",
            "workflow": "agent",
            "research": "research",
            "auto": "agent"  # 기본 자동 모드
        }

        # 에이전트 상태
        self._interaction_mode = True
        self._workflow_cache: Dict[str, Any] = {}

        logger.info("UnifiedAgent 초기화 완료 - 범용 에이전트 모드")

    async def generate_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """범용 에이전트의 메인 처리 로직 - 워크플로우에 위임"""
        try:
            logger.info("=== UnifiedAgent: 범용 에이전트 처리 시작 ===")

            # 사용자 메시지 추가
            self.add_user_message(user_message)

            # 워크플로우 선택 및 실행
            workflow = self._select_and_create_workflow()

            logger.info(f"=== 워크플로우 실행: {type(workflow).__name__} ===")

            result = await workflow.run(self, user_message, streaming_callback)

            logger.info(f"=== 처리 완료: {len(str(result))}자 응답 ===")

            return self._create_response_data(
                result,
                reasoning=f"워크플로우 처리 완료",
                used_tools=getattr(workflow, 'used_tools', [])
            )

        except Exception as e:
            logger.error(f"UnifiedAgent 처리 중 오류: {e}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return self._create_error_response(
                "요청 처리 중 오류가 발생했습니다",
                str(e)
            )

    def _select_and_create_workflow(self) -> Any:
        """워크플로우 선택 및 생성 (캐시 지원)"""
        # 모드에 따른 워크플로우 선택
        mode = self._get_llm_mode()
        workflow_name = self._mode_to_workflow.get(mode, "basic_chat")

        # 설정에서 명시적으로 지정된 워크플로우가 있다면 우선 사용
        if hasattr(self.llm_config, 'workflow') and self.llm_config.workflow:
            workflow_name = self.llm_config.workflow

        logger.info(f"선택된 워크플로우: {workflow_name} (모드: {mode})")

        # 캐시된 워크플로우 확인
        cache_key = f"{workflow_name}_{mode}"
        if cache_key in self._workflow_cache:
            return self._workflow_cache[cache_key]

        # 워크플로우 생성
        workflow_class = get_workflow(workflow_name)

        # 워크플로우별 파라미터 설정 (확장 가능)
        workflow_params = self._get_workflow_params(workflow_name)
        workflow = workflow_class(**workflow_params)

        # 상호작용 모드 설정 (if supported)
        if hasattr(workflow, 'set_interaction_mode'):
            workflow.set_interaction_mode(self._interaction_mode)

        # 캐시에 저장
        self._workflow_cache[cache_key] = workflow

        return workflow

    def _get_workflow_params(self, workflow_name: str) -> Dict[str, Any]:
        """워크플로우별 초기화 파라미터 반환"""
        params = {}

        if workflow_name == "agent":
            params.update({
                "llm_service": self.llm_service,
                "mcp_tool_manager": self.mcp_tool_manager
            })
        elif workflow_name == "research":
            params.update({
                "llm_service": self.llm_service,
                "mcp_tool_manager": self.mcp_tool_manager
            })
        # 새로운 워크플로우 타입은 여기에 추가

        return params

    def set_interaction_mode(self, interactive: bool) -> None:
        """상호작용 모드 설정"""
        self._interaction_mode = interactive
        logger.info(f"상호작용 모드 설정: {interactive}")

        # 캐시된 워크플로우들에도 설정 적용
        for workflow in self._workflow_cache.values():
            if hasattr(workflow, 'set_interaction_mode'):
                workflow.set_interaction_mode(interactive)

    def clear_workflow_cache(self) -> None:
        """워크플로우 캐시 초기화"""
        self._workflow_cache.clear()
        logger.info("워크플로우 캐시 초기화 완료")

    def get_supported_workflows(self) -> list[str]:
        """지원되는 워크플로우 목록 반환"""
        return list(self._mode_to_workflow.values())

    def is_available(self) -> bool:
        """항상 사용 가능 (범용 에이전트)"""
        return True

    async def cleanup(self) -> None:
        """리소스 정리"""
        try:
            # 캐시된 워크플로우들 정리
            for workflow in self._workflow_cache.values():
                if hasattr(workflow, 'cleanup'):
                    await workflow.cleanup()

            self.clear_workflow_cache()

            # 부모 클래스 정리
            await super().cleanup()

            logger.info("UnifiedAgent 정리 완료")
        except Exception as e:
            logger.error(f"UnifiedAgent 정리 중 오류: {e}")
