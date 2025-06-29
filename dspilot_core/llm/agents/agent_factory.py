import logging
from typing import Any, Optional

from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.agents.unified_agent import UnifiedAgent

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Agent Factory 모듈
    =================

    `AgentFactory` 는 설정(ConfigManager) 내용을 읽어 현재 실행 맥락에 가장
    적합한 `BaseAgent` 서브클래스를 **동적으로 선택**하여 반환합니다.

    현재 구현은 의사 결정 복잡도를 `UnifiedAgent` 내부로 이동시켜
    팩토리에서 단순 생성만 수행하지만, 다음과 같은 확장 포인트를 제공합니다.

    1. **전략 추가** : `mode` 값에 따라 별도 Agent 클래스를 매핑.
    2. **캐싱/싱글턴** : 동일 설정 조합에 대해 Agent 인스턴스 재사용.
    3. **DI 컨테이너 연동** : 외부 의존성 주입 프레임워크와 통합.

    사용 예시
    ---------
    ```python
    config_manager = ConfigManager()
    agent = AgentFactory.create_agent(config_manager, mcp_tool_manager)
    response = await agent.process("안녕?")
    ```
    """

    @staticmethod
    def create_agent(config_manager: Any, mcp_tool_manager: Optional[Any] = None) -> BaseAgent:
        """UnifiedAgent를 생성합니다 (모든 처리는 Workflow에 위임)"""
        try:
            # 설정에서 모드 가져오기
            llm_config = config_manager.get_llm_config()
            mode = llm_config.get("mode", "basic").lower()

            logger.info("UnifiedAgent 생성: mode=%s", mode)

            # 항상 UnifiedAgent 반환 (내부에서 워크플로우 선택)
            agent = UnifiedAgent(config_manager, mcp_tool_manager)
            logger.info("UnifiedAgent 생성 완료")
            return agent

        except Exception as e:
            logger.error("Agent 생성 중 오류: %s", e)
            # 오류 시에도 UnifiedAgent 반환 (기본 워크플로우로 처리)
            return UnifiedAgent(config_manager, mcp_tool_manager)
