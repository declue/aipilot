import logging
from typing import Any, Callable, Dict, Optional

from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.workflow.workflow_utils import get_workflow

logger = logging.getLogger(__name__)


class UnifiedAgent(BaseAgent):
    """
    통합 Agent - 모든 처리를 Workflow에 위임
    Agent는 공통 기능(메시지 관리, LLM 설정 등)만 담당하고
    실제 처리 로직은 모두 Workflow에서 수행
    """

    def __init__(self, config_manager: Any, mcp_tool_manager: Optional[Any] = None) -> None:
        super().__init__(config_manager, mcp_tool_manager)
        self._mode_to_workflow = {
            "basic": "basic_chat",
            "mcp_tools": "agent", 
            "workflow": "agent",
            "research": "research"
        }

    async def generate_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """모든 처리를 Workflow에 위임"""
        try:
            logger.info("=== UnifiedAgent: 워크플로우 위임 처리 시작 ===")
            
            # 사용자 메시지 추가
            self.add_user_message(user_message)
            
            # 모드에 따른 워크플로우 선택
            mode = self._get_llm_mode()
            workflow_name = self._mode_to_workflow.get(mode, "basic_chat")
            
            # 설정에서 명시적으로 지정된 워크플로우가 있다면 우선 사용
            if hasattr(self.llm_config, 'workflow') and self.llm_config.workflow:
                workflow_name = self.llm_config.workflow
            
            logger.info(f"=== 선택된 워크플로우: {workflow_name} (모드: {mode}) ===")
            
            # 워크플로우 실행
            workflow_class = get_workflow(workflow_name)
            
            # 워크플로우에 필요한 파라미터 전달
            if workflow_name == "agent":
                # AgentWorkflow는 llm_service와 mcp_tool_manager가 필요
                workflow = workflow_class(
                    llm_service=self.llm_service, 
                    mcp_tool_manager=self.mcp_tool_manager
                )
            else:
                # 다른 워크플로우들은 기본 생성
                workflow = workflow_class()
            
            logger.info(f"=== 워크플로우 실행 시작: {type(workflow).__name__} ===")
            
            result = await workflow.run(self, user_message, streaming_callback)
            
            logger.info(f"=== 워크플로우 실행 완료: {len(str(result))}자 응답 ===")
            
            return self._create_response_data(
                result,
                reasoning=f"워크플로우 실행: {workflow_name}",
                used_tools=[workflow_name]
            )
            
        except Exception as e:
            logger.error(f"UnifiedAgent 처리 중 오류: {e}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return self._create_error_response(
                "요청 처리 중 오류가 발생했습니다", 
                str(e)
            )

    def is_available(self) -> bool:
        """항상 사용 가능 (워크플로우에서 개별 확인)"""
        return True 