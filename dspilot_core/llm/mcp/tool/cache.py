"""Legacy ToolCache shim for tests."""

try:
    from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolCache as ToolCache  # type: ignore
except Exception:  # pragma: no cover
    # 외부 의존성 부족으로 MCPToolManager를 가져올 수 없을 때 최소 스텁 제공
    class ToolCache:  # type: ignore
        """간소화된 테스트용 ToolCache 스텁"""

        def __init__(self, *_, **__):
            self._cache = {}

        def add(self, tool_key, server_name, tool_name, meta):  # noqa: D401
            self._cache[tool_key] = {
                "server_name": server_name,
                "tool_name": tool_name,
                "meta": meta,
            }

        def get(self, tool_key):  # noqa: D401
            return self._cache.get(tool_key)

        def __contains__(self, key):  # noqa: D401
            return key in self._cache
