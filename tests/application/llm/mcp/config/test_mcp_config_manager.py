# pylint: disable=redefined-outer-name
import json
from pathlib import Path

import pytest

from application.llm.mcp.config.mcp_config_manager import MCPConfigManager
from application.llm.mcp.config.models.mcp_server import MCPServer


@pytest.fixture()
def temp_config_path(tmp_path: Path) -> Path:
    """임시 설정 파일 경로를 제공합니다."""
    return tmp_path / "mcp.json"


def test_create_default_config_when_file_missing(temp_config_path: Path):
    """설정 파일이 없으면 기본 설정이 생성되고 파일이 저장되어야 한다."""
    assert not temp_config_path.exists()

    manager = MCPConfigManager(config_file=str(temp_config_path))

    # 파일이 생성되었는지 확인
    assert temp_config_path.exists()

    # 기본 서버가 설정되었는지 확인
    config = manager.get_config()
    assert config.defaultServer == "test"
    assert "github" in config.mcpServers
    assert "test" in config.mcpServers


def test_add_and_save_server_excludes_runtime_fields(temp_config_path: Path):
    """런타임 필드는 저장 파일에 포함되지 않아야 한다."""
    manager = MCPConfigManager(config_file=str(temp_config_path))

    new_server = MCPServer(
        command="echo",
        args=["hello"],
        env={"KEY": "VALUE"},
        description="테스트 서버",
        enabled=True,
        connected=True,  # 런타임 필드
        tools=[{"name": "tool"}],  # 런타임 필드
        resources=[{"r": 1}],  # 런타임 필드
        prompts=[{"p": 1}],  # 런타임 필드
    )

    manager.add_server("test_server", new_server)

    # 저장된 JSON 확인
    with open(temp_config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    saved_server = data["mcpServers"]["test_server"]
    # 런타임 필드가 제거되었는지 확인
    assert "connected" not in saved_server
    assert "tools" not in saved_server
    assert "resources" not in saved_server
    assert "prompts" not in saved_server


def test_set_and_remove_default_server(temp_config_path: Path):
    """기본 서버 설정 및 제거 동작을 검증한다."""
    manager = MCPConfigManager(config_file=str(temp_config_path))

    # 새로운 서버 추가 및 기본 서버 설정
    sample_server = MCPServer(command="cmd", args=[], env={}, description="desc")
    manager.add_server("alpha", sample_server)
    assert manager.set_default_server("alpha") is True
    assert manager.get_config().defaultServer == "alpha"

    # 기본 서버 제거 시 defaultServer 가 None 또는 다른 서버로 변경되는지 테스트
    manager.remove_server("alpha")
    assert manager.get_config().defaultServer != "alpha"
