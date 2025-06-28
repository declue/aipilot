"""Legacy LLMAgent shim."""

try:
    from dspilot_core.llm.agents.base_agent import BaseAgent as LLMAgent  # type: ignore
except Exception:  # pragma: no cover
    class LLMAgent:  # type: ignore
        """간소화된 테스트용 LLMAgent 스텁 (BaseAgent 로드 실패 시)"""

        def __init__(self, *args, **kwargs):
            self.config_manager = args[0] if args else None
            self.mcp_tool_manager = args[1] if len(args) > 1 else None
            self.history = []
            self._client = None

        def add_user_message(self, message):  # noqa: D401
            self.history.append({"role": "user", "content": message})

        def add_assistant_message(self, message):  # noqa: D401
            self.history.append({"role": "assistant", "content": message})

        def clear_conversation(self):  # noqa: D401
            self.history.clear()

        def reinitialize_client(self):  # noqa: D401
            self._client = None
