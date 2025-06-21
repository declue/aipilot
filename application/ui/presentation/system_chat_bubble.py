from __future__ import annotations

"""SystemChatBubble – Presentation Layer

기존 `application.ui.system_chat_bubble` 구현을 이동.
"""

# pylint: disable=too-many-lines

import logging
from typing import Optional

import markdown
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

from application.ui.chat_bubble import ChatBubble
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("system_chat_bubble") or logging.getLogger(
    "system_chat_bubble"
)


class SystemChatBubble(ChatBubble):
    """시스템 메시지 채팅 버블 (Presentation)"""

    AVATAR_ICON = "⚙️"
    AVATAR_SIZE = 40

    def __init__(
        self,
        message: str,
        ui_config: Optional[dict] = None,
        is_html: bool = False,
        parent: Optional[QFrame] = None,
    ) -> None:
        self.is_html = is_html
        self.raw_mode: bool = False
        super().__init__(message, ui_config, parent)

    # ------------------------------------------------------------------
    def setup_ui(self) -> None:  # noqa: D401
        try:
            self.setContentsMargins(0, 0, 0, 0)
            layout: QHBoxLayout = QHBoxLayout(self)
            logger.debug("Setting up SYSTEM bubble")
            layout.setContentsMargins(8, 16, 8, 16)
            layout.setSpacing(16)
            self._setup_system_bubble(layout)
            layout.addStretch()
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to setup UI layout: %s", exc)
            raise RuntimeError("UI setup failed") from exc

    # pylint: disable=too-many-locals,too-many-statements
    def _setup_system_bubble(self, layout: QHBoxLayout) -> None:
        try:
            avatar: QLabel = QLabel(self.AVATAR_ICON)
            avatar.setFixedSize(self.AVATAR_SIZE, self.AVATAR_SIZE)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(
                """
                QLabel {
                    background-color: #F59E0B;
                    border-radius: 20px;
                    font-size: 18px;
                    color: white;
                    font-weight: bold;
                }
            """
            )
            layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)

            bubble_container: QFrame = QFrame()
            bubble_container_layout = QVBoxLayout(bubble_container)
            bubble_container_layout.setContentsMargins(0, 0, 0, 0)
            bubble_container_layout.setSpacing(0)

            message_bubble_frame: QFrame = QFrame()
            max_width: int = self.get_max_width()
            message_bubble_frame.setMaximumWidth(max_width)
            # 버블 프레임 참조 저장 및 테마 적용
            self.bubble_frame = message_bubble_frame
            self._update_bubble_theme()
            bubble_layout: QVBoxLayout = QVBoxLayout(message_bubble_frame)
            bubble_layout.setContentsMargins(12, 16, 12, 16)
            bubble_layout.setSpacing(8)

            button_container = QFrame()
            button_container.setStyleSheet("QFrame{background:transparent;border:none;}")
            btn_layout = QHBoxLayout(button_container)
            btn_layout.setContentsMargins(0, 8, 0, 0)
            btn_layout.addStretch()

            self.toggle_button = QPushButton("📝")
            self.toggle_button.setMinimumSize(32, 28)
            self.toggle_button.setToolTip("RAW 전환")
            self.toggle_button.clicked.connect(self.toggle_raw_mode)  # type: ignore

            self.copy_button = QPushButton("📋")
            self.copy_button.setMinimumSize(32, 28)
            self.copy_button.setToolTip("내용 복사")
            self.copy_button.clicked.connect(self.copy_content)  # type: ignore
            
            # 버튼 테마 적용
            self._update_button_theme()

            btn_layout.addWidget(self.copy_button)
            btn_layout.addSpacing(4)
            btn_layout.addWidget(self.toggle_button)
            bubble_layout.addWidget(button_container)

            self.text_browser: QTextBrowser = QTextBrowser()
            self.text_browser.setMaximumWidth(max_width - 16)

            html_content = self.message if self.is_html else self._convert_markdown()
            self.text_browser.setHtml(html_content)
            self.text_browser.setStyleSheet(self._get_markdown_stylesheet())
            self.text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.text_browser.document().setDocumentMargin(0)
            self.text_browser.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            self.text_browser.document().setTextWidth(max_width - 16)
            self.text_browser.setFixedHeight(int(self.text_browser.document().size().height()) + 5)
            bubble_layout.addWidget(self.text_browser)
            bubble_container_layout.addWidget(message_bubble_frame)
            layout.addWidget(bubble_container, 1)
            logger.debug("System bubble setup completed")
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to setup system bubble: %s", exc)
            raise RuntimeError("System bubble setup failed") from exc

    # ------------------------------------------------------------------
    def _convert_markdown(self) -> str:
        try:
            html = markdown.markdown(
                self.message,
                extensions=[
                    "markdown.extensions.tables",
                    "markdown.extensions.fenced_code",
                    "markdown.extensions.nl2br",
                ],
            )
            font_family, font_size = self.get_font_config()
            return (
                f"<div style=\"font-family:'{font_family}';font-size:{font_size}px;line-height:1.6;color:#1F2937;\">{html}</div>"
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Markdown to HTML failed: %s", exc)
            return self.message

    def _get_markdown_stylesheet(self) -> str:
        font_family, font_size = self.get_font_config()
        code_font: int = max(font_size - 1, 12)
        return (
            f"""
            QTextBrowser {{
                background-color: transparent;
                border: none;
                font-family: '{font_family}';
                font-size: {font_size}px;
            }}
            QTextBrowser code {{
                background-color: #F1F5F9;
                padding: 3px 6px;
                border-radius: 6px;
                font-size: {code_font}px;
            }}
        """
        )

    # ------------------------------------------------------------------
    def toggle_raw_mode(self) -> None:  # noqa: D401
        if not self.text_browser:
            return
        self.raw_mode = not self.raw_mode
        if self.raw_mode:
            self.toggle_button.setText("🎨")
            self.text_browser.setPlainText(self.message)
        else:
            self.toggle_button.setText("📝")
            html_content = self.message if self.is_html else self._convert_markdown()
            self.text_browser.setHtml(html_content)
            self.text_browser.setStyleSheet(self._get_markdown_stylesheet())
        self.text_browser.update()
        self.update()

    def copy_content(self) -> None:  # noqa: D401
        clipboard = QApplication.clipboard()
        clipboard.setText(self.message if not self.raw_mode else self.text_browser.toPlainText())
        original = self.copy_button.text() if self.copy_button else "📋"
        if self.copy_button:
            self.copy_button.setText("✅")
            from threading import Timer

            Timer(1, lambda: self.copy_button.setText(original)).start()

    def adjust_browser_height(self, text_browser: QTextBrowser) -> None:  # noqa: D401
        if not text_browser:
            return
        doc_height = int(text_browser.document().size().height())
        text_browser.setFixedHeight(min(doc_height + 5, 800))

    def update_styles(self) -> None:  # noqa: D401
        if not self.text_browser:
            return
        font_family, font_size = self.get_font_config()
        self.text_browser.setStyleSheet(self._get_markdown_stylesheet())
        self.text_browser.document().setDefaultFontFamily(font_family)  # type: ignore
        self.text_browser.document().setDefaultFontPointSize(font_size)  # type: ignore

    def update_theme_styles(self) -> None:
        """테마에 맞는 스타일을 적용합니다."""
        try:
            if hasattr(self, 'bubble_frame'):
                self._update_bubble_theme()
            if hasattr(self, 'text_browser'):
                self._update_text_browser_theme()
            if hasattr(self, 'copy_button'):
                self._update_button_theme()
            if hasattr(self, 'toggle_button'):
                self._update_button_theme()
        except Exception as e:
            logger.error(f"시스템 버블 테마 업데이트 실패: {e}")

    def _update_bubble_theme(self) -> None:
        """버블 프레임의 테마를 업데이트합니다."""
        colors = self.get_theme_colors()
        if hasattr(self, 'bubble_frame'):
            # 시스템 메시지는 경고 색상 사용
            self.bubble_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.get('warning_background', '#FEF3C7')};
                    border: 1px solid {colors.get('warning', '#F59E0B')};
                    border-radius: 20px;
                }}
            """)

    def _update_text_browser_theme(self) -> None:
        """텍스트 브라우저의 테마를 업데이트합니다."""
        if hasattr(self, 'text_browser'):
            self.text_browser.setStyleSheet(self._get_markdown_stylesheet())

    def _update_button_theme(self) -> None:
        """버튼들의 테마를 업데이트합니다."""
        colors = self.get_theme_colors()
        button_style = f"""
            QPushButton {{
                background-color: {colors.get('button_background', '#F3F4F6')};
                color: {colors.get('warning_text', '#92400E')};
                border: 1px solid {colors.get('warning', '#D97706')};
                border-radius: 8px;
                font-size: 11px;
                font-weight: 500;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {colors.get('button_hover', '#E5E7EB')};
            }}
        """
        
        if hasattr(self, 'copy_button'):
            self.copy_button.setStyleSheet(button_style)
        if hasattr(self, 'toggle_button'):
            self.toggle_button.setStyleSheet(button_style)


__all__: list[str] = ["SystemChatBubble"]