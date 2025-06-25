import logging
from typing import Any, Callable, Dict, Optional

from application.llm.agents.base_agent import BaseAgent
from application.llm.workflow.workflow_utils import get_workflow

logger = logging.getLogger(__name__)


class WorkflowAgent(BaseAgent):
    """워크플로우 모드 Agent - 정의된 워크플로우에 따라 처리"""

    async def generate_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """워크플로우 모드로 응답 생성"""
        try:
            logger.info("WorkflowAgent: 워크플로우 모드로 응답 생성 중...")
            
            # 사용자 메시지 추가
            self.add_user_message(user_message)
            
            workflow_name = self.llm_config.workflow or "basic_chat"
            workflow_class = get_workflow(workflow_name)
            workflow = workflow_class()

            result = await workflow.run(self, user_message, streaming_callback)

            return {
                "response": result,
                "workflow": workflow_name,
                "reasoning": "",
                "used_tools": [],
            }

        except Exception as e:
            logger.error(f"WorkflowAgent 워크플로우 처리 중 오류: {e}")
            return {
                "response": "워크플로우 처리 중 문제가 발생했습니다.",
                "workflow": self.llm_config.workflow or "basic_chat",
                "reasoning": str(e),
                "used_tools": [],
            } 