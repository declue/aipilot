import logging
from typing import Any, Optional

from application.llm.agents.base_agent import BaseAgent
from application.llm.agents.basic_agent import BasicAgent
from application.llm.agents.react_agent import ReactAgent
from application.llm.agents.workflow_agent import WorkflowAgent

logger = logging.getLogger(__name__)


class AgentFactory:
    """Agent 생성 팩토리"""

    @staticmethod
    def create_agent(config_manager: Any, mcp_tool_manager: Optional[Any] = None) -> BaseAgent:
        """설정에 따라 적절한 Agent를 생성합니다."""
        try:
            # 설정에서 모드 가져오기
            llm_config = config_manager.get_llm_config()
            mode = llm_config.get("mode", "basic").lower()

            logger.info(f"Agent 생성: mode={mode}")

            if mode == "mcp_tools":
                agent = ReactAgent(config_manager, mcp_tool_manager)
                if agent.is_available():
                    return agent
                else:
                    logger.warning("ReAct Agent를 사용할 수 없어 Basic Agent로 폴백")
                    return BasicAgent(config_manager, mcp_tool_manager)

            elif mode == "workflow":
                return WorkflowAgent(config_manager, mcp_tool_manager)

            else:  # 'basic' or any other mode
                return BasicAgent(config_manager, mcp_tool_manager)

        except Exception as e:
            logger.error(f"Agent 생성 중 오류: {e}, Basic Agent로 폴백")
            return BasicAgent(config_manager, mcp_tool_manager)
