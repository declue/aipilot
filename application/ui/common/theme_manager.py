from enum import Enum
from typing import Dict

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget

from application.config.config_manager import ConfigManager


class ThemeMode(Enum):
    """테마 모드 열거형"""

    LIGHT = "light"
    DARK = "dark"


class ThemeManager(QObject):
    """테마 관리 클래스

    다크/라이트 모드를 관리하고 UI 전반에 테마를 적용하는 역할을 담당합니다.
    ConfigManager를 통해 테마 설정을 저장하고 불러옵니다.
    """

    # 테마 변경 시그널
    theme_changed = Signal(ThemeMode)

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.current_theme = ThemeMode.LIGHT
        self._load_theme_from_config()

    def _load_theme_from_config(self) -> None:
        """설정에서 테마를 로드합니다."""
        try:
            ui_config = self.config_manager.get_ui_config()
            theme_value = ui_config.get("window_theme", "light")
            self.current_theme = ThemeMode(theme_value)
        except (KeyError, ValueError):
            self.current_theme = ThemeMode.LIGHT

    def get_current_theme(self) -> ThemeMode:
        """현재 테마를 반환합니다."""
        return self.current_theme

    def set_theme(self, theme: ThemeMode) -> None:
        """테마를 설정합니다."""
        if self.current_theme != theme:
            self.current_theme = theme
            self._save_theme_to_config()
            self.theme_changed.emit(theme)

    def toggle_theme(self) -> ThemeMode:
        """테마를 토글합니다."""
        new_theme = ThemeMode.DARK if self.current_theme == ThemeMode.LIGHT else ThemeMode.LIGHT
        self.set_theme(new_theme)
        return new_theme

    def _save_theme_to_config(self) -> None:
        """테마를 설정에 저장합니다."""
        try:
            ui_config = self.config_manager.get_ui_config()
            ui_config["window_theme"] = self.current_theme.value
            self.config_manager.save_ui_config(ui_config)
        except Exception:
            pass

    def get_theme_colors(self) -> dict[str, str]:
        """현재 테마의 색상 팔레트를 반환합니다."""
        if self.current_theme == ThemeMode.DARK:
            return self._get_dark_theme_colors()
        else:
            return self._get_light_theme_colors()

    def _get_light_theme_colors(self) -> dict[str, str]:
        """라이트 테마 색상 팔레트를 반환합니다."""
        return {
            "background": "#FFFFFF",
            "surface": "#F9FAFB",
            "text": "#1F2937",
            "text_secondary": "#6B7280",
            "border": "#E5E7EB",
            "border_light": "#F3F4F6",
            "primary": "#3B82F6",
            "primary_hover": "#2563EB",
            "primary_pressed": "#1D4ED8",
            "success": "#10B981",
            "success_hover": "#059669",
            "success_pressed": "#047857",
            "warning": "#F59E0B",
            "warning_background": "#FEF3C7",
            "warning_text": "#92400E",
            "danger": "#EF4444",
            "button_background": "#EEF2FF",
            "button_border": "#C7D2FE",
            "button_hover": "#E0E7FF",
            "button_pressed": "#C7D2FE",
            "input_background": "#FFFFFF",
            "header_background": "#FFFFFF",
            "chat_bubble_user": "#3B82F6",
            "chat_bubble_ai": "#F3F4F6",
            "scrollbar": "#D1D5DB",
            "scrollbar_hover": "#9CA3AF",
        }

    def _get_dark_theme_colors(self) -> Dict[str, str]:
        """다크 테마 색상 팔레트를 반환합니다."""
        return {
            "background": "#1F2937",
            "surface": "#374151",
            "text": "#F9FAFB",
            "text_secondary": "#D1D5DB",
            "border": "#4B5563",
            "border_light": "#6B7280",
            "primary": "#60A5FA",
            "primary_hover": "#3B82F6",
            "primary_pressed": "#2563EB",
            "success": "#34D399",
            "success_hover": "#10B981",
            "success_pressed": "#059669",
            "warning": "#FBBF24",
            "warning_background": "#451A03",
            "warning_text": "#FEF3C7",
            "danger": "#F87171",
            "button_background": "#374151",
            "button_border": "#4B5563",
            "button_hover": "#4B5563",
            "button_pressed": "#6B7280",
            "input_background": "#374151",
            "header_background": "#1F2937",
            "chat_bubble_user": "#3B82F6",
            "chat_bubble_ai": "#374151",
            "scrollbar": "#4B5563",
            "scrollbar_hover": "#6B7280",
        }

    def get_button_style(self) -> str:
        """현재 테마의 버튼 스타일을 반환합니다."""
        colors = self.get_theme_colors()
        return f"""
            QPushButton {{
                background-color: {colors['button_background']};
                color: {colors['text']};
                border: 1px solid {colors['button_border']};
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {colors['button_hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['button_pressed']};
            }}
        """

    def get_input_style(self) -> str:
        """현재 테마의 입력 위젯 스타일을 반환합니다."""
        colors = self.get_theme_colors()
        return f"""
            QLineEdit, QComboBox, QSpinBox, QTextEdit {{
                background-color: {colors['input_background']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 4px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {{
                border-color: {colors['primary']};
            }}
        """

    def get_window_style(self) -> str:
        """현재 테마의 윈도우 스타일을 반환합니다."""
        colors = self.get_theme_colors()
        return f"""
            QMainWindow {{
                background-color: {colors['background']};
                color: {colors['text']};
            }}
            QWidget {{
                background-color: {colors['background']};
                color: {colors['text']};
            }}
        """

    def get_header_style(self) -> str:
        """현재 테마의 헤더 스타일을 반환합니다."""
        colors = self.get_theme_colors()
        return f"""
            QFrame {{
                background-color: {colors['header_background']};
                border: none;
                border-bottom: 1px solid {colors['border']};
            }}
        """

    def get_chat_area_style(self) -> str:
        """현재 테마의 채팅 영역 스타일을 반환합니다."""
        colors = self.get_theme_colors()
        return f"""
            QScrollArea {{
                background-color: {colors['background']};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {colors['surface']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {colors['scrollbar']};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {colors['scrollbar_hover']};
            }}
        """

    def apply_theme_to_widget(self, widget: QWidget) -> None:
        """위젯에 현재 테마를 적용합니다."""
        if widget is None:
            return

        style = self.get_window_style()
        widget.setStyleSheet(style)

    def apply_global_theme(self) -> None:
        """애플리케이션 전체에 테마를 적용합니다."""
        app = QApplication.instance()
        if app:
            style = self.get_window_style()
            app.setStyleSheet(style)

    def get_theme_toggle_button_style(self) -> str:
        """테마 토글 버튼의 스타일을 반환합니다."""
        colors = self.get_theme_colors()
        icon = "🌙" if self.current_theme == ThemeMode.LIGHT else "☀️"
        return (
            f"""
            QPushButton {{
                background-color: {colors['button_background']};
                color: {colors['text']};
                border: 1px solid {colors['button_border']};
                border-radius: 20px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {colors['button_hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['button_pressed']};
            }}
        """,
            icon,
        )

    def is_dark_mode(self) -> bool:
        """다크 모드인지 확인합니다."""
        return self.current_theme == ThemeMode.DARK

    def is_light_mode(self) -> bool:
        """라이트 모드인지 확인합니다."""
        return self.current_theme == ThemeMode.LIGHT


__all__ = ["ThemeManager", "ThemeMode"]
