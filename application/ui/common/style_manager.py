from __future__ import annotations

"""StyleManager – Common Layer

PySide6 위젯에 일관된 스타일을 적용하기 위한 헬퍼.
현재 단계에서는 UI-Tab 매니저에서 호출되는 최소 메서드만 제공한다.
필요 시 점진적으로 확장한다.
"""

from PySide6.QtWidgets import QLabel, QWidget


class StyleManager:  # pylint: disable=too-few-public-methods
    """Static helpers to style Qt widgets (minimal stub)."""

    BORDER_COLOR = "#D1D5DB"
    BG_GROUP = "#F8FAFC"
    FONT_COLOR = "#1F2937"

    # ------------------------------------------------------------------
    # Public static helpers referenced elsewhere
    # ------------------------------------------------------------------
    @staticmethod
    def get_group_box_style() -> str:  # noqa: D401
        """Return QSS for group boxes / frames."""
        return (
            "QGroupBox, QFrame {"
            f"  background-color: {StyleManager.BG_GROUP};"
            f"  border: 1px solid {StyleManager.BORDER_COLOR};"
            "  border-radius: 8px;"
            "  padding: 8px;"
            "}"
        )

    @staticmethod
    def style_label(label: QLabel) -> None:  # noqa: D401
        """Apply basic label style."""
        label.setStyleSheet(f"color: {StyleManager.FONT_COLOR}; font-weight: 600;")

    @staticmethod
    def style_input(widget: QWidget) -> None:  # noqa: D401
        """Apply border styling to input widgets (LineEdit, ComboBox 등)."""
        widget.setStyleSheet(
            (
                "QLineEdit, QComboBox, QSpinBox, QTextEdit {"
                f"  border: 1px solid {StyleManager.BORDER_COLOR};"
                "  border-radius: 6px;"
                "  padding: 4px;"
                "}"
            )
        )

    @staticmethod
    def style_button(btn: QWidget) -> None:  # noqa: D401
        """Apply default button style."""
        btn.setStyleSheet(
            (
                "QPushButton {"
                "  background-color: #EEF2FF;"
                f"  color: {StyleManager.FONT_COLOR};"
                "  border: 1px solid #C7D2FE;"
                "  padding: 6px 12px;"
                "  border-radius: 6px;"
                "}"
                "QPushButton:hover { background-color: #E0E7FF; }"
                "QPushButton:pressed { background-color: #C7D2FE; }"
            )
        )


__all__: list[str] = ["StyleManager"] 