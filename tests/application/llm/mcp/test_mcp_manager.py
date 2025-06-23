# pylint: disable=redefined-outer-name

import pytest

from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.models.mcp_server import MCPServer


class DummyConfigManager:  # pylint: disable=too-few-public-methods
    """MCPManager 테스트용 더미 ConfigManager"""

    def __init__(self, mcp_config_data: dict | None = None):
        self._mcp_config_data = mcp_config_data or {
            "mcpServers": {
                "test_server": {
                    "command": "echo",
                    "args": ["hello"],
                    "env": {},
                    "description": "테스트 서버",
                    "enabled": True
                },
                "disabled_server": {
                    "command": "echo", 
                    "args": ["world"],
                    "env": {},
                    "description": "비활성화 서버",
                    "enabled": False
                }
            },
            "enabled": True
        }

    def get_mcp_config(self):  # noqa: D401, pylint: disable=missing-function-docstring
        return self._mcp_config_data


@pytest.fixture()
def mcp_manager():  # noqa: D401
    """MCP 설정이 있는 MCPManager 픽스처"""
    dummy_cfg = DummyConfigManager()
    return MCPManager(config_manager=dummy_cfg)


@pytest.fixture()
def empty_mcp_manager():  # noqa: D401
    """빈 설정으로 초기화된 MCPManager 픽스처"""
    dummy_cfg = DummyConfigManager({"mcpServers": {}, "enabled": True})
    return MCPManager(config_manager=dummy_cfg)


def test_mcp_server_model():
    """MCPServer 모델 생성 테스트"""
    # 정상적인 서버 생성
    server = MCPServer(
        name="test_server",
        command="echo",
        args=["hello"],
        env={"TEST": "value"},
        description="테스트 서버",
        enabled=True
    )
    
    assert server.name == "test_server"
    assert server.command == "echo"
    assert server.args == ["hello"]
    assert server.env == {"TEST": "value"}
    assert server.description == "테스트 서버"
    assert server.enabled is True
    
    # 전체 명령 테스트
    assert server.get_full_command() == ["echo", "hello"]
    
    # from_dict 테스트
    server_data = {
        "command": "python",
        "args": ["-m", "test"],
        "env": {},
        "description": "Python 테스트",
        "enabled": True
    }
    server_from_dict = MCPServer.from_dict("python_server", server_data)
    assert server_from_dict.name == "python_server"
    assert server_from_dict.command == "python"
    assert server_from_dict.args == ["-m", "test"]


def test_mcp_manager_initialization(mcp_manager):
    """MCPManager 초기화 테스트"""
    assert mcp_manager is not None
    assert mcp_manager.config_manager is not None
    assert mcp_manager.is_mcp_enabled() is True


def test_get_enabled_servers(mcp_manager):
    """활성화된 서버 목록 조회 테스트"""
    enabled_servers = mcp_manager.get_enabled_servers()
    
    # test_server는 활성화되어 있어야 함
    assert "test_server" in enabled_servers
    assert enabled_servers["test_server"].enabled is True
    assert enabled_servers["test_server"].command == "echo"
    
    # disabled_server는 비활성화되어 있으므로 목록에 없어야 함
    assert "disabled_server" not in enabled_servers


def test_get_enabled_servers_empty(empty_mcp_manager):
    """빈 설정에서 활성화된 서버 목록 테스트"""
    enabled_servers = empty_mcp_manager.get_enabled_servers()
    assert len(enabled_servers) == 0


@pytest.mark.asyncio
async def test_server_connection_test(mcp_manager):
    """서버 연결 테스트"""
    # 존재하는 서버 테스트
    status = await mcp_manager.test_server_connection("test_server")
    assert status.server_name == "test_server"
    assert status.connected is True
    assert status.error_message is None
    assert len(status.tools) > 0
    
    # 존재하지 않는 서버 테스트  
    status = await mcp_manager.test_server_connection("nonexistent_server")
    assert status.server_name == "nonexistent_server"
    assert status.connected is False
    assert "찾을 수 없습니다" in status.error_message


@pytest.mark.asyncio
async def test_server_status_management(mcp_manager):
    """서버 상태 관리 테스트"""
    # 초기에는 상태가 없어야 함
    assert mcp_manager.get_server_status("test_server") is None
    
    # 연결 테스트 후 상태가 저장되어야 함
    await mcp_manager.test_server_connection("test_server")
    status = mcp_manager.get_server_status("test_server")
    assert status is not None
    assert status.server_name == "test_server"
    
    # 모든 서버 상태 조회
    all_statuses = mcp_manager.get_all_server_statuses()
    assert "test_server" in all_statuses


@pytest.mark.asyncio
async def test_refresh_all_servers(mcp_manager):
    """모든 서버 상태 갱신 테스트"""
    # 초기에는 상태가 없어야 함
    assert len(mcp_manager.get_all_server_statuses()) == 0
    
    # 모든 서버 갱신
    await mcp_manager.refresh_all_servers()
    
    # 활성화된 서버의 상태가 갱신되어야 함
    all_statuses = mcp_manager.get_all_server_statuses()
    assert "test_server" in all_statuses
    assert "disabled_server" not in all_statuses  # 비활성화된 서버는 제외


def test_mcp_config_access(mcp_manager):
    """MCP 설정 접근 테스트"""
    mcp_config = mcp_manager.get_mcp_config()
    assert mcp_config is not None
    assert mcp_config.enabled is True
    
    enabled_servers_from_config = mcp_config.get_enabled_servers()
    assert "test_server" in enabled_servers_from_config
    assert "disabled_server" not in enabled_servers_from_config 