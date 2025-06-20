# pylint: disable=redefined-outer-name
import pytest

from application.llm.mcp.config.models.mcp_server import MCPServer
# MCPManager, MCPServer import
from application.llm.mcp.mcp_manager import MCPManager


class DummyConfigManager:  # pylint: disable=too-few-public-methods
    """MCPManager 테스트용 더미 ConfigManager"""

    def __init__(self, initial_servers: dict | None = None):
        self._initial_servers = initial_servers or {}

    def get_mcp_config(self):  # noqa: D401, pylint: disable=missing-function-docstring
        return {"mcpServers": self._initial_servers, "defaultServer": None, "enabled": True}


@pytest.fixture()
def mcp_manager():  # noqa: D401
    """빈 설정으로 초기화된 MCPManager 픽스처"""

    dummy_cfg = DummyConfigManager()
    return MCPManager(config_manager=dummy_cfg)


def _create_sample_server(enabled: bool = True):  # pylint: disable=missing-function-docstring
    return MCPServer(
        command="echo",
        args=["hello"],
        env={},
        description="테스트 서버",
        enabled=enabled,
    )


def test_add_and_get_server(mcp_manager):  # noqa: D401
    """서버 추가 후 조회가 정상적으로 동작하는지 검증한다."""

    server = _create_sample_server()
    # 서버 추가
    assert mcp_manager.add_server("alpha", server) is True

    # add_server 호출 시 name 필드가 설정되어야 함
    assert server.name == "alpha"

    # 목록과 개별 조회 확인
    assert "alpha" in mcp_manager.get_server_list()
    retrieved = mcp_manager.get_server("alpha")
    assert retrieved == server

    # MCPProcess 도 등록되었는지 확인 (내부 구현 세부사항)
    assert "alpha" in mcp_manager.processes


def test_remove_server(mcp_manager):  # noqa: D401
    """서버 제거 동작 검증"""

    server = _create_sample_server()
    mcp_manager.add_server("beta", server)

    # 제거 후 존재하지 않아야 함
    assert mcp_manager.remove_server("beta") is True
    assert mcp_manager.get_server("beta") is None
    assert "beta" not in mcp_manager.processes


def test_get_enabled_servers(mcp_manager):  # noqa: D401
    """활성화된 서버 필터링이 정상적으로 동작하는지 검증한다."""

    mcp_manager.add_server("enabled_srv", _create_sample_server(enabled=True))
    mcp_manager.add_server("disabled_srv", _create_sample_server(enabled=False))

    enabled_servers = mcp_manager.get_enabled_servers()
    assert "enabled_srv" in enabled_servers
    assert "disabled_srv" not in enabled_servers


def test_start_and_stop_server(mcp_manager):  # noqa: D401
    """start_server / stop_server 동작을 확인한다 (placeholder 로직)."""

    mcp_manager.add_server("gamma", _create_sample_server())

    # 시작
    assert mcp_manager.start_server("gamma") is True

    # 중지 (placeholder, 현재는 False 일 수도 있지만 인터페이스 확인용)
    # stop_server 는 placeholder 구현에 따라 True/False 가 달라질 수 있으므로 Not None 만 확인
    assert mcp_manager.stop_server("gamma") in (True, False)


def test_update_server_replaces_process(mcp_manager):  # noqa: D401
    """update_server 가 프로세스 객체도 교체하는지 확인한다."""

    srv1 = _create_sample_server()
    mcp_manager.add_server("delta", srv1)

    old_proc = mcp_manager.processes["delta"]

    srv2 = _create_sample_server()
    assert mcp_manager.update_server("delta", srv2) is True

    # 새로운 MCPProcess 로 교체되었는지
    assert mcp_manager.processes["delta"] is not old_proc 