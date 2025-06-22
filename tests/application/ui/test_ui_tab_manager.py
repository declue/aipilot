"""UI 탭 매니저 테스트 모듈"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from application.ui.common.theme_manager import ThemeManager, ThemeMode
from application.ui.managers.ui_tab_manager import UITabManager


class TestUITabManager:
    """UI 탭 매니저 테스트 클래스"""

    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        # Mock parent 생성
        self.mock_parent = Mock()
        self.mock_parent.theme_manager = Mock(spec=ThemeManager)
        
        # Mock UI 컴포넌트들
        self.mock_parent.font_family_combo = Mock()
        self.mock_parent.font_size_slider = Mock()
        self.mock_parent.font_size_label = Mock()
        self.mock_parent.bubble_width_slider = Mock()
        self.mock_parent.bubble_width_label = Mock()
        self.mock_parent.preview_label = Mock()
        
        # 기본 폰트 설정
        mock_font = Mock()
        mock_font.family.return_value = "Arial"
        self.mock_parent.font_family_combo.currentFont.return_value = mock_font
        self.mock_parent.font_size_slider.value.return_value = 14
        
        # UI 탭 매니저 생성
        self.ui_tab_manager = UITabManager(self.mock_parent)

    def test_ui_tab_manager_initialization(self):
        """UI 탭 매니저 초기화 테스트"""
        assert self.ui_tab_manager is not None
        assert self.ui_tab_manager.parent == self.mock_parent

    @patch('application.ui.managers.ui_tab_manager.QWidget')
    @patch('application.ui.managers.ui_tab_manager.QScrollArea')
    @patch('application.ui.managers.ui_tab_manager.QGroupBox')
    @patch('application.ui.managers.ui_tab_manager.QVBoxLayout')
    @patch('application.ui.managers.ui_tab_manager.QFormLayout')
    @patch('application.ui.managers.ui_tab_manager.QFontComboBox')
    @patch('application.ui.managers.ui_tab_manager.QSlider')
    @patch('application.ui.managers.ui_tab_manager.QLabel')
    @patch('application.ui.managers.ui_tab_manager.QHBoxLayout')
    def test_create_ui_tab(self, mock_hbox, mock_label, mock_slider, mock_font_combo, 
                          mock_form_layout, mock_vbox, mock_group_box, mock_scroll_area, mock_widget):
        """UI 탭 생성 테스트"""
        # Mock 설정
        mock_tab = Mock()
        mock_widget.return_value = mock_tab
        
        # When - UI 탭 생성
        tab = self.ui_tab_manager.create_ui_tab()
        
        # Then - 탭이 생성됨
        assert tab == mock_tab
        # UI 위젯들이 parent에 할당됨
        assert hasattr(self.mock_parent, 'font_family_combo')
        assert hasattr(self.mock_parent, 'font_size_slider')
        assert hasattr(self.mock_parent, 'preview_label')

    def test_get_font_combo_style(self):
        """폰트 콤보박스 스타일 테스트"""
        # When - 폰트 콤보박스 스타일 조회
        style = self.ui_tab_manager.get_font_combo_style()
        
        # Then - 스타일이 반환됨
        assert isinstance(style, str)
        assert 'QFontComboBox' in style
        assert 'border:' in style
        assert 'background-color:' in style

    def test_get_slider_style(self):
        """슬라이더 스타일 테스트"""
        # When - 슬라이더 스타일 조회
        style = self.ui_tab_manager.get_slider_style()
        
        # Then - 슬라이더 스타일이 반환됨
        assert isinstance(style, str)
        assert 'QSlider::groove:horizontal' in style
        assert 'QSlider::handle:horizontal' in style
        assert 'background-color:' in style

    def test_get_size_label_style(self):
        """크기 라벨 스타일 테스트"""
        # When - 크기 라벨 스타일 조회
        style = self.ui_tab_manager.get_size_label_style()
        
        # Then - 라벨 스타일이 반환됨
        assert isinstance(style, str)
        assert 'QLabel' in style
        assert 'font-weight:' in style
        assert 'min-width:' in style

    def test_update_preview(self):
        """미리보기 업데이트 테스트"""
        # Given - 폰트 설정
        mock_font = Mock()
        mock_font.family.return_value = "Arial"
        self.mock_parent.font_family_combo.currentFont.return_value = mock_font
        self.mock_parent.font_size_slider.value.return_value = 16
        
        # When - 미리보기 업데이트
        self.ui_tab_manager.update_preview()
        
        # Then - 미리보기 라벨의 스타일이 업데이트됨
        self.mock_parent.preview_label.setStyleSheet.assert_called_once()
        call_args = self.mock_parent.preview_label.setStyleSheet.call_args[0][0]
        assert 'Arial' in call_args
        assert '16px' in call_args

    def test_update_theme_with_theme_manager(self):
        """테마 매니저가 있을 때 테마 업데이트 테스트"""
        # Given - 테마 색상 설정
        colors = {
            'background': '#1F2937',
            'surface': '#374151',
            'text': '#F9FAFB',
            'border': '#4B5563',
            'primary': '#60A5FA',
            'primary_hover': '#3B82F6',
            'text_secondary': '#D1D5DB',
            'input_background': '#374151'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = colors
        
        # When - 테마 업데이트
        self.ui_tab_manager.update_theme()
        
        # Then - 테마 매니저의 색상 조회가 호출됨
        self.mock_parent.theme_manager.get_theme_colors.assert_called_once()

    def test_update_theme_without_theme_manager(self):
        """테마 매니저가 없을 때 테마 업데이트 테스트"""
        # Given - 테마 매니저 없는 parent
        parent_without_theme = Mock()
        # theme_manager 속성 제거
        if hasattr(parent_without_theme, 'theme_manager'):
            delattr(parent_without_theme, 'theme_manager')
        
        ui_tab_manager = UITabManager(parent_without_theme)
        
        # When - 테마 업데이트 (예외 발생하지 않아야 함)
        ui_tab_manager.update_theme()
        
        # Then - 예외 없이 완료됨
        assert True

    def test_update_preview_theme_with_colors(self):
        """색상이 주어졌을 때 미리보기 테마 업데이트 테스트"""
        # Given - 테마 색상
        colors = {
            'text': '#F9FAFB',
            'surface': '#374151',
            'border': '#4B5563'
        }
        
        # Mock 폰트 설정
        mock_font = Mock()
        mock_font.family.return_value = "Arial"
        self.mock_parent.font_family_combo.currentFont.return_value = mock_font
        self.mock_parent.font_size_slider.value.return_value = 14
        
        # When - 미리보기 테마 업데이트
        self.ui_tab_manager._update_preview_theme(colors)
        
        # Then - 미리보기 라벨의 스타일이 업데이트됨
        self.mock_parent.preview_label.setStyleSheet.assert_called_once()
        call_args = self.mock_parent.preview_label.setStyleSheet.call_args[0][0]
        assert colors['text'] in call_args
        assert colors['surface'] in call_args
        assert colors['border'] in call_args

    def test_update_scroll_area_theme(self):
        """스크롤 영역 테마 업데이트 테스트"""
        # Given - 테마 색상
        colors = {
            'surface': '#F9FAFB',
            'border': '#E5E7EB',
            'text_secondary': '#6B7280'
        }
        
        # When - 스크롤 영역 테마 업데이트 (현재는 pass로 구현됨)
        self.ui_tab_manager._update_scroll_area_theme(colors)
        
        # Then - 예외 없이 완료됨
        assert True

    def test_theme_integration_with_style_manager(self):
        """스타일 매니저와의 테마 통합 테스트"""
        # Given - 테마 매니저 설정
        colors = {
            'background': '#FFFFFF',
            'surface': '#F9FAFB',
            'text': '#1F2937',
            'border': '#E5E7EB',
            'primary': '#2563EB'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = colors
        
        # When - 테마 업데이트
        with patch('application.ui.managers.ui_tab_manager.StyleManager.set_theme_manager') as mock_set_theme:
            self.ui_tab_manager.update_theme()
            
            # Then - 스타일 매니저에 테마 매니저가 설정됨
            mock_set_theme.assert_called_once_with(self.mock_parent.theme_manager)

    def test_error_handling_in_update_theme(self):
        """테마 업데이트 중 오류 처리 테스트"""
        # Given - 테마 매니저에서 예외 발생
        self.mock_parent.theme_manager.get_theme_colors.side_effect = Exception("테마 로드 실패")
        
        # When - 테마 업데이트 (예외가 처리되어야 함)
        self.ui_tab_manager.update_theme()
        
        # Then - 예외가 처리되어 프로그램이 계속 실행됨
        assert True  # 예외가 발생하지 않으면 성공

    def test_font_combo_style_contains_required_elements(self):
        """폰트 콤보박스 스타일이 필수 요소를 포함하는지 테스트"""
        # When - 폰트 콤보박스 스타일 조회
        style = self.ui_tab_manager.get_font_combo_style()
        
        # Then - 필수 스타일 요소들이 포함됨
        required_elements = [
            'QFontComboBox {',
            'border:',
            'border-radius:',
            'padding:',
            'background-color:',
            'color:',
            'QFontComboBox:focus',
            'QFontComboBox::drop-down',
            'QFontComboBox QAbstractItemView'
        ]
        
        for element in required_elements:
            assert element in style, f"스타일에 '{element}'가 포함되어야 합니다"

    def test_slider_style_contains_required_elements(self):
        """슬라이더 스타일이 필수 요소를 포함하는지 테스트"""
        # When - 슬라이더 스타일 조회
        style = self.ui_tab_manager.get_slider_style()
        
        # Then - 필수 스타일 요소들이 포함됨
        required_elements = [
            'QSlider::groove:horizontal',
            'QSlider::handle:horizontal',
            'background-color:',
            'border:',
            'border-radius:'
        ]
        
        for element in required_elements:
            assert element in style, f"스타일에 '{element}'가 포함되어야 합니다" 