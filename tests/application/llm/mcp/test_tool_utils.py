"""MCP Tool 관련 유틸리티 테스트

pytest -q tests/application/llm/mcp/test_tool_utils.py
"""

from types import SimpleNamespace
from typing import Any, Dict, List

from application.llm.mcp.mcp_tool_manager import MCPToolManager
from application.llm.mcp.tool.cache import ToolCache
from application.llm.mcp.tool.converter import ToolConverter

# pytest 는 현재 파일에서 직접 사용되지 않지만, 향후 테스트 확장을 위해 남겨둘 수 있습니다.


# ---------------------------------------------------------------------------
# 더미 객체들과 헬퍼
# ---------------------------------------------------------------------------


class _DummyStatus:  # pylint: disable=too-few-public-methods
    """MCPServerStatus를 대체하는 간단한 스텁."""

    def __init__(self, connected: bool, tools: List[Dict[str, Any]]):
        self.connected = connected
        self.tools = tools


class _DummyMCPManager:  # pylint: disable=too-few-public-methods
    """실제 MCPManager 로직을 최소화한 스텁."""

    def __init__(self, servers: Dict[str, Any]):
        self._servers = servers

    # 필요한 메서드만 구현 -----------------------------------------------------
    def get_enabled_servers(self):  # noqa: D401
        return self._servers

    async def test_server_connection(self, server_name: str):  # noqa: D401
        server = self._servers[server_name]
        return _DummyStatus(True, server.tools)  # type: ignore[attr-defined]


class _DummyConfigManager:  # pylint: disable=too-few-public-methods
    """OpenAI 연동을 막기 위한 최소 ConfigManager 스텁."""

    def get_llm_config(self):  # noqa: D401
        return {"api_key": "test", "base_url": "https://test.invalid", "model": "gpt-3.5-turbo"}


# ---------------------------------------------------------------------------
# 테스트 케이스
# ---------------------------------------------------------------------------

def test_tool_cache_add_and_get():
    cache = ToolCache()
    cache.add("server_tool", "server", "tool", {"description": "desc"})

    assert "server_tool" in cache
    stored = cache.get("server_tool")
    assert stored["server_name"] == "server"
    assert stored["tool_name"] == "tool"


def test_tool_converter_schema_and_description():
    converter = ToolConverter()

    # 빈 스키마 → query 요구
    result = converter.convert_schema({})
    assert result["type"] == "object"
    assert "query" in result["properties"]

    # 이미 object/properties 포함 시 그대로 리턴
    schema = {"type": "object", "properties": {"foo": {"type": "string"}}}
    assert converter.convert_schema(schema) == schema

    # description 향상
    desc = converter.enhance_description("github_server", "list_pr", "PR 목록")
    assert "GitHub" in desc or "github" in desc.lower()


def test_mcp_tool_manager_openai_tools():
    import asyncio  # 로컬 import로 의존 최소화

    # 더미 서버/도구 구성
    dummy_tool = {
        "name": "echo",
        "description": "Echo input",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    }

    class _Srv(SimpleNamespace):
        command: str
        args: List[str]
        env: Dict[str, str]
        enabled: bool = True
        tools: List[Dict[str, Any]]

    dummy_server_cfg = _Srv(command="echo", args=[], env={}, tools=[dummy_tool])

    mcp_manager = _DummyMCPManager({"dummy": dummy_server_cfg})
    config_manager = _DummyConfigManager()

    manager = MCPToolManager(mcp_manager, config_manager)

    tools = asyncio.run(manager.get_openai_tools())
    assert len(tools) == 1
    tool_spec = tools[0]
    assert tool_spec["function"]["name"] == "dummy_echo"
    params = tool_spec["function"]["parameters"]
    assert params["properties"]["text"]["type"] == "string" 