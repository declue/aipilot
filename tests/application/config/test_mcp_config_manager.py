import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

from application.config.mcp_config_manager import MCPConfigManager


@pytest.fixture
def temp_mcp_config_file(tmp_path: Path) -> str:
    """임시 MCP 설정 파일 경로 반환"""
    return str(tmp_path / "test_mcp.json")


@pytest.fixture
def mcp_manager(temp_mcp_config_file: str) -> MCPConfigManager:
    """MCPConfigManager 인스턴스 생성"""
    return MCPConfigManager(temp_mcp_config_file)


@pytest.fixture
def sample_server_config() -> dict:
    """샘플 서버 설정 반환"""
    return {
        "command": "python",
        "args": ["server.py", "--port", "8080"],
        "env": {"DEBUG": "true"},
        "timeout": 30
    }


class TestMCPConfigManager:
    """MCP Config Manager 테스트 클래스"""

    def test_initialization_with_new_file(self, temp_mcp_config_file: str):
        """새 파일로 초기화 테스트"""
        manager = MCPConfigManager(temp_mcp_config_file)
        
        # 기본 설정이 생성되었는지 확인
        assert os.path.exists(temp_mcp_config_file)
        config = manager.get_config()
        assert config["mcpServers"] == {}
        assert config["defaultServer"] is None
        assert config["enabled"] is True

    def test_initialization_with_existing_file(self, temp_mcp_config_file: str):
        """기존 파일로 초기화 테스트"""
        # 기존 설정 파일 생성
        existing_config = {
            "mcpServers": {
                "test_server": {
                    "command": "test",
                    "args": ["--test"]
                }
            },
            "defaultServer": "test_server",
            "enabled": False
        }
        
        with open(temp_mcp_config_file, "w", encoding="utf-8") as f:
            json.dump(existing_config, f)
        
        manager = MCPConfigManager(temp_mcp_config_file)
        config = manager.get_config()
        
        assert "test_server" in config["mcpServers"]
        assert config["defaultServer"] == "test_server"
        assert config["enabled"] is False

    def test_default_file_path(self):
        """기본 파일 경로 테스트"""
        manager = MCPConfigManager()
        assert manager.config_file == "mcp.json"

    def test_get_config(self, mcp_manager: MCPConfigManager):
        """전체 설정 반환 테스트"""
        config = mcp_manager.get_config()
        
        assert isinstance(config, dict)
        assert "mcpServers" in config
        assert "defaultServer" in config
        assert "enabled" in config

    def test_get_servers(self, mcp_manager: MCPConfigManager):
        """서버 목록 반환 테스트"""
        servers = mcp_manager.get_servers()
        assert isinstance(servers, dict)
        assert servers == {}  # 초기에는 빈 딕셔너리

    def test_add_server_success(self, mcp_manager: MCPConfigManager, sample_server_config: dict):
        """서버 추가 성공 테스트"""
        mcp_manager.add_server("test_server", sample_server_config)
        
        servers = mcp_manager.get_servers()
        assert "test_server" in servers
        assert servers["test_server"]["command"] == "python"
        assert servers["test_server"]["args"] == ["server.py", "--port", "8080"]

    def test_add_server_empty_name(self, mcp_manager: MCPConfigManager, sample_server_config: dict):
        """빈 서버 이름으로 추가 시 오류 테스트"""
        with pytest.raises(ValueError, match="서버 이름은 필수 입력값입니다"):
            mcp_manager.add_server("", sample_server_config)
        
        with pytest.raises(ValueError, match="서버 이름은 필수 입력값입니다"):
            mcp_manager.add_server("   ", sample_server_config)

    def test_add_server_duplicate_name(self, mcp_manager: MCPConfigManager, sample_server_config: dict):
        """중복 서버 이름으로 추가 시 오류 테스트"""
        mcp_manager.add_server("test_server", sample_server_config)
        
        with pytest.raises(ValueError, match="서버 'test_server'이 이미 존재합니다"):
            mcp_manager.add_server("test_server", sample_server_config)

    def test_update_server_success(self, mcp_manager: MCPConfigManager, sample_server_config: dict):
        """서버 업데이트 성공 테스트"""
        mcp_manager.add_server("test_server", sample_server_config)
        
        update_config = {"timeout": 60, "retries": 3}
        mcp_manager.update_server("test_server", update_config)
        
        servers = mcp_manager.get_servers()
        assert servers["test_server"]["timeout"] == 60
        assert servers["test_server"]["retries"] == 3
        # 기존 설정은 유지되어야 함
        assert servers["test_server"]["command"] == "python"

    def test_update_server_not_exists(self, mcp_manager: MCPConfigManager):
        """존재하지 않는 서버 업데이트 시 오류 테스트"""
        with pytest.raises(ValueError, match="서버 'nonexistent'을 찾을 수 없습니다"):
            mcp_manager.update_server("nonexistent", {"timeout": 30})

    def test_remove_server_success(self, mcp_manager: MCPConfigManager, sample_server_config: dict):
        """서버 제거 성공 테스트"""
        mcp_manager.add_server("test_server", sample_server_config)
        assert mcp_manager.server_exists("test_server")
        
        mcp_manager.remove_server("test_server")
        assert not mcp_manager.server_exists("test_server")

    def test_remove_server_not_exists(self, mcp_manager: MCPConfigManager):
        """존재하지 않는 서버 제거 시 오류 테스트"""
        with pytest.raises(ValueError, match="서버 'nonexistent'을 찾을 수 없습니다"):
            mcp_manager.remove_server("nonexistent")

    def test_remove_default_server(self, mcp_manager: MCPConfigManager, sample_server_config: dict):
        """기본 서버 제거 시 기본 서버 설정 해제 테스트"""
        mcp_manager.add_server("test_server", sample_server_config)
        mcp_manager.set_default_server("test_server")
        
        assert mcp_manager.get_default_server() == "test_server"
        
        mcp_manager.remove_server("test_server")
        assert mcp_manager.get_default_server() is None

    def test_set_default_server_success(self, mcp_manager: MCPConfigManager, sample_server_config: dict):
        """기본 서버 설정 성공 테스트"""
        mcp_manager.add_server("test_server", sample_server_config)
        mcp_manager.set_default_server("test_server")
        
        assert mcp_manager.get_default_server() == "test_server"

    def test_set_default_server_none(self, mcp_manager: MCPConfigManager):
        """기본 서버 해제 테스트"""
        mcp_manager.set_default_server(None)
        assert mcp_manager.get_default_server() is None

    def test_set_default_server_not_exists(self, mcp_manager: MCPConfigManager):
        """존재하지 않는 서버를 기본으로 설정 시 오류 테스트"""
        with pytest.raises(ValueError, match="서버 'nonexistent'을 찾을 수 없습니다"):
            mcp_manager.set_default_server("nonexistent")

    def test_is_enabled_default(self, mcp_manager: MCPConfigManager):
        """기본 활성화 상태 테스트"""
        assert mcp_manager.is_enabled() is True

    def test_set_enabled(self, mcp_manager: MCPConfigManager):
        """활성화/비활성화 설정 테스트"""
        mcp_manager.set_enabled(False)
        assert mcp_manager.is_enabled() is False
        
        mcp_manager.set_enabled(True)
        assert mcp_manager.is_enabled() is True

    def test_server_exists(self, mcp_manager: MCPConfigManager, sample_server_config: dict):
        """서버 존재 여부 확인 테스트"""
        assert not mcp_manager.server_exists("test_server")
        
        mcp_manager.add_server("test_server", sample_server_config)
        assert mcp_manager.server_exists("test_server")

    def test_load_config_invalid_json(self, temp_mcp_config_file: str):
        """잘못된 JSON 파일 로드 시 기본 설정 생성 테스트"""
        # 잘못된 JSON 파일 생성
        with open(temp_mcp_config_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")
        
        manager = MCPConfigManager(temp_mcp_config_file)
        config = manager.get_config()
        
        # 기본 설정이 생성되어야 함
        assert config["mcpServers"] == {}
        assert config["defaultServer"] is None
        assert config["enabled"] is True

    def test_load_config_permission_error(self, temp_mcp_config_file: str):
        """파일 접근 권한 오류 시 기본 설정 생성 테스트"""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            manager = MCPConfigManager(temp_mcp_config_file)
            config = manager.get_config()
            
            # 기본 설정이 생성되어야 함
            assert config["mcpServers"] == {}
            assert config["defaultServer"] is None
            assert config["enabled"] is True

    def test_save_config_create_directory(self, tmp_path: Path):
        """설정 저장 시 디렉토리 생성 테스트"""
        nested_config_file = tmp_path / "nested" / "dir" / "mcp.json"
        manager = MCPConfigManager(str(nested_config_file))
        
        # 디렉토리가 생성되고 파일이 저장되었는지 확인
        assert nested_config_file.exists()
        assert nested_config_file.parent.exists()

    def test_save_config_permission_error(self, mcp_manager: MCPConfigManager, sample_server_config: dict):
        """설정 저장 시 권한 오류 테스트"""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                mcp_manager.add_server("test_server", sample_server_config)

    def test_create_default_config_error(self, temp_mcp_config_file: str):
        """기본 설정 생성 시 오류 테스트"""
        with patch.object(MCPConfigManager, 'save_config', side_effect=Exception("Save failed")):
            with pytest.raises(Exception, match="Save failed"):
                MCPConfigManager(temp_mcp_config_file)

    def test_config_persistence(self, temp_mcp_config_file: str, sample_server_config: dict):
        """설정 영속성 테스트"""
        # 첫 번째 매니저로 설정 저장
        manager1 = MCPConfigManager(temp_mcp_config_file)
        manager1.add_server("test_server", sample_server_config)
        manager1.set_default_server("test_server")
        manager1.set_enabled(False)
        
        # 두 번째 매니저로 설정 로드
        manager2 = MCPConfigManager(temp_mcp_config_file)
        
        assert manager2.server_exists("test_server")
        assert manager2.get_default_server() == "test_server"
        assert manager2.is_enabled() is False
        
        servers = manager2.get_servers()
        assert servers["test_server"]["command"] == "python"

    def test_complex_server_operations(self, mcp_manager: MCPConfigManager):
        """복합 서버 조작 테스트"""
        # 여러 서버 추가
        server_configs = {
            "server1": {"command": "python", "args": ["server1.py"]},
            "server2": {"command": "node", "args": ["server2.js"]},
            "server3": {"command": "java", "args": ["-jar", "server3.jar"]}
        }
        
        for name, config in server_configs.items():
            mcp_manager.add_server(name, config)
        
        # 모든 서버가 추가되었는지 확인
        servers = mcp_manager.get_servers()
        assert len(servers) == 3
        for name in server_configs.keys():
            assert name in servers
        
        # 기본 서버 설정
        mcp_manager.set_default_server("server2")
        assert mcp_manager.get_default_server() == "server2"
        
        # 서버 업데이트
        mcp_manager.update_server("server1", {"timeout": 60})
        updated_servers = mcp_manager.get_servers()
        assert updated_servers["server1"]["timeout"] == 60
        
        # 서버 제거
        mcp_manager.remove_server("server3")
        final_servers = mcp_manager.get_servers()
        assert len(final_servers) == 2
        assert "server3" not in final_servers
        
        # 기본 서버는 여전히 유지되어야 함
        assert mcp_manager.get_default_server() == "server2" 