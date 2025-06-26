import logging
from typing import Any, Optional

from application.llm.agents.base_agent import BaseAgent
from application.llm.agents.unified_agent import UnifiedAgent

logger = logging.getLogger(__name__)


class AgentFactory:
    """Agent 생성 팩토리 - 단순화된 UnifiedAgent 사용"""

    @staticmethod
    def create_agent(config_manager: Any, mcp_tool_manager: Optional[Any] = None) -> BaseAgent:
        """UnifiedAgent를 생성합니다 (모든 처리는 Workflow에 위임)"""
        try:
            # 설정에서 모드 가져오기
            llm_config = config_manager.get_llm_config()
            mode = llm_config.get("mode", "basic").lower()

            logger.info(f"UnifiedAgent 생성: mode={mode}")

            # 항상 UnifiedAgent 반환 (내부에서 워크플로우 선택)
            agent = UnifiedAgent(config_manager, mcp_tool_manager)
            logger.info("UnifiedAgent 생성 완료")
            return agent

        except Exception as e:
            logger.error(f"Agent 생성 중 오류: {e}")
            # 오류 시에도 UnifiedAgent 반환 (기본 워크플로우로 처리)
            return UnifiedAgent(config_manager, mcp_tool_manager)
