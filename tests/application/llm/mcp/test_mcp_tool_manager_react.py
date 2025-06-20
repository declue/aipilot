import pytest

from application.config.config_manager import ConfigManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager


class DummyMCPManager:  # pylint: disable=too-few-public-methods
    def get_enabled_servers(self):
        return {}

    async def test_server_connection(self, _server_name):  # noqa: D401
        return None


@pytest.mark.asyncio
async def test_run_agent_with_tools_pattern(monkeypatch, tmp_path):
    cfg_path = tmp_path / "app.config"
    cm = ConfigManager(config_file=str(cfg_path))

    mcp_manager = DummyMCPManager()
    tool_manager = MCPToolManager(mcp_manager, cm)

    # monkeypatch call_mcp_tool to avoid real execution
    async def _fake_call(tool_key, args):  # noqa: D401
        assert tool_key == "my_tool"
        assert args == {"arg": "123"}
        return "EXECUTED"

    monkeypatch.setattr(tool_manager, "call_mcp_tool", _fake_call)

    result = await tool_manager.run_agent_with_tools("some text my_tool(arg='123') end")

    assert result["response"] == "EXECUTED"
    assert result["used_tools"] == ["my_tool"] 