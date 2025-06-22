import os
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from application.config.config_manager import ConfigManager
from application.config.app_config_manager import AppConfigManager
from application.config.llm_profile_manager import LLMProfileManager


@pytest.fixture
def temp_config_file(tmp_path: Path) -> str:
    """임시 설정 파일 경로 반환"""
    return str(tmp_path / "test_app.config")


@pytest.fixture
def temp_profiles_file(tmp_path: Path) -> str:
    """임시 프로필 파일 경로 반환"""
    return str(tmp_path / "test_llm_profiles.json")


@pytest.fixture
def mock_config_manager(temp_config_file: str, temp_profiles_file: str) -> ConfigManager:
    """Mock을 사용한 ConfigManager 인스턴스"""
    # 각 테스트마다 별도의 프로필 파일을 사용하도록 수정
    manager = ConfigManager(temp_config_file)
    manager.llm_profile_manager.llm_profiles_file = temp_profiles_file
    manager.llm_profile_manager.load_llm_profiles()  # 다시 로드하여 깨끗한 상태로 시작
    return manager


class TestConfigManagerRefactored:
    """리팩토링된 ConfigManager 테스트 클래스"""

    def test_composition_structure(self, mock_config_manager: ConfigManager):
        """컴포지션 구조가 올바르게 구성되었는지 테스트"""
        # AppConfigManager와 LLMProfileManager가 올바르게 조합되었는지 확인
        assert isinstance(mock_config_manager.app_config_manager, AppConfigManager)
        assert isinstance(mock_config_manager.llm_profile_manager, LLMProfileManager)
        
        # 기존 인터페이스 호환성 확인
        assert hasattr(mock_config_manager, 'config_file')
        assert hasattr(mock_config_manager, 'config')
        assert hasattr(mock_config_manager, 'llm_profiles_file')

    def test_app_config_delegation(self, mock_config_manager: ConfigManager):
        """AppConfigManager에 대한 위임이 올바르게 작동하는지 테스트"""
        # UI 설정 위임 테스트
        ui_config = mock_config_manager.get_ui_config()
        assert "font_size" in ui_config
        assert "window_theme" in ui_config

        # 설정값 위임 테스트
        mock_config_manager.set_config_value("TEST", "key", "value")
        assert mock_config_manager.get_config_value("TEST", "key") == "value"

        # GitHub 저장소 위임 테스트
        repositories = ["user/repo1", "user/repo2"]
        mock_config_manager.set_github_repositories(repositories)
        assert mock_config_manager.get_github_repositories() == repositories

    def test_llm_profile_delegation(self, mock_config_manager: ConfigManager):
        """LLMProfileManager에 대한 위임이 올바르게 작동하는지 테스트"""
        # 프로필 목록 위임 테스트
        profiles = mock_config_manager.get_llm_profiles()
        assert "default" in profiles
        assert "openai" in profiles

        # 현재 프로필 위임 테스트 (실제 현재 프로필 확인)
        current_profile_name = mock_config_manager.get_current_profile_name()
        assert current_profile_name in ["default", "openai"]  # 둘 중 하나여야 함

        # 프로필 생성 위임 테스트
        profile_config = {
            "name": "테스트 프로필",
            "api_key": "test-key",
            "base_url": "http://test.com",
            "model": "test-model",
            "temperature": 0.5,
            "max_tokens": 1000,
            "top_k": 10,
        }
        mock_config_manager.create_llm_profile("test_profile", profile_config)
        assert "test_profile" in mock_config_manager.get_llm_profiles()

    def test_reference_synchronization(self, mock_config_manager: ConfigManager):
        """참조 동기화가 올바르게 작동하는지 테스트"""
        # 프로필 변경 후 참조 동기화 확인
        mock_config_manager.set_current_profile("openai")
        assert mock_config_manager._current_profile_name == mock_config_manager.llm_profile_manager._current_profile_name

        # 새로운 프로필 생성 후 참조 동기화 확인
        profile_config = {
            "name": "동기화 테스트",
            "api_key": "sync-key",
            "base_url": "http://sync.com",
            "model": "sync-model",
            "temperature": 0.7,
            "max_tokens": 2000,
            "top_k": 15,
        }
        
        # 고유한 프로필 이름 사용
        import time
        unique_profile_name = f"sync_profile_{int(time.time() * 1000000)}"
        mock_config_manager.create_llm_profile(unique_profile_name, profile_config)
        assert mock_config_manager._llm_profiles == mock_config_manager.llm_profile_manager._llm_profiles

    def test_get_llm_config_with_profile_priority(self, mock_config_manager: ConfigManager):
        """프로필 우선, 하위 호환성 유지하는 LLM 설정 반환 테스트"""
        # 프로필에서 설정을 가져오는지 확인
        llm_config = mock_config_manager.get_llm_config()
        
        # 기본 프로필의 설정이 반환되는지 확인 (실제 생성된 기본 프로필 확인)
        current_profile = mock_config_manager.llm_profile_manager.get_current_profile()
        assert llm_config["api_key"] == current_profile.get("api_key", "your-api-key-here")
        assert llm_config["model"] == current_profile.get("model", "llama3.2")
        assert llm_config["base_url"] == current_profile.get("base_url", "http://localhost:11434/v1")

    def test_set_current_profile_updates_both_storages(self, mock_config_manager: ConfigManager):
        """현재 프로필 설정 시 두 저장소 모두 업데이트되는지 테스트"""
        mock_config_manager.set_current_profile("openai")
        
        # LLM 프로필 매니저에서 업데이트되었는지 확인
        assert mock_config_manager.llm_profile_manager.get_current_profile_name() == "openai"
        
        # app.config에도 저장되었는지 확인
        assert mock_config_manager.get_config_value("LLM", "current_profile") == "openai"

    def test_backward_compatibility_with_app_config(self, mock_config_manager: ConfigManager):
        """app.config 파일만 있을 때의 하위 호환성 테스트"""
        # 프로필 파일이 없거나 비어있을 때 app.config 설정 사용
        with patch.object(mock_config_manager.llm_profile_manager, 'get_current_profile', return_value={}):
            # app.config에 LLM 설정 추가
            mock_config_manager.set_config_value("LLM", "model", "legacy-model")
            mock_config_manager.set_config_value("LLM", "api_key", "legacy-key")
            
            llm_config = mock_config_manager.get_llm_config()
            
            # app.config의 설정이 사용되는지 확인
            assert llm_config["model"] == "legacy-model"
            assert llm_config["api_key"] == "legacy-key"

    def test_load_methods_delegation(self, mock_config_manager: ConfigManager):
        """로드 메서드들이 올바르게 위임되는지 테스트"""
        with patch.object(mock_config_manager.app_config_manager, 'load_config') as mock_load_config, \
             patch.object(mock_config_manager.llm_profile_manager, 'load_llm_profiles') as mock_load_profiles:
            
            mock_config_manager.load_config()
            mock_config_manager.load_llm_profiles()
            
            mock_load_config.assert_called_once()
            mock_load_profiles.assert_called_once()

    def test_save_methods_delegation(self, mock_config_manager: ConfigManager):
        """저장 메서드들이 올바르게 위임되는지 테스트"""
        with patch.object(mock_config_manager.app_config_manager, 'save_config') as mock_save_config, \
             patch.object(mock_config_manager.llm_profile_manager, 'save_llm_profiles') as mock_save_profiles:
            
            mock_config_manager.save_config()
            mock_config_manager.save_llm_profiles()
            
            mock_save_config.assert_called_once()
            mock_save_profiles.assert_called_once()

    def test_profile_crud_operations_integration(self, mock_config_manager: ConfigManager):
        """프로필 CRUD 작업 통합 테스트"""
        # Create
        profile_config = {
            "name": "CRUD 테스트",
            "api_key": "crud-key",
            "base_url": "http://crud.com",
            "model": "crud-model",
            "temperature": 0.6,
            "max_tokens": 1500,
            "top_k": 12,
        }
        mock_config_manager.create_llm_profile("crud_profile", profile_config)
        
        # Read
        profiles = mock_config_manager.get_llm_profiles()
        assert "crud_profile" in profiles
        assert profiles["crud_profile"]["name"] == "CRUD 테스트"
        
        # Update
        mock_config_manager.update_llm_profile("crud_profile", {"model": "updated-crud-model"})
        updated_profiles = mock_config_manager.get_llm_profiles()
        assert updated_profiles["crud_profile"]["model"] == "updated-crud-model"
        
        # Delete
        mock_config_manager.delete_llm_profile("crud_profile")
        final_profiles = mock_config_manager.get_llm_profiles()
        assert "crud_profile" not in final_profiles

    def test_error_handling_delegation(self, mock_config_manager: ConfigManager):
        """에러 처리가 올바르게 위임되는지 테스트"""
        # LLM 프로필 에러
        with pytest.raises(ValueError):
            mock_config_manager.delete_llm_profile("default")  # 기본 프로필 삭제 불가
        
        with pytest.raises(ValueError):
            mock_config_manager.set_current_profile("nonexistent")  # 존재하지 않는 프로필
        
        # App 설정 에러
        with pytest.raises(ValueError):
            mock_config_manager.set_config_value("", "key", "value")  # 빈 섹션

    def test_mcp_config_delegation(self, mock_config_manager: ConfigManager):
        """MCP 설정이 올바르게 위임되는지 테스트"""
        with patch.object(mock_config_manager.app_config_manager, 'get_mcp_config') as mock_get_mcp:
            mock_get_mcp.return_value = {"mcpServers": {}, "enabled": True}
            
            mcp_config = mock_config_manager.get_mcp_config()
            
            mock_get_mcp.assert_called_once()
            assert "mcpServers" in mcp_config

    @patch('application.config.config_manager.AppConfigManager')
    @patch('application.config.config_manager.LLMProfileManager')
    def test_initialization_with_mocks(self, mock_llm_manager_class: Mock, mock_app_manager_class: Mock, temp_config_file: str):
        """Mock을 사용한 초기화 테스트"""
        mock_app_manager = Mock()
        mock_llm_manager = Mock()
        mock_app_manager_class.return_value = mock_app_manager
        mock_llm_manager_class.return_value = mock_llm_manager
        
        # Mock 속성 설정
        mock_app_manager.config_file = temp_config_file
        mock_app_manager.config = Mock()
        mock_llm_manager.llm_profiles_file = "test_profiles.json"
        mock_llm_manager._llm_profiles = {}
        mock_llm_manager._current_profile_name = "default"
        
        manager = ConfigManager(temp_config_file)
        
        # Mock 클래스들이 올바른 인자로 호출되었는지 확인
        mock_app_manager_class.assert_called_once_with(temp_config_file)
        mock_llm_manager_class.assert_called_once_with()
        
        # 속성이 올바르게 설정되었는지 확인
        assert manager.config_file == temp_config_file 