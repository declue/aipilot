"""
Langchain 기반 MCP 관리자 테스트
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.models.mcp_config import MCPConfig
from application.llm.mcp.models.mcp_server import MCPServer
from application.llm.mcp.models.mcp_server_status import MCPServerStatus


class MockConfigManager:
    """테스트용 설정 관리자"""
    pass


class TestMCPManager:
    """MCP 관리자 테스트"""
    
    @pytest.fixture
    def mock_config_manager(self):
        """테스트용 설정 관리자"""
        return MockConfigManager()
    
    @pytest.fixture
    def sample_mcp_config(self):
        """샘플 MCP 설정"""
        return {
            "mcpServers": {
                "time": {
                    "command": "fastmcp",
                    "args": ["run", "tools/time.py"],
                    "env": {},
                    "description": "Time and timezone management",
                    "enabled": True
                },
                "weather": {
                    "command": "fastmcp",
                    "args": ["run", "tools/weather.py"],
                    "env": {"OPENWEATHER_API_KEY": "test_key"},
                    "description": "Weather information MCP server",
                    "enabled": True
                },
                "disabled_server": {
                    "command": "test",
                    "args": [],
                    "env": {},
                    "description": "Disabled server",
                    "enabled": False
                }
            },
            "defaultServer": None,
            "enabled": True
        }
    
    @pytest.fixture
    def temp_mcp_file(self, sample_mcp_config):
        """임시 MCP 설정 파일"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_mcp_config, f)
            temp_file = f.name
        
        yield temp_file
        
        # 정리
        os.unlink(temp_file)
    
    def test_initialization_with_config_file(self, mock_config_manager, temp_mcp_file):
        """설정 파일과 함께 초기화 테스트"""
        with patch('builtins.open', side_effect=lambda path, *args, **kwargs: 
                   open(temp_mcp_file, *args, **kwargs) if path == 'mcp.json' else open(path, *args, **kwargs)):
            manager = MCPManager(mock_config_manager)
            
            assert manager._mcp_config is not None
            assert manager._mcp_config.enabled is True
            assert len(manager._mcp_config.mcp_servers) == 3
    
    def test_initialization_without_config_file(self, mock_config_manager):
        """설정 파일 없이 초기화 테스트"""
        manager = MCPManager(mock_config_manager)
        
        assert manager._mcp_config is not None
        assert isinstance(manager._mcp_config, MCPConfig)
    
    def test_get_enabled_servers(self, mock_config_manager, temp_mcp_file):
        """활성화된 서버 목록 가져오기 테스트"""
        with patch('builtins.open', side_effect=lambda path, *args, **kwargs: 
                   open(temp_mcp_file, *args, **kwargs) if path == 'mcp.json' else open(path, *args, **kwargs)):
            manager = MCPManager(mock_config_manager)
            
            enabled_servers = manager.get_enabled_servers()
            
            assert len(enabled_servers) == 2  # time과 weather만 enabled
            assert "time" in enabled_servers
            assert "weather" in enabled_servers
            assert "disabled_server" not in enabled_servers
            
            # MCPServer 객체인지 확인
            assert isinstance(enabled_servers["time"], MCPServer)
            assert enabled_servers["time"].name == "time"
            assert enabled_servers["time"].command == "fastmcp"
    
    @pytest.mark.asyncio
    async def test_test_server_connection_success(self, mock_config_manager, temp_mcp_file):
        """서버 연결 테스트 성공"""
        with patch('builtins.open', side_effect=lambda path, *args, **kwargs: 
                   open(temp_mcp_file, *args, **kwargs) if path == 'mcp.json' else open(path, *args, **kwargs)):
            manager = MCPManager(mock_config_manager)
            
            status = await manager.test_server_connection("time")
            
            assert isinstance(status, MCPServerStatus)
            assert status.server_name == "time"
            assert status.connected is True
            assert len(status.tools) > 0
            assert status.error_message is None
    
    @pytest.mark.asyncio
    async def test_test_server_connection_not_found(self, mock_config_manager, temp_mcp_file):
        """존재하지 않는 서버 연결 테스트"""
        with patch('builtins.open', side_effect=lambda path, *args, **kwargs: 
                   open(temp_mcp_file, *args, **kwargs) if path == 'mcp.json' else open(path, *args, **kwargs)):
            manager = MCPManager(mock_config_manager)
            
            status = await manager.test_server_connection("non_existent")
            
            assert isinstance(status, MCPServerStatus)
            assert status.server_name == "non_existent"
            assert status.connected is False
            assert "서버 'non_existent'를 찾을 수 없습니다" in status.error_message
    
    def test_get_server_status(self, mock_config_manager):
        """서버 상태 가져오기 테스트"""
        manager = MCPManager(mock_config_manager)
        
        # 상태가 없는 경우
        status = manager.get_server_status("test")
        assert status is None
        
        # 상태 추가 후
        test_status = MCPServerStatus(server_name="test", connected=True)
        manager._server_statuses["test"] = test_status
        
        status = manager.get_server_status("test")
        assert status == test_status
    
    def test_get_all_server_statuses(self, mock_config_manager):
        """모든 서버 상태 가져오기 테스트"""
        manager = MCPManager(mock_config_manager)
        
        # 빈 상태
        statuses = manager.get_all_server_statuses()
        assert isinstance(statuses, dict)
        assert len(statuses) == 0
        
        # 상태 추가 후
        test_status = MCPServerStatus(server_name="test", connected=True)
        manager._server_statuses["test"] = test_status
        
        statuses = manager.get_all_server_statuses()
        assert len(statuses) == 1
        assert "test" in statuses
        assert statuses["test"] == test_status
    
    @pytest.mark.asyncio
    async def test_refresh_all_servers(self, mock_config_manager, temp_mcp_file):
        """모든 서버 상태 갱신 테스트"""
        with patch('builtins.open', side_effect=lambda path, *args, **kwargs: 
                   open(temp_mcp_file, *args, **kwargs) if path == 'mcp.json' else open(path, *args, **kwargs)):
            manager = MCPManager(mock_config_manager)
            
            await manager.refresh_all_servers()
            
            # 활성화된 서버들의 상태가 갱신되었는지 확인
            statuses = manager.get_all_server_statuses()
            assert len(statuses) == 2  # time과 weather
            assert "time" in statuses
            assert "weather" in statuses
    
    def test_is_mcp_enabled(self, mock_config_manager, temp_mcp_file):
        """MCP 활성화 상태 확인 테스트"""
        with patch('builtins.open', side_effect=lambda path, *args, **kwargs: 
                   open(temp_mcp_file, *args, **kwargs) if path == 'mcp.json' else open(path, *args, **kwargs)):
            manager = MCPManager(mock_config_manager)
            
            assert manager.is_mcp_enabled() is True
    
    def test_get_mcp_config(self, mock_config_manager, temp_mcp_file):
        """MCP 설정 가져오기 테스트"""
        with patch('builtins.open', side_effect=lambda path, *args, **kwargs: 
                   open(temp_mcp_file, *args, **kwargs) if path == 'mcp.json' else open(path, *args, **kwargs)):
            manager = MCPManager(mock_config_manager)
            
            config = manager.get_mcp_config()
            assert isinstance(config, MCPConfig)
            assert config.enabled is True
            assert len(config.mcp_servers) == 3 