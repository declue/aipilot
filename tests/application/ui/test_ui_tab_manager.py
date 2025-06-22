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
        assert self.ui_tab_manager.scroll_area is None
        assert self.ui_tab_manager.font_group is None
        assert self.ui_tab_manager.chat_group is None
        assert self.ui_tab_manager.preview_group is None

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
        
        # 테마 색상 Mock 설정 (모든 필요한 키 포함)
        colors = {
            'background': '#FFFFFF',
            'surface': '#F9FAFB',
            'text': '#1F2937',
            'text_secondary': '#6B7280',
            'border': '#E5E7EB',
            'primary': '#2563EB',
            'primary_hover': '#1D4ED8',
            'input_background': '#FFFFFF'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = colors
        
        # When - UI 탭 생성
        tab = self.ui_tab_manager.create_ui_tab()
        
        # Then - 탭이 생성되고 위젯 참조가 저장됨
        assert tab == mock_tab
        assert self.ui_tab_manager.scroll_area is not None
        assert self.ui_tab_manager.font_group is not None
        assert self.ui_tab_manager.chat_group is not None
        assert self.ui_tab_manager.preview_group is not None

    def test_get_theme_colors_with_theme_manager(self):
        """테마 매니저가 있을 때 테마 색상 조회 테스트"""
        # Given - 테마 매니저 설정
        expected_colors = {
            'background': '#FFFFFF',
            'surface': '#F9FAFB',
            'text': '#1F2937',
            'border': '#E5E7EB',
            'primary': '#2563EB'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = expected_colors
        
        # When - 테마 색상 조회
        colors = self.ui_tab_manager._get_theme_colors()
        
        # Then - 테마 매니저의 색상이 반환됨
        assert colors == expected_colors
        self.mock_parent.theme_manager.get_theme_colors.assert_called_once()

    def test_get_theme_colors_without_theme_manager(self):
        """테마 매니저가 없을 때 기본 테마 색상 조회 테스트"""
        # Given - 테마 매니저 없음
        parent_without_theme = Mock()
        # theme_manager 속성이 없도록 설정
        del parent_without_theme.theme_manager
        ui_tab_manager = UITabManager(parent_without_theme)
        
        # When - 테마 색상 조회
        colors = ui_tab_manager._get_theme_colors()
        
        # Then - 기본 라이트 테마 색상이 반환됨 (실제 딕셔너리 반환)
        assert isinstance(colors, dict)
        assert colors['background'] == '#FFFFFF'
        assert colors['text'] == '#1F2937'
        assert colors['primary'] == '#2563EB'

    def test_get_font_combo_style_light_theme(self):
        """라이트 테마 폰트 콤보박스 스타일 테스트"""
        # Given - 라이트 테마 색상
        light_colors = {
            'border': '#E5E7EB',
            'input_background': '#FFFFFF',
            'text': '#1F2937',
            'primary': '#2563EB',
            'surface': '#F9FAFB',
            'text_secondary': '#6B7280'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = light_colors
        
        # When - 폰트 콤보박스 스타일 조회
        style = self.ui_tab_manager.get_font_combo_style()
        
        # Then - 라이트 테마 색상이 포함된 스타일이 반환됨
        assert '#E5E7EB' in style  # border
        assert '#FFFFFF' in style  # input_background
        assert '#1F2937' in style  # text
        assert '#2563EB' in style  # primary

    def test_get_font_combo_style_dark_theme(self):
        """다크 테마 폰트 콤보박스 스타일 테스트"""
        # Given - 다크 테마 색상
        dark_colors = {
            'border': '#4B5563',
            'input_background': '#374151',
            'text': '#F9FAFB',
            'primary': '#60A5FA',
            'surface': '#374151',
            'text_secondary': '#D1D5DB'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = dark_colors
        
        # When - 폰트 콤보박스 스타일 조회
        style = self.ui_tab_manager.get_font_combo_style()
        
        # Then - 다크 테마 색상이 포함된 스타일이 반환됨
        assert '#4B5563' in style  # border
        assert '#374151' in style  # input_background
        assert '#F9FAFB' in style  # text
        assert '#60A5FA' in style  # primary

    def test_get_slider_style_with_theme(self):
        """테마가 적용된 슬라이더 스타일 테스트"""
        # Given - 테마 색상
        colors = {
            'border': '#E5E7EB',
            'surface': '#F9FAFB',
            'primary': '#2563EB',
            'primary_hover': '#1D4ED8'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = colors
        
        # When - 슬라이더 스타일 조회
        style = self.ui_tab_manager.get_slider_style()
        
        # Then - 테마 색상이 포함된 스타일이 반환됨
        assert 'QSlider::groove:horizontal' in style
        assert 'QSlider::handle:horizontal' in style
        assert colors['border'] in style
        assert colors['surface'] in style
        assert colors['primary'] in style

    def test_get_size_label_style_with_theme(self):
        """테마가 적용된 크기 라벨 스타일 테스트"""
        # Given - 테마 색상
        colors = {'primary': '#2563EB'}
        self.mock_parent.theme_manager.get_theme_colors.return_value = colors
        
        # When - 크기 라벨 스타일 조회
        style = self.ui_tab_manager.get_size_label_style()
        
        # Then - 테마 색상이 포함된 스타일이 반환됨
        assert colors['primary'] in style
        assert 'font-weight: 600' in style
        assert 'min-width: 32px' in style

    def test_update_preview(self):
        """미리보기 업데이트 테스트"""
        # Given - 미리보기 라벨과 설정 위젯들이 있는 상태
        colors = {
            'text': '#1F2937',
            'surface': '#F9FAFB',
            'border': '#E5E7EB'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = colors
        
        # When - 미리보기 업데이트
        self.ui_tab_manager.update_preview()
        
        # Then - 미리보기 라벨의 스타일이 업데이트됨
        self.mock_parent.preview_label.setStyleSheet.assert_called()

    def test_update_theme_with_theme_manager(self):
        """테마 매니저가 있을 때 테마 업데이트 테스트"""
        # Given - Mock 위젯들 설정
        self.ui_tab_manager.scroll_area = Mock()
        self.ui_tab_manager.font_group = Mock()
        self.ui_tab_manager.chat_group = Mock()
        self.ui_tab_manager.preview_group = Mock()
        
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
        
        # Then - 모든 UI 컴포넌트들의 스타일이 업데이트됨
        assert self.mock_parent.font_family_combo.setStyleSheet.called
        assert self.mock_parent.font_size_slider.setStyleSheet.called
        assert self.mock_parent.bubble_width_slider.setStyleSheet.called
        assert self.mock_parent.preview_label.setStyleSheet.called

    def test_update_theme_without_theme_manager(self):
        """테마 매니저가 없을 때 테마 업데이트 테스트"""
        # Given - 테마 매니저가 없는 상태
        parent_without_theme = Mock()
        parent_without_theme.font_family_combo = Mock()
        parent_without_theme.font_size_slider = Mock()
        parent_without_theme.preview_label = Mock()
        parent_without_theme.bubble_width_slider = Mock()
        parent_without_theme.font_size_label = Mock()
        parent_without_theme.bubble_width_label = Mock()
        
        # Mock 폰트 설정
        mock_font = Mock()
        mock_font.family.return_value = "Arial"
        parent_without_theme.font_family_combo.currentFont.return_value = mock_font
        parent_without_theme.font_size_slider.value.return_value = 14
        
        ui_tab_manager = UITabManager(parent_without_theme)
        ui_tab_manager.scroll_area = Mock()
        ui_tab_manager.font_group = Mock()
        ui_tab_manager.chat_group = Mock()
        ui_tab_manager.preview_group = Mock()
        
        # When - 테마 업데이트 (예외 발생하지 않아야 함)
        ui_tab_manager.update_theme()
        
        # Then - 테마 매니저가 없을 때는 기본적으로 StyleManager에 의존하므로
        # 특정 동작보다는 예외가 발생하지 않는 것을 확인
        # UI 위젯들이 있다면 스타일이 적용되어야 함
        assert hasattr(ui_tab_manager, 'scroll_area')
        assert hasattr(ui_tab_manager, 'font_group')

    def test_apply_scroll_area_theme(self):
        """스크롤 영역 테마 적용 테스트"""
        # Given - Mock 스크롤 영역과 테마 색상
        mock_scroll_area = Mock()
        self.ui_tab_manager.scroll_area = mock_scroll_area
        
        colors = {
            'surface': '#F9FAFB',
            'border': '#E5E7EB',
            'text_secondary': '#6B7280'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = colors
        
        # When - 스크롤 영역 테마 적용
        self.ui_tab_manager._apply_scroll_area_theme()
        
        # Then - 스크롤 영역 스타일이 설정됨
        mock_scroll_area.setStyleSheet.assert_called()

    def test_apply_preview_theme(self):
        """미리보기 테마 적용 테스트"""
        # Given - 미리보기 라벨이 있는 상태
        colors = {
            'text': '#1F2937',
            'surface': '#F9FAFB',
            'border': '#E5E7EB'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = colors
        
        # When - 미리보기 테마 적용
        self.ui_tab_manager._apply_preview_theme()
        
        # Then - 미리보기 라벨 스타일이 설정됨
        self.mock_parent.preview_label.setStyleSheet.assert_called()
        call_args = self.mock_parent.preview_label.setStyleSheet.call_args[0][0]
        assert 'font-family:' in call_args
        assert 'font-size:' in call_args

    def test_update_font_combo_theme(self):
        """폰트 콤보박스 테마 업데이트 테스트"""
        # Given - 폰트 콤보박스가 있는 상태
        colors = {
            'primary': '#2563EB', 
            'text': '#1F2937',
            'border': '#E5E7EB',
            'input_background': '#FFFFFF',
            'surface': '#F9FAFB',
            'text_secondary': '#6B7280'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = colors
        
        # When - 폰트 콤보박스 테마 업데이트
        self.ui_tab_manager._update_font_combo_theme(colors)
        
        # Then - 폰트 콤보박스 스타일이 업데이트됨
        self.mock_parent.font_family_combo.setStyleSheet.assert_called()

    def test_update_sliders_theme(self):
        """슬라이더들 테마 업데이트 테스트"""
        # Given - 슬라이더들이 있는 상태
        colors = {
            'primary': '#2563EB',
            'border': '#E5E7EB',
            'surface': '#F9FAFB',
            'primary_hover': '#1D4ED8'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = colors
        
        # When - 슬라이더들 테마 업데이트
        self.ui_tab_manager._update_sliders_theme(colors)
        
        # Then - 모든 슬라이더와 라벨의 스타일이 업데이트됨
        self.mock_parent.font_size_slider.setStyleSheet.assert_called()
        self.mock_parent.bubble_width_slider.setStyleSheet.assert_called()
        self.mock_parent.font_size_label.setStyleSheet.assert_called()
        self.mock_parent.bubble_width_label.setStyleSheet.assert_called()

    @patch('application.ui.managers.style_manager.StyleManager.get_group_box_style')
    def test_update_group_boxes_theme(self, mock_get_style):
        """그룹박스들 테마 업데이트 테스트"""
        # Given - 그룹박스들이 생성된 상태
        mock_get_style.return_value = "mock_style"
        self.ui_tab_manager.font_group = Mock()
        self.ui_tab_manager.chat_group = Mock()
        self.ui_tab_manager.preview_group = Mock()
        
        colors = {'surface': '#F9FAFB', 'border': '#E5E7EB'}
        
        # When - 그룹박스들 테마 업데이트
        self.ui_tab_manager._update_group_boxes_theme(colors)
        
        # Then - 모든 그룹박스의 스타일이 업데이트됨
        self.ui_tab_manager.font_group.setStyleSheet.assert_called_with("mock_style")
        self.ui_tab_manager.chat_group.setStyleSheet.assert_called_with("mock_style")
        self.ui_tab_manager.preview_group.setStyleSheet.assert_called_with("mock_style")

    def test_theme_transition_light_to_dark(self):
        """라이트에서 다크 테마로 전환 테스트"""
        # Given - Mock 위젯들 설정
        self.ui_tab_manager.scroll_area = Mock()
        self.ui_tab_manager.font_group = Mock()
        self.ui_tab_manager.chat_group = Mock()
        self.ui_tab_manager.preview_group = Mock()
        
        # Mock 테마 매니저의 다크 테마 색상
        dark_colors = {
            'background': '#1F2937',
            'surface': '#374151',
            'text': '#F9FAFB',
            'border': '#4B5563',
            'primary': '#60A5FA',
            'primary_hover': '#3B82F6',
            'text_secondary': '#D1D5DB',
            'input_background': '#374151'
        }
        self.mock_parent.theme_manager.get_theme_colors.return_value = dark_colors
        
        # When - 다크 테마로 업데이트
        self.ui_tab_manager.update_theme()
        
        # Then - 모든 UI 컴포넌트가 다크 테마로 업데이트됨
        # 폰트 콤보박스 스타일 확인
        font_combo_call = self.mock_parent.font_family_combo.setStyleSheet.call_args[0][0]
        assert '#374151' in font_combo_call  # 다크 테마 input_background
        assert '#F9FAFB' in font_combo_call   # 다크 테마 text
        
        # 슬라이더 스타일 확인
        slider_call = self.mock_parent.font_size_slider.setStyleSheet.call_args[0][0]
        assert '#60A5FA' in slider_call       # 다크 테마 primary 