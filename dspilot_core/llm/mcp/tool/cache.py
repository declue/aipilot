"""Legacy ToolCache shim for tests."""


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
