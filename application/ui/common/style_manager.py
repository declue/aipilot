from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QLabel, QWidget

from application.ui.common.theme_manager import ThemeManager


class StyleManager:  # pylint: disable=too-few-public-methods
    """Static helpers to style Qt widgets (minimal stub)."""

    # 기본 색상 (테마 매니저가 없을 때 사용)
    BORDER_COLOR = "#D1D5DB"
    BG_GROUP = "#F8FAFC"
    FONT_COLOR = "#1F2937"
    
    # 테마 매니저 인스턴스
    _theme_manager: Optional[ThemeManager] = None

    # ------------------------------------------------------------------
    # Public static helpers referenced elsewhere
    # ------------------------------------------------------------------
    @classmethod
    def set_theme_manager(cls, theme_manager: ThemeManager) -> None:
        """테마 매니저를 설정합니다."""
        cls._theme_manager = theme_manager
    
    @classmethod
    def get_group_box_style(cls) -> str:  # noqa: D401
        """Return QSS for group boxes / frames."""
        if cls._theme_manager:
            colors = cls._theme_manager.get_theme_colors()
            return (
                "QGroupBox, QFrame {"
                f"  background-color: {colors['surface']};"
                f"  border: 1px solid {colors['border']};"
                "  border-radius: 8px;"
                "  padding: 8px;"
                f"  color: {colors['text']};"
                "}"
            )
        else:
            return (
                "QGroupBox, QFrame {"
                f"  background-color: {cls.BG_GROUP};"
                f"  border: 1px solid {cls.BORDER_COLOR};"
                "  border-radius: 8px;"
                "  padding: 8px;"
                "}"
            )

    @classmethod
    def style_label(cls, label: QLabel) -> None:  # noqa: D401
        """Apply basic label style."""
        if cls._theme_manager:
            colors = cls._theme_manager.get_theme_colors()
            label.setStyleSheet(f"color: {colors['text']}; font-weight: 600;")
        else:
            label.setStyleSheet(f"color: {cls.FONT_COLOR}; font-weight: 600;")

    @classmethod
    def style_input(cls, widget: QWidget) -> None:  # noqa: D401
        """Apply border styling to input widgets (LineEdit, ComboBox 등)."""
        if cls._theme_manager:
            style = cls._theme_manager.get_input_style()
            widget.setStyleSheet(style)
        else:
            widget.setStyleSheet(
                (
                    "QLineEdit, QComboBox, QSpinBox, QTextEdit {"
                    f"  border: 1px solid {cls.BORDER_COLOR};"
                    "  border-radius: 6px;"
                    "  padding: 4px;"
                    "}"
                )
            )

    @classmethod
    def style_button(cls, btn: QWidget) -> None:  # noqa: D401
        """Apply default button style."""
        if cls._theme_manager:
            style = cls._theme_manager.get_button_style()
            btn.setStyleSheet(style)
        else:
            btn.setStyleSheet(
                (
                    "QPushButton {"
                    "  background-color: #EEF2FF;"
                    f"  color: {cls.FONT_COLOR};"
                    "  border: 1px solid #C7D2FE;"
                    "  padding: 6px 12px;"
                    "  border-radius: 6px;"
                    "}"
                    "QPushButton:hover { background-color: #E0E7FF; }"
                    "QPushButton:pressed { background-color: #C7D2FE; }"
                )
            )


__all__: list[str] = ["StyleManager"] 