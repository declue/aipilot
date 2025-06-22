from pathlib import Path
from unittest.mock import patch

import pytest

from application.config.github_notification_config import GitHubNotificationConfig
from application.config.unified_config_manager import UnifiedConfigManager


@pytest.fixture
def temp_config_files(tmp_path: Path) -> dict[str, str]:
    """임시 설정 파일들 생성"""
    return {
        "app_config": str(tmp_path / "test_app.config"),
        "llm_profiles": str(tmp_path / "test_llm_profiles.json"),
        "mcp_config": str(tmp_path / "test_mcp.json"),
        "github_notification": str(tmp_path / "test_github_notification.json"),
    }


@pytest.fixture
def unified_manager(temp_config_files: dict[str, str]) -> UnifiedConfigManager:
    """UnifiedConfigManager 인스턴스 생성"""
    return UnifiedConfigManager(
        app_config_file=temp_config_files["app_config"],
        llm_profiles_file=temp_config_files["llm_profiles"],
        mcp_config_file=temp_config_files["mcp_config"],
        github_notification_config_file=temp_config_files["github_notification"],
    )


class TestUnifiedConfigManager:
    """통합 설정 관리자 테스트 클래스"""

    def test_initialization(self, unified_manager: UnifiedConfigManager):
        """초기화 테스트"""
        assert unified_manager.app_config_manager is not None
        assert unified_manager.llm_profile_manager is not None
        assert unified_manager.mcp_config_manager is not None
        assert unified_manager._github_notification_config is not None

    def test_app_config_delegation(self, unified_manager: UnifiedConfigManager):
        """앱 설정 위임 테스트"""
        # 설정값 저장/조회
        unified_manager.set_config_value("TEST", "key", "value")
        assert unified_manager.get_config_value("TEST", "key") == "value"

        # UI 설정
        ui_config = unified_manager.get_ui_config()
        assert "font_size" in ui_config
        assert "window_theme" in ui_config

        # GitHub 저장소 설정
        repositories = ["user/repo1", "user/repo2"]
        unified_manager.set_github_repositories(repositories)
        assert unified_manager.get_github_repositories() == repositories

    def test_llm_profile_delegation(self, unified_manager: UnifiedConfigManager):
        """LLM 프로필 위임 테스트"""
        # 기본 프로필 확인
        profiles = unified_manager.get_llm_profiles()
        assert isinstance(profiles, dict)
        
        current_profile_name = unified_manager.get_current_profile_name()
        assert isinstance(current_profile_name, str)

        # 새 프로필 생성
        test_profile = {
            "name": "테스트 프로필",
            "api_key": "test-key",
            "base_url": "http://test.com",
            "model": "test-model",
            "temperature": 0.8,
            "max_tokens": 1000,
            "top_k": 50,
        }
        unified_manager.create_llm_profile("test_profile", test_profile)
        
        # 프로필 존재 확인
        assert unified_manager.profile_exists("test_profile")
        
        # 프로필 업데이트
        unified_manager.update_llm_profile("test_profile", {"temperature": 0.9})
        profiles = unified_manager.get_llm_profiles()
        assert profiles["test_profile"]["temperature"] == 0.9

        # 프로필 삭제
        unified_manager.delete_llm_profile("test_profile")
        assert not unified_manager.profile_exists("test_profile")

    def test_mcp_config_delegation(self, unified_manager: UnifiedConfigManager):
        """MCP 설정 위임 테스트"""
        # 기본 설정 확인
        mcp_config = unified_manager.get_mcp_config()
        assert "mcpServers" in mcp_config
        assert "enabled" in mcp_config

        # MCP 서버 추가
        server_config = {
            "command": "python",
            "args": ["test_server.py"],
            "env": {"TEST": "value"}
        }
        unified_manager.add_mcp_server("test_server", server_config)
        
        # 서버 존재 확인
        assert unified_manager.mcp_server_exists("test_server")
        
        servers = unified_manager.get_mcp_servers()
        assert "test_server" in servers

        # 기본 서버 설정
        unified_manager.set_default_mcp_server("test_server")
        assert unified_manager.get_default_mcp_server() == "test_server"

        # MCP 비활성화/활성화
        unified_manager.set_mcp_enabled(False)
        assert not unified_manager.is_mcp_enabled()
        
        unified_manager.set_mcp_enabled(True)
        assert unified_manager.is_mcp_enabled()

        # 서버 업데이트
        unified_manager.update_mcp_server("test_server", {"timeout": 30})
        servers = unified_manager.get_mcp_servers()
        assert servers["test_server"]["timeout"] == 30

        # 서버 제거
        unified_manager.remove_mcp_server("test_server")
        assert not unified_manager.mcp_server_exists("test_server")

    def test_github_notification_delegation(self, unified_manager: UnifiedConfigManager):
        """GitHub 알림 설정 위임 테스트"""
        # 기본 설정 확인
        github_config = unified_manager.get_github_notification_config()
        assert isinstance(github_config, GitHubNotificationConfig)

        # 새 설정 생성 및 저장
        new_config = GitHubNotificationConfig()
        new_config.enabled = False
        unified_manager.set_github_notification_config(new_config)
        
        # 설정 확인
        saved_config = unified_manager.get_github_notification_config()
        assert not saved_config.enabled

        # 알림 표시 여부 확인
        show_system, show_chat = unified_manager.should_show_github_notification("push")
        assert not show_system and not show_chat  # enabled=False이므로

    def test_ui_config_methods(self, unified_manager: UnifiedConfigManager):
        """UI 설정 메서드들 테스트"""
        # 개별 파라미터로 설정
        unified_manager.set_ui_config("Arial", 16, 800, "dark")
        ui_config = unified_manager.get_ui_config()
        
        assert ui_config["font_family"] == "Arial"
        assert ui_config["font_size"] == 16
        assert ui_config["chat_bubble_max_width"] == 800
        assert ui_config["window_theme"] == "dark"

        # 딕셔너리로 설정
        new_ui_config = {
            "font_family": "Helvetica",
            "font_size": 18,
            "chat_bubble_max_width": 700,
            "window_theme": "light"
        }
        unified_manager.save_ui_config(new_ui_config)
        
        updated_config = unified_manager.get_ui_config()
        assert updated_config["font_family"] == "Helvetica"
        assert updated_config["font_size"] == 18

    def test_github_config_methods(self, unified_manager: UnifiedConfigManager):
        """GitHub 설정 메서드들 테스트"""
        # GitHub 설정
        github_config = {
            "repositories": ["user/repo1", "user/repo2"],
            "webhook_enabled": True,
            "webhook_port": 9000
        }
        unified_manager.set_github_config(github_config)
        
        # 설정 확인
        saved_config = unified_manager.get_github_config()
        assert saved_config["repositories"] == ["user/repo1", "user/repo2"]
        assert saved_config["webhook_enabled"] is True
        assert saved_config["webhook_port"] == 9000

    def test_reload_all_configs(self, unified_manager: UnifiedConfigManager):
        """모든 설정 리로드 테스트"""
        # 초기 설정값 변경
        unified_manager.set_config_value("TEST", "before_reload", "old_value")
        
        # 외부에서 설정 파일 직접 수정 시뮬레이션
        with patch.object(unified_manager.app_config_manager, 'load_config') as mock_load_app:
            with patch.object(unified_manager.llm_profile_manager, 'load_llm_profiles') as mock_load_llm:
                with patch.object(unified_manager.mcp_config_manager, 'load_config') as mock_load_mcp:
                    
                    unified_manager.reload_all_configs()
                    
                    # 모든 load 메서드가 호출되었는지 확인
                    mock_load_app.assert_called_once()
                    mock_load_llm.assert_called_once()
                    mock_load_mcp.assert_called_once()

    def test_get_all_config_files(self, unified_manager: UnifiedConfigManager, temp_config_files: dict[str, str]):
        """모든 설정 파일 경로 반환 테스트"""
        config_files = unified_manager.get_all_config_files()
        
        assert len(config_files) == 4
        assert temp_config_files["app_config"] in config_files
        assert temp_config_files["llm_profiles"] in config_files
        assert temp_config_files["mcp_config"] in config_files
        assert temp_config_files["github_notification"] in config_files

    def test_initialization_without_github_config(self, temp_config_files: dict[str, str]):
        """GitHub 설정 파일 없이 초기화 테스트"""
        manager = UnifiedConfigManager(
            app_config_file=temp_config_files["app_config"],
            llm_profiles_file=temp_config_files["llm_profiles"],
            mcp_config_file=temp_config_files["mcp_config"],
            # github_notification_config_file은 None
        )
        
        # GitHub 설정이 None이어야 함
        assert manager.get_github_notification_config() is None
        
        # 알림 표시 여부 확인 (False 반환되어야 함)
        show_system, show_chat = manager.should_show_github_notification("push")
        assert not show_system and not show_chat

    def test_cleanup(self, unified_manager: UnifiedConfigManager):
        """리소스 정리 테스트"""
        # cleanup 메서드 호출 (예외 발생하지 않아야 함)
        unified_manager.cleanup()

    def test_error_handling_in_github_notification_load(self, temp_config_files: dict[str, str]):
        """GitHub 알림 설정 로드 오류 처리 테스트"""
        # 잘못된 JSON 파일 생성
        github_config_file = temp_config_files["github_notification"]
        with open(github_config_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")
        
        # 초기화 시 오류 처리되어야 함
        manager = UnifiedConfigManager(
            app_config_file=temp_config_files["app_config"],
            llm_profiles_file=temp_config_files["llm_profiles"],
            mcp_config_file=temp_config_files["mcp_config"],
            github_notification_config_file=github_config_file,
        )
        
        # 기본 설정이 생성되어야 함
        assert manager.get_github_notification_config() is not None
        assert isinstance(manager.get_github_notification_config(), GitHubNotificationConfig)

    def test_github_notification_save_error_handling(self, unified_manager: UnifiedConfigManager):
        """GitHub 알림 설정 저장 오류 처리 테스트"""
        # 파일 경로를 읽기 전용 디렉토리로 설정
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            new_config = GitHubNotificationConfig()
            new_config.enabled = False
            
            # 저장 시 예외가 발생해도 프로그램이 중단되지 않아야 함
            try:
                unified_manager.set_github_notification_config(new_config)
            except PermissionError:
                pytest.fail("PermissionError should be handled gracefully")

    def test_method_chaining_compatibility(self, unified_manager: UnifiedConfigManager):
        """메서드 체이닝 호환성 테스트"""
        # 여러 설정을 연속으로 변경해도 문제없어야 함
        unified_manager.set_config_value("APP", "name", "TestApp")
        unified_manager.set_ui_config("Arial", 14, 600, "light")
        unified_manager.set_github_repositories(["test/repo"])
        unified_manager.set_mcp_enabled(True)
        
        # 모든 설정이 올바르게 저장되었는지 확인
        assert unified_manager.get_config_value("APP", "name") == "TestApp"
        ui_config = unified_manager.get_ui_config()
        assert ui_config["font_family"] == "Arial"
        assert unified_manager.get_github_repositories() == ["test/repo"]
        assert unified_manager.is_mcp_enabled() is True 