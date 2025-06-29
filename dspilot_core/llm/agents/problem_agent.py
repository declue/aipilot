import logging
from typing import Any, Callable, Dict, Optional

from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.workflow.workflow_utils import get_workflow

logger = logging.getLogger(__name__)


class ProblemAgent(BaseAgent):
    """복잡한 문제 해결 전용 에이전트.

    • 모드(basic / workflow / mcp_tools / research 등)에 따라 적절한 워크플로우를 동적으로
      선택·실행한다.
    • 기존 `UnifiedAgent` 의 모든 기능을 그대로 흡수했으며, 앞으로는 이 클래스를 직접
      사용한다. (UnifiedAgent는 완전히 제거됨)
    """

    def __init__(self, config_manager: Any, mcp_tool_manager: Optional[Any] = None) -> None:
        super().__init__(config_manager, mcp_tool_manager)

        # 모드 → 워크플로우 매핑 (필요 시 확장 가능)
        self._mode_to_workflow = {
            "basic": "basic_chat",
            "mcp_tools": "smart",
            "workflow": "smart",
            "research": "research",
            "auto": "smart",  # 기본 자동 모드
        }

        # 에이전트 상태
        self._interaction_mode = True
        self._workflow_cache: Dict[str, Any] = {}

        logger.info("ProblemAgent 초기화 완료 – 범용 문제 해결 모드")

    # ------------------------------------------------------------------
    # 메인 진입점 ---------------------------------------------------------
    # ------------------------------------------------------------------
    async def generate_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """사용자 메시지 처리 – 선택된 워크플로우에 위임"""
        try:
            logger.info("=== ProblemAgent: 처리 시작 ===")

            # 1) 메시지 기록
            self.add_user_message(user_message)

            # 2) 워크플로우 선택·실행
            workflow = self._select_and_create_workflow()
            logger.info("=== 워크플로우 실행: %s ===", type(workflow).__name__)

            result = await workflow.run(self, user_message, streaming_callback)

            logger.info("=== 처리 완료: %d자 응답 ===", len(str(result)))

            return self._create_response_data(
                result,
                reasoning="워크플로우 처리 완료",
                used_tools=getattr(workflow, "used_tools", []),
            )

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("ProblemAgent 처리 중 오류: %s", exc, exc_info=True)
            return self._create_error_response("요청 처리 중 오류가 발생했습니다", str(exc))

    # ------------------------------------------------------------------
    # 워크플로우 선택 / 캐싱 --------------------------------------------
    # ------------------------------------------------------------------
    def _select_and_create_workflow(self) -> Any:
        """현재 모드에 맞는 워크플로우 인스턴스를 캐싱하여 반환"""
        mode = self._get_llm_mode()
        workflow_name = self._mode_to_workflow.get(mode, "basic_chat")

        # 설정에서 명시적으로 워크플로우 지정 시 우선
        if getattr(self.llm_config, "workflow", None):
            workflow_name = self.llm_config.workflow

        logger.info("선택된 워크플로우: %s (모드: %s)", workflow_name, mode)

        cache_key = f"{workflow_name}_{mode}"
        if cache_key in self._workflow_cache:
            return self._workflow_cache[cache_key]

        # 워크플로우 생성
        workflow_cls = get_workflow(workflow_name)
        workflow_params = self._get_workflow_params(workflow_name)
        workflow = workflow_cls(**workflow_params)

        # 상호작용 모드 전달 (옵션)
        if hasattr(workflow, "set_interaction_mode"):
            workflow.set_interaction_mode(self._interaction_mode)

        self._workflow_cache[cache_key] = workflow
        return workflow

    def _get_workflow_params(self, workflow_name: str) -> Dict[str, Any]:
        """워크플로우별 초기화 파라미터 설정"""
        params: Dict[str, Any] = {}

        if workflow_name in {"agent", "research", "smart"}:
            params.update(
                {
                    "llm_service": self.llm_service,
                    "mcp_tool_manager": self.mcp_tool_manager,
                }
            )
        # 추가 워크플로우는 여기에 if/elif 로 확장
        return params

    # ------------------------------------------------------------------
    # 옵션 설정 · 유틸 ----------------------------------------------------
    # ------------------------------------------------------------------
    def set_interaction_mode(self, interactive: bool) -> None:
        """도구 실행 전 사용자 승인 여부 같은 인터랙션 모드 설정"""
        self._interaction_mode = interactive
        logger.info("상호작용 모드 설정: %s", interactive)

        for workflow in self._workflow_cache.values():
            if hasattr(workflow, "set_interaction_mode"):
                workflow.set_interaction_mode(interactive)

    def clear_workflow_cache(self) -> None:
        """캐시된 워크플로우 객체 제거"""
        self._workflow_cache.clear()
        logger.info("워크플로우 캐시 초기화 완료")

    def get_supported_workflows(self) -> list[str]:
        """지원되는 워크플로우 이름 리스트"""
        return list(self._mode_to_workflow.values())

    def is_available(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # 리소스 정리 --------------------------------------------------------
    # ------------------------------------------------------------------
    async def cleanup(self) -> None:  # noqa: D401
        try:
            for wf in self._workflow_cache.values():
                if hasattr(wf, "cleanup"):
                    await wf.cleanup()
            self.clear_workflow_cache()
            await super().cleanup()
            logger.info("ProblemAgent 정리 완료")
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("정리 중 오류: %s", exc) 