from __future__ import annotations

"""AIChatBubble – Presentation Layer

최소 standalone 구현.
기존 레거시 버전(수백 라인)을 단계적으로
이곳으로 이전하기 전에, 우선 BaseChatBubble 을 상속한
간단한 메시지 렌더러를 제공해 순환 import 를 제거한다.
"""

import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QTextBrowser, QVBoxLayout

from application.ui.presentation.base_chat_bubble import ChatBubble
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("ai_chat_bubble") or logging.getLogger("ai_chat_bubble")


class AIChatBubble(ChatBubble):  # pylint: disable=too-many-ancestors
    """간단한 AI 응답 채팅 버블.

    완전한 기능(Markdown 하이라이트, raw/markdown 토글, 툴 정보 표시 등)은
    향후 단계에서 다시 채워넣는다. 현재는 최소한의 QTextBrowser 로 내용을
    렌더링하여 UI 가 깨지지 않도록 보장하는 수준이다.
    """

    AVATAR_ICON = "🤖"
    AVATAR_SIZE = 40

    def __init__(
        self,
        message: str,
        ui_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QFrame] = None,
        avatar_icon: Optional[str] = None,
    ) -> None:
        self.avatar_icon = avatar_icon or self.AVATAR_ICON
        # streaming related defaults (for compatibility with legacy managers)
        self.is_streaming: bool = False
        self.streaming_content: str = ""
        self.original_content: str = ""
        self.original_message: str = message
        super().__init__(message=message, ui_config=ui_config, parent=parent)

    # ------------------------------------------------------------------
    # ChatBubble overrides
    # ------------------------------------------------------------------
    def setup_ui(self) -> None:  # noqa: D401 – Not a docstring test target
        """QFrame 기반의 간단한 좌측 정렬 버블 UI 작성."""
        self.setContentsMargins(0, 0, 0, 0)
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        # Avatar (이모지 아이콘)
        avatar_lbl = QLabel(self.avatar_icon)
        avatar_lbl.setFixedSize(self.AVATAR_SIZE, self.AVATAR_SIZE)
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        root_layout.addWidget(avatar_lbl)

        # Bubble container
        bubble_frame: QFrame = QFrame()
        bubble_frame.setStyleSheet(
            """
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }"""
        )
        bubble_layout = QVBoxLayout(bubble_frame)
        bubble_layout.setContentsMargins(12, 8, 12, 8)

        # Text area
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)
        # word wrap
        text_browser.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        font_family, font_size = self.get_font_config()
        text_browser.setStyleSheet(
            f"QTextBrowser {{ background: transparent; border: none; font-family: '{font_family}'; font-size: {font_size}px; }}"
        )
        text_browser.setHtml(self.message.replace("\n", "<br>"))
        bubble_layout.addWidget(text_browser)

        # expose for external managers
        self.text_browser: QTextBrowser = text_browser  # type: ignore
        self.toggle_button = None  # legacy placeholder

        root_layout.addWidget(bubble_frame)
        root_layout.addStretch()

    # ------------------------------------------------------------------
    # Convenience factory (GitHub icon etc.) – stubbed
    # ------------------------------------------------------------------
    @staticmethod
    def create_github_bubble(  # type: ignore[override]
        message: str,
        ui_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QFrame] = None,
    ) -> "AIChatBubble":
        """현재는 아이콘만 바꾼 동일 버전의 버블을 반환한다."""
        return AIChatBubble(message=message, ui_config=ui_config, parent=parent, avatar_icon="🐱")

    # ------------------------------------------------------------------
    # Legacy-API compatibility (no-op stubs)
    # ------------------------------------------------------------------
    def adjust_browser_height(self, browser: QTextBrowser) -> None:  # noqa: D401
        """Resize browser height to fit its document (simple version)."""
        doc_height = browser.document().size().height()
        browser.setFixedHeight(int(doc_height) + 20)

    def show_raw_button(self) -> None:  # noqa: D401
        """Legacy stub (no UI toggle in slim version)."""
        pass

    def set_used_tools(self, _tools: list[Any] | None = None) -> None:  # noqa: D401
        """Store tools list for later (unused)."""
        self._used_tools = _tools  # type: ignore

    def set_reasoning_info(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
        """Stub for reasoning-model metadata."""
        pass

    def update_message_content(self, new_content: str) -> None:  # noqa: D401
        """Update displayed HTML with new content."""
        self.message = new_content
        if hasattr(self, "text_browser") and self.text_browser:
            self.text_browser.setHtml(new_content.replace("\n", "<br>"))


__all__: list[str] = ["AIChatBubble"] 