from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

"""MessageManager – Domain Layer

채팅 버블 생성 및 관리 담당. 기존 managers 구현을 도메인 레이어로 이동하고
presentation 레이어의 버블 클래스를 사용하도록 경로를 수정했다.
"""

import logging

from PySide6.QtCore import QTimer

from application.ui.presentation.ai_chat_bubble import AIChatBubble
from application.ui.presentation.system_chat_bubble import SystemChatBubble
from application.ui.presentation.user_chat_bubble import UserChatBubble

logger: logging.Logger = logging.getLogger("message_manager")

if TYPE_CHECKING:
    from application.ui.presentation.ai_chat_bubble import AIChatBubble

class MessageManager:
    """메시지 추가/관리 담당 클래스 (Domain)"""

    def __init__(self, main_window: Any):
        self.main_window = main_window
        self.ui_config = main_window.ui_config
        self.current_ai_bubble: Optional["AIChatBubble"] = None  # 현재 스트리밍 중인 AI 버블 추적

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def add_user_message(self, message: str) -> None:
        """사용자 메시지 추가"""
        self._remove_trailing_spacer()
        current_ui_config = self.main_window.ui_config
        bubble = UserChatBubble(message, ui_config=current_ui_config)
        self.main_window.chat_layout.addWidget(bubble)
        self._append_spacer()
        self.main_window.scroll_to_bottom()

    def add_ai_message(self, message: str, used_tools: Optional[List[Any]] = None) -> None:
        """AI 메시지 추가 (스트리밍이 아닌 일반 응답)"""
        self._remove_trailing_spacer()
        current_ui_config = self.main_window.ui_config
        bubble = AIChatBubble(message, ui_config=current_ui_config)
        if used_tools:
            bubble.set_used_tools(used_tools)
        self.main_window.chat_layout.addWidget(bubble)
        self.current_ai_bubble = bubble
        bubble.show_raw_button()
        self._append_spacer()
        self.main_window.scroll_to_bottom()

    def add_github_message(self, message: str) -> None:
        """GitHub webhook 메시지 추가"""
        self._remove_trailing_spacer()
        current_ui_config = self.main_window.ui_config
        bubble = AIChatBubble.create_github_bubble(message, ui_config=current_ui_config)
        bubble.show_raw_button()
        self.main_window.chat_layout.addWidget(bubble)
        self._append_spacer()
        self.main_window.scroll_to_bottom()

    def add_system_message(self, message: str) -> None:
        """시스템 메시지 추가"""
        logger.debug("시스템 메시지 추가: %s...", message[:50])
        self._remove_trailing_spacer()
        current_ui_config = self.main_window.ui_config
        bubble = SystemChatBubble(message, ui_config=current_ui_config)
        self.main_window.chat_layout.addWidget(bubble)
        self._append_spacer()
        QTimer.singleShot(50, lambda: bubble.adjust_browser_height(bubble.text_browser))
        QTimer.singleShot(100, self.main_window.scroll_to_bottom)

    def add_html_message(self, html_content: str) -> None:
        """HTML 메시지 추가 (HTML 다이얼로그 알림용)"""
        logger.debug("HTML 메시지 추가: %s...", html_content[:50])
        self._remove_trailing_spacer()
        current_ui_config = self.main_window.ui_config
        bubble = SystemChatBubble(html_content, ui_config=current_ui_config, is_html=True)
        self.main_window.chat_layout.addWidget(bubble)
        self._append_spacer()
        QTimer.singleShot(50, lambda: bubble.adjust_browser_height(bubble.text_browser))
        QTimer.singleShot(100, self.main_window.scroll_to_bottom)

    def show_current_ai_raw_button(self) -> None:
        """현재 AI 버블의 Raw 버튼 표시 (스트리밍 완료 후 호출)"""
        if self.current_ai_bubble:
            self.current_ai_bubble.show_raw_button()
            logger.debug("Raw button shown for current AI bubble")
            self.current_ai_bubble = None

    def update_all_message_styles(self) -> None:
        """모든 메시지 스타일을 새로운 UI 설정으로 업데이트"""
        logger.debug("모든 메시지 스타일 업데이트 시작")
        self.ui_config = self.main_window.ui_config
        updated_count = 0
        for i in range(self.main_window.chat_layout.count()):
            item = self.main_window.chat_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget and hasattr(widget, "update_ui_config") and hasattr(widget, "update_styles"):
                widget.update_ui_config(self.ui_config)
                widget.update_styles()
                updated_count += 1
        logger.debug("총 %s개 버블 스타일 업데이트 완료", updated_count)
        if hasattr(self.main_window, "chat_area") and self.main_window.chat_area:
            self.main_window.chat_area.updateGeometry()
            self.main_window.chat_area.update()
        if hasattr(self.main_window, "scroll_area") and self.main_window.scroll_area:
            self.main_window.scroll_area.updateGeometry()
            self.main_window.scroll_area.update()

    def clear_chat_area(self) -> None:
        """채팅 영역 비우기"""
        for i in reversed(range(self.main_window.chat_layout.count())):
            item = self.main_window.chat_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                else:
                    self.main_window.chat_layout.removeItem(item)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _remove_trailing_spacer(self) -> None:
        if self.main_window.chat_layout.count() > 0:
            last_item = self.main_window.chat_layout.itemAt(self.main_window.chat_layout.count() - 1)
            if last_item and last_item.spacerItem():
                self.main_window.chat_layout.removeItem(last_item)

    def _append_spacer(self) -> None:
        self.main_window.chat_layout.addStretch() 