from unittest.mock import Mock, patch

import pytest

from application.config.config_manager import ConfigManager
from application.ui.common.theme_manager import ThemeManager, ThemeMode


class TestThemeManager:
    """테마 매니저 테스트 클래스"""

    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.config_manager = Mock(spec=ConfigManager)
        self.theme_manager = ThemeManager(self.config_manager)

    def test_theme_manager_initialization(self):
        """테마 매니저 초기화 테스트"""
        assert self.theme_manager is not None
        assert self.theme_manager.config_manager == self.config_manager
        assert self.theme_manager.current_theme == ThemeMode.LIGHT

    def test_get_current_theme(self):
        """현재 테마 조회 테스트"""
        # Given - 라이트 테마가 설정된 상태
        self.config_manager.get_ui_config.return_value = {'window_theme': 'light'}
        
        # When - 현재 테마를 조회
        theme = self.theme_manager.get_current_theme()
        
        # Then - 라이트 테마가 반환됨
        assert theme == ThemeMode.LIGHT

    def test_set_theme_to_dark(self):
        """다크 테마 설정 테스트"""
        # Given - 초기 라이트 테마 상태
        assert self.theme_manager.current_theme == ThemeMode.LIGHT
        self.config_manager.get_ui_config.return_value = {'window_theme': 'light'}
        
        # When - 다크 테마로 변경
        self.theme_manager.set_theme(ThemeMode.DARK)
        
        # Then - 다크 테마로 변경됨
        assert self.theme_manager.current_theme == ThemeMode.DARK
        self.config_manager.save_ui_config.assert_called_once()

    def test_set_theme_to_light(self):
        """라이트 테마 설정 테스트"""
        # Given - 다크 테마 상태
        self.theme_manager.current_theme = ThemeMode.DARK
        
        # When - 라이트 테마로 변경
        self.theme_manager.set_theme(ThemeMode.LIGHT)
        
        # Then - 라이트 테마로 변경됨
        assert self.theme_manager.current_theme == ThemeMode.LIGHT

    def test_toggle_theme_from_light_to_dark(self):
        """라이트에서 다크로 테마 토글 테스트"""
        # Given - 라이트 테마 상태
        self.theme_manager.current_theme = ThemeMode.LIGHT
        
        # When - 테마 토글
        new_theme = self.theme_manager.toggle_theme()
        
        # Then - 다크 테마로 변경됨
        assert new_theme == ThemeMode.DARK
        assert self.theme_manager.current_theme == ThemeMode.DARK

    def test_toggle_theme_from_dark_to_light(self):
        """다크에서 라이트로 테마 토글 테스트"""
        # Given - 다크 테마 상태
        self.theme_manager.current_theme = ThemeMode.DARK
        
        # When - 테마 토글
        new_theme = self.theme_manager.toggle_theme()
        
        # Then - 라이트 테마로 변경됨
        assert new_theme == ThemeMode.LIGHT
        assert self.theme_manager.current_theme == ThemeMode.LIGHT

    def test_get_theme_colors_light(self):
        """라이트 테마 색상 조회 테스트"""
        # Given - 라이트 테마 상태
        self.theme_manager.current_theme = ThemeMode.LIGHT
        
        # When - 테마 색상 조회
        colors = self.theme_manager.get_theme_colors()
        
        # Then - 라이트 테마 색상이 반환됨
        assert colors is not None
        assert 'background' in colors
        assert 'text' in colors
        assert 'border' in colors
        assert colors['background'] == '#FFFFFF'
        assert colors['text'] == '#1F2937'

    def test_get_theme_colors_dark(self):
        """다크 테마 색상 조회 테스트"""
        # Given - 다크 테마 상태
        self.theme_manager.current_theme = ThemeMode.DARK
        
        # When - 테마 색상 조회
        colors = self.theme_manager.get_theme_colors()
        
        # Then - 다크 테마 색상이 반환됨
        assert colors is not None
        assert 'background' in colors
        assert 'text' in colors
        assert 'border' in colors
        assert colors['background'] == '#1F2937'
        assert colors['text'] == '#F9FAFB'

    def test_get_button_style_light(self):
        """라이트 테마 버튼 스타일 조회 테스트"""
        # Given - 라이트 테마 상태
        self.theme_manager.current_theme = ThemeMode.LIGHT
        
        # When - 버튼 스타일 조회
        style = self.theme_manager.get_button_style()
        
        # Then - 라이트 테마 버튼 스타일이 반환됨
        assert isinstance(style, str)
        assert 'QPushButton' in style
        assert '#EEF2FF' in style  # 라이트 테마 버튼 배경색

    def test_get_button_style_dark(self):
        """다크 테마 버튼 스타일 조회 테스트"""
        # Given - 다크 테마 상태
        self.theme_manager.current_theme = ThemeMode.DARK
        
        # When - 버튼 스타일 조회
        style = self.theme_manager.get_button_style()
        
        # Then - 다크 테마 버튼 스타일이 반환됨
        assert isinstance(style, str)
        assert 'QPushButton' in style
        assert '#374151' in style  # 다크 테마 버튼 배경색

    def test_apply_theme_to_widget(self):
        """위젯에 테마 적용 테스트"""
        # Given - Mock 위젯 생성
        mock_widget = Mock()
        
        # When - 테마 적용
        self.theme_manager.apply_theme_to_widget(mock_widget)
        
        # Then - 위젯에 스타일이 적용됨
        mock_widget.setStyleSheet.assert_called_once()

    @patch('application.ui.common.theme_manager.QApplication.instance')
    def test_apply_global_theme(self, mock_app_instance):
        """전역 테마 적용 테스트"""
        # Given - Mock QApplication 인스턴스
        mock_app = Mock()
        mock_app_instance.return_value = mock_app
        
        # When - 전역 테마 적용
        self.theme_manager.apply_global_theme()
        
        # Then - 애플리케이션에 스타일시트가 적용됨
        mock_app.setStyleSheet.assert_called_once()

    def test_theme_changed_signal_emission(self):
        """테마 변경 시그널 발생 테스트"""
        # Given - 시그널 리스너 설정
        signal_received = False
        received_theme = None
        
        def on_theme_changed(theme):
            nonlocal signal_received, received_theme
            signal_received = True
            received_theme = theme
        
        self.theme_manager.theme_changed.connect(on_theme_changed)
        
        # When - 테마 변경
        self.theme_manager.set_theme(ThemeMode.DARK)
        
        # Then - 시그널이 발생함
        assert signal_received
        assert received_theme == ThemeMode.DARK 