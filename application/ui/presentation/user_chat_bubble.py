from __future__ import annotations

"""UserChatBubble – Presentation Layer

기존 `application.ui.user_chat_bubble` 구현을 이동.
"""

# pylint: disable=too-many-lines

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

from application.ui.chat_bubble import ChatBubble
from application.util.logger import setup_logger
from application.util.markdown_manager import MarkdownManager

logger: logging.Logger = setup_logger("ui") or logging.getLogger("ui")


class UserChatBubble(ChatBubble):
    """사용자 메시지 채팅 버블 (Presentation)"""

    def __init__(
        self,
        message: str,
        ui_config: Optional[dict] = None,
        parent: Optional[QFrame] = None,
    ) -> None:
        self.raw_mode: bool = False
        super().__init__(message, ui_config, parent)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def setup_ui(self) -> None:  # noqa: D401
        """사용자 메시지 UI 레이아웃 설정"""
        try:
            self.setContentsMargins(0, 0, 0, 0)
            layout: QHBoxLayout = QHBoxLayout(self)
            logger.debug("Setting up USER bubble")
            layout.setContentsMargins(8, 16, 8, 16)
            layout.setSpacing(16)
            layout.addStretch()
            self._setup_user_bubble(layout)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to setup UI layout: %s", exc)
            raise RuntimeError("UI setup failed") from exc

    # pylint: disable=too-many-locals,too-many-statements
    def _setup_user_bubble(self, layout: QHBoxLayout) -> None:
        """실제 버블 위젯 구성"""
        try:
            bubble_frame: QFrame = QFrame()
            max_width: int = self.get_max_width()
            bubble_frame.setMaximumWidth(max_width)
            # 버블 프레임 참조 저장 및 테마 적용
            self.bubble_frame = bubble_frame
            self._update_bubble_theme()

            bubble_layout: QVBoxLayout = QVBoxLayout(bubble_frame)
            bubble_layout.setContentsMargins(12, 12, 12, 12)
            bubble_layout.setSpacing(8)

            # 버튼 영역
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

            # 텍스트 영역
            text_browser: QTextBrowser = QTextBrowser()
            text_browser.setMaximumWidth(max_width - 16)
            self._apply_content_to_browser(text_browser)
            text_browser.setStyleSheet(self._get_user_stylesheet())
            text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            text_browser.document().setDocumentMargin(0)
            text_browser.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            text_browser.document().setTextWidth(max_width - 16)
            text_browser.setFixedHeight(int(text_browser.document().size().height()) + 5)
            bubble_layout.addWidget(text_browser)
            self.text_browser = text_browser
            layout.addWidget(bubble_frame, 1)
            logger.debug("User bubble setup completed")
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to setup user bubble: %s", exc)
            raise RuntimeError("User bubble setup failed") from exc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _apply_content_to_browser(self, text_browser: QTextBrowser) -> None:
        try:
            md_manager = MarkdownManager()
            html_content, _ = md_manager.convert_with_syntax_highlighting(self.message)
            simple_html = f"<p>{self.message.strip()}</p>"
            if html_content.strip() == simple_html:
                html_content = self.message.replace("\n", "<br>")
            font_family, font_size = self.get_font_config()
            styled_html = (
                f"<div style=\"font-family:'{font_family}';font-size:{font_size}px;line-height:1.6;color:#FFFFFF;\">{html_content}</div>"
            )
            text_browser.setHtml(styled_html)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Markdown conversion failed: %s", exc)
            text_browser.setPlainText(self.message)

    def _get_user_stylesheet(self) -> str:
        font_family, font_size = self.get_font_config()
        code_font: int = max(font_size - 1, 12)
        return (
            f"""
            QTextBrowser {{
                background-color: transparent;
                border: none;
                font-family: '{font_family}';
                font-size: {font_size}px;
                color: #FFFFFF;
            }}
            QTextBrowser code {{
                background: rgba(255,255,255,0.2);
                border-radius: 4px;
                padding: 2px 4px;
                font-size: {code_font}px;
            }}
        """
        )

    # ------------------------------------------------------------------
    # Actions
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
            self._apply_content_to_browser(self.text_browser)
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update_styles(self) -> None:
        if not self.text_browser:
            return
        font_family, font_size = self.get_font_config()
        self.text_browser.setStyleSheet(self._get_user_stylesheet())
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
            logger.error(f"사용자 버블 테마 업데이트 실패: {e}")

    def _update_bubble_theme(self) -> None:
        """버블 프레임의 테마를 업데이트합니다."""
        colors = self.get_theme_colors()
        if hasattr(self, 'bubble_frame'):
            self.bubble_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.get('primary', '#2563EB')};
                    border-radius: 20px;
                }}
            """)

    def _update_text_browser_theme(self) -> None:
        """텍스트 브라우저의 테마를 업데이트합니다."""
        if hasattr(self, 'text_browser'):
            self.text_browser.setStyleSheet(self._get_user_stylesheet())

    def _update_button_theme(self) -> None:
        """버튼들의 테마를 업데이트합니다."""
        button_style = """
            QPushButton {
                background-color: rgba(255,255,255,0.2);
                color: white;
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 8px;
                font-size: 11px;
                font-weight: 500;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.3);
            }
        """
        
        if hasattr(self, 'copy_button'):
            self.copy_button.setStyleSheet(button_style)
        if hasattr(self, 'toggle_button'):
            self.toggle_button.setStyleSheet(button_style)


__all__: list[str] = ["UserChatBubble"] 