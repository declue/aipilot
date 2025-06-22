import configparser
import os
from pathlib import Path
from unittest.mock import Mock, mock_open, patch
import pytest

from application.config.app_config_manager import AppConfigManager


@pytest.fixture
def temp_config_file(tmp_path: Path) -> str:
    """임시 설정 파일 경로 반환"""
    return str(tmp_path / "test_app.config")


@pytest.fixture
def mock_app_config_manager(temp_config_file: str) -> AppConfigManager:
    """Mock을 사용한 AppConfigManager 인스턴스"""
    return AppConfigManager(temp_config_file)


class TestAppConfigManager:
    """AppConfigManager 테스트 클래스"""

    def test_init_creates_default_config_when_file_not_exists(self, temp_config_file: str):
        """파일이 없을 때 기본 설정이 생성되는지 테스트"""
        manager = AppConfigManager(temp_config_file)
        
        assert os.path.exists(temp_config_file)
        assert manager.get_config_value("LLM", "api_key") == "your-api-key-here"
        assert manager.get_config_value("UI", "font_size") == "14"

    def test_init_with_template_file(self, tmp_path: Path):
        """템플릿 파일이 있을 때 복사되는지 테스트"""
        template_file = tmp_path / "app.config.template"
        config_file = tmp_path / "app.config"
        
        # 템플릿 파일 생성
        with open(template_file, "w", encoding="utf-8") as f:
            f.write("[TEST]\nkey=value\n")
        
        manager = AppConfigManager(str(config_file))
        
        assert config_file.exists()

    def test_load_existing_config(self, temp_config_file: str):
        """기존 설정 파일을 로드하는 테스트"""
        # 기존 설정 파일 생성
        config = configparser.ConfigParser()
        config["TEST"] = {"key": "value"}
        with open(temp_config_file, "w", encoding="utf-8") as f:
            config.write(f)
        
        manager = AppConfigManager(temp_config_file)
        assert manager.get_config_value("TEST", "key") == "value"

    def test_set_and_get_config_value(self, mock_app_config_manager: AppConfigManager):
        """설정값 저장 및 가져오기 테스트"""
        mock_app_config_manager.set_config_value("TEST", "key", "value")
        assert mock_app_config_manager.get_config_value("TEST", "key") == "value"

    def test_get_config_value_with_fallback(self, mock_app_config_manager: AppConfigManager):
        """존재하지 않는 설정값에 대한 fallback 테스트"""
        result = mock_app_config_manager.get_config_value("NONEXISTENT", "key", "fallback")
        assert result == "fallback"

    def test_set_config_value_validation(self, mock_app_config_manager: AppConfigManager):
        """설정값 유효성 검사 테스트"""
        # 빈 섹션
        with pytest.raises(ValueError, match="섹션과 키는 필수 입력값입니다"):
            mock_app_config_manager.set_config_value("", "key", "value")
        
        # 빈 키
        with pytest.raises(ValueError, match="섹션과 키는 필수 입력값입니다"):
            mock_app_config_manager.set_config_value("section", "", "value")
        
        # None 값
        with pytest.raises(ValueError, match="값은 None일 수 없습니다"):
            mock_app_config_manager.set_config_value("section", "key", None)

    def test_get_ui_config_default(self, mock_app_config_manager: AppConfigManager):
        """UI 설정 기본값 테스트"""
        ui_config = mock_app_config_manager.get_ui_config()
        
        assert ui_config["font_size"] == 14
        assert ui_config["chat_bubble_max_width"] == 600
        assert ui_config["window_theme"] == "light"
        assert "font_family" in ui_config

    def test_set_ui_config_success(self, mock_app_config_manager: AppConfigManager):
        """UI 설정 저장 성공 테스트"""
        mock_app_config_manager.set_ui_config(
            font_family="Arial",
            font_size=16,
            chat_bubble_max_width=800,
            window_theme="dark"
        )
        
        ui_config = mock_app_config_manager.get_ui_config()
        assert ui_config["font_family"] == "Arial"
        assert ui_config["font_size"] == 16
        assert ui_config["chat_bubble_max_width"] == 800
        assert ui_config["window_theme"] == "dark"

    def test_set_ui_config_validation(self, mock_app_config_manager: AppConfigManager):
        """UI 설정 유효성 검사 테스트"""
        # 빈 폰트 패밀리
        with pytest.raises(ValueError, match="폰트 패밀리와 윈도우 테마는 필수 입력값입니다"):
            mock_app_config_manager.set_ui_config("", 14, 600, "light")
        
        # 0 이하 폰트 크기
        with pytest.raises(ValueError, match="폰트 크기는 0보다 커야 합니다"):
            mock_app_config_manager.set_ui_config("Arial", 0, 600, "light")
        
        # 0 이하 채팅 버블 너비
        with pytest.raises(ValueError, match="채팅 버블 최대 너비는 0보다 커야 합니다"):
            mock_app_config_manager.set_ui_config("Arial", 14, 0, "light")

    def test_get_github_repositories_empty(self, mock_app_config_manager: AppConfigManager):
        """GitHub 저장소 목록이 비어있을 때 테스트"""
        repos = mock_app_config_manager.get_github_repositories()
        assert repos == []

    def test_set_and_get_github_repositories(self, mock_app_config_manager: AppConfigManager):
        """GitHub 저장소 목록 설정 및 가져오기 테스트"""
        repositories = ["user/repo1", "user/repo2", "org/repo3"]
        mock_app_config_manager.set_github_repositories(repositories)
        
        retrieved_repos = mock_app_config_manager.get_github_repositories()
        assert retrieved_repos == repositories

    def test_save_ui_config_dict(self, mock_app_config_manager: AppConfigManager):
        """UI 설정 딕셔너리 형태 저장 테스트"""
        ui_config = {
            "font_family": "Helvetica",
            "font_size": "18",
            "window_theme": "dark"
        }
        
        mock_app_config_manager.save_ui_config(ui_config)
        
        retrieved_config = mock_app_config_manager.get_ui_config()
        assert retrieved_config["font_family"] == "Helvetica"
        assert retrieved_config["font_size"] == 18  # 자동 형변환 확인

    def test_get_mcp_config_file_exists(self, mock_app_config_manager: AppConfigManager):
        """MCP 설정 파일이 존재할 때 테스트"""
        test_mcp_data = {
            "mcpServers": {
                "test_server": {
                    "command": "test_command",
                    "args": ["arg1", "arg2"]
                }
            },
            "defaultServer": "test_server",
            "enabled": True
        }
        
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data='{"mcpServers": {}}')), \
             patch("json.load", return_value=test_mcp_data):
            
            mcp_config = mock_app_config_manager.get_mcp_config()
            assert "mcpServers" in mcp_config

    def test_get_mcp_config_file_not_exists(self, mock_app_config_manager: AppConfigManager):
        """MCP 설정 파일이 없을 때 기본값 반환 테스트"""
        with patch("os.path.exists", return_value=False):
            mcp_config = mock_app_config_manager.get_mcp_config()
            
            assert mcp_config["mcpServers"] == {}
            assert mcp_config["defaultServer"] is None
            assert mcp_config["enabled"] is True

    @patch("builtins.open", new_callable=mock_open)
    def test_save_config_called(self, mock_file: Mock, mock_app_config_manager: AppConfigManager):
        """설정 저장 메서드 호출 테스트"""
        mock_app_config_manager.save_config()
        
        # 파일이 쓰기 모드로 열렸는지 확인
        mock_file.assert_called_once_with(mock_app_config_manager.config_file, "w", encoding="utf-8")

    @patch("configparser.ConfigParser.read", side_effect=configparser.Error("파싱 오류"))
    @patch("os.path.exists", return_value=True)
    def test_load_config_parse_error(self, mock_exists: Mock, mock_read: Mock, temp_config_file: str):
        """설정 파일 파싱 오류 시 기본 설정 생성 테스트"""
        with patch.object(AppConfigManager, 'create_default_config') as mock_create_default:
            manager = AppConfigManager(temp_config_file)
            mock_create_default.assert_called()

    @patch("configparser.ConfigParser.read", side_effect=PermissionError("권한 없음"))
    @patch("os.path.exists", return_value=True)
    def test_load_config_permission_error(self, mock_exists: Mock, mock_read: Mock, temp_config_file: str):
        """설정 파일 접근 권한 오류 시 기본 설정 생성 테스트"""
        with patch.object(AppConfigManager, 'create_default_config') as mock_create_default:
            manager = AppConfigManager(temp_config_file)
            mock_create_default.assert_called()

    def test_get_ui_config_invalid_font_size(self, mock_app_config_manager: AppConfigManager):
        """잘못된 폰트 크기 값 처리 테스트"""
        # 잘못된 폰트 크기 설정
        mock_app_config_manager.set_config_value("UI", "font_size", "invalid")
        
        ui_config = mock_app_config_manager.get_ui_config()
        # 기본값으로 대체되어야 함
        assert ui_config["font_size"] == 14

    def test_get_ui_config_invalid_chat_bubble_width(self, mock_app_config_manager: AppConfigManager):
        """잘못된 채팅 버블 너비 값 처리 테스트"""
        # 잘못된 채팅 버블 너비 설정
        mock_app_config_manager.set_config_value("UI", "chat_bubble_max_width", "invalid")
        
        ui_config = mock_app_config_manager.get_ui_config()
        # 기본값으로 대체되어야 함
        assert ui_config["chat_bubble_max_width"] == 600 