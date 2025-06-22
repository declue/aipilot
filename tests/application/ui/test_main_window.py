import sys
from unittest.mock import Mock, patch

import pytest

# PySide6 Qt 어플리케이션 테스트를 위한 필수 설정
from PySide6.QtWidgets import QApplication

# QApplication이 없으면 생성
if not QApplication.instance():
    app = QApplication(sys.argv)

from application.config.config_manager import ConfigManager
from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager
from application.ui.main_window import MainWindow


class TestMainWindow:
    """MainWindow 테스트 클래스"""

    @pytest.fixture
    def mock_config_manager(self) -> Mock:
        """ConfigManager 모킹"""
        mock = Mock(spec=ConfigManager)
        mock.get_ui_config.return_value = {
            'font_family': 'Arial',
            'font_size': 14,
            'chat_bubble_max_width': 700,
            'window_theme': 'light'
        }
        mock.get_llm_config.return_value = {
            'model': 'test-model',
            'api_key': 'test-key'
        }
        return mock

    @pytest.fixture
    def mock_mcp_manager(self) -> Mock:
        """MCPManager 모킹"""
        return Mock(spec=MCPManager)

    @pytest.fixture
    def mock_mcp_tool_manager(self) -> Mock:
        """MCPToolManager 모킹"""
        return Mock(spec=MCPToolManager)

    @pytest.fixture
    def main_window(self, mock_config_manager, mock_mcp_manager, mock_mcp_tool_manager) -> MainWindow:
        """MainWindow 인스턴스 생성"""
        with patch('application.ui.main_window.ConfigManager', return_value=mock_config_manager):
            window = MainWindow(mock_mcp_manager, mock_mcp_tool_manager)
            return window

    def test_refresh_ui_elements_with_none_model_label(self, main_window: MainWindow):
        """model_label이 None일 때 refresh_ui_elements가 에러 없이 실행되는지 테스트"""
        # Given - model_label이 None인 상태
        main_window.model_label = None
        
        # When - refresh_ui_elements 실행
        try:
            main_window.refresh_ui_elements()
            # Then - 에러 없이 실행됨
            assert True
        except AttributeError as e:
            pytest.fail(f"model_label이 None일 때 AttributeError 발생: {e}")

    def test_refresh_ui_elements_without_model_label_attribute(self, main_window: MainWindow):
        """model_label 속성이 없을 때 refresh_ui_elements가 에러 없이 실행되는지 테스트"""
        # Given - model_label 속성이 없는 상태
        if hasattr(main_window, 'model_label'):
            delattr(main_window, 'model_label')
        
        # When - refresh_ui_elements 실행
        try:
            main_window.refresh_ui_elements()
            # Then - 에러 없이 실행됨
            assert True
        except AttributeError as e:
            pytest.fail(f"model_label 속성이 없을 때 AttributeError 발생: {e}")

    def test_refresh_ui_elements_with_valid_model_label(self, main_window: MainWindow):
        """model_label이 유효한 객체일 때 refresh_ui_elements가 정상 작동하는지 테스트"""
        # Given - model_label이 유효한 QLabel 객체
        from PySide6.QtWidgets import QLabel
        mock_label = Mock(spec=QLabel)
        main_window.model_label = mock_label
        
        # When - refresh_ui_elements 실행
        main_window.refresh_ui_elements()
        
        # Then - setStyleSheet이 호출됨
        mock_label.setStyleSheet.assert_called_once()

    def test_update_model_label_with_none_model_label(self, main_window: MainWindow):
        """model_label이 None일 때 update_model_label이 에러 없이 실행되는지 테스트"""
        # Given - model_label이 None인 상태
        main_window.model_label = None
        
        # When - update_model_label 실행
        try:
            main_window.update_model_label()
            # Then - 에러 없이 실행됨 (디버그 로그만 출력됨)
            assert True
        except AttributeError as e:
            pytest.fail(f"model_label이 None일 때 AttributeError 발생: {e}")

    def test_update_model_label_without_model_label_attribute(self, main_window: MainWindow):
        """model_label 속성이 없을 때 update_model_label이 에러 없이 실행되는지 테스트"""
        # Given - model_label 속성이 없는 상태
        if hasattr(main_window, 'model_label'):
            delattr(main_window, 'model_label')
        
        # When - update_model_label 실행
        try:
            main_window.update_model_label()
            # Then - 에러 없이 실행됨 (디버그 로그만 출력됨)
            assert True
        except AttributeError as e:
            pytest.fail(f"model_label 속성이 없을 때 AttributeError 발생: {e}")

    def test_update_model_label_with_valid_model_label(self, main_window: MainWindow):
        """model_label이 유효한 객체일 때 update_model_label이 정상 작동하는지 테스트"""
        # Given - model_label이 유효한 QLabel 객체
        from PySide6.QtWidgets import QLabel
        mock_label = Mock(spec=QLabel)
        main_window.model_label = mock_label
        
        # When - update_model_label 실행
        main_window.update_model_label()
        
        # Then - setText가 호출됨
        mock_label.setText.assert_called_once()
        call_args = mock_label.setText.call_args[0][0]
        assert "📋" in call_args
        assert "test-model" in call_args 