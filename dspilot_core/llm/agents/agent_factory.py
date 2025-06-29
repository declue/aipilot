import logging
from typing import Any, Optional

from dspilot_core.llm.agents.ask_agent import AskAgent
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.agents.problem_agent import ProblemAgent

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Agent Factory 모듈
    =================

    `AgentFactory` 는 설정(ConfigManager) 내용을 읽어 현재 실행 맥락에 가장
    적합한 `BaseAgent` 서브클래스를 **동적으로 선택**하여 반환합니다.

    현재 구현은 의사 결정 복잡도를 `ProblemAgent` 내부로 이동시켜
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
    def create_agent(
        config_manager: Any,
        mcp_tool_manager: Optional[Any] = None,
        agent_type: str = "problem",
    ) -> BaseAgent:
        """AskAgent 또는 ProblemAgent 를 생성하여 반환한다.

        Args:
            config_manager: 설정 매니저
            mcp_tool_manager: MCP 도구 매니저
            agent_type: "ask" 또는 "problem" (대소문자 무관). 기본값은 problem.
        """
        try:
            atype = str(agent_type or "problem").lower()

            if atype in ("ask", "basic"):
                logger.info("AskAgent 생성 (type=%s)", atype)
                return AskAgent(config_manager, mcp_tool_manager)

            # default → ProblemAgent
            logger.info("ProblemAgent 생성 (type=%s)", atype)
            return ProblemAgent(config_manager, mcp_tool_manager)

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Agent 생성 중 오류 – ProblemAgent 폴백: %s", exc)
            return ProblemAgent(config_manager, mcp_tool_manager)
