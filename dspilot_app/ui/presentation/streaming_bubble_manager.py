from __future__ import annotations

"""StreamingBubbleManager – Presentation Layer

UI 측 스트리밍 버블 관리 로직을 기존 managers에서 이동.
"""

import logging
from typing import Any, Dict, List

from PySide6.QtCore import QTimer

from application.ui.domain.streaming_state import StreamingState
from application.ui.presentation.ai_chat_bubble import AIChatBubble
from application.ui.presentation.streaming_html_renderer import StreamingHtmlRenderer
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("ui") or logging.getLogger("ui")


class StreamingBubbleManager:
    """스트리밍 버블 UI를 관리하는 클래스 (Presentation)"""

    def __init__(self, main_window: Any, ui_config: Dict[str, Any]):
        self.main_window = main_window
        self.ui_config: Dict[str, Any] = ui_config
        self.html_renderer: StreamingHtmlRenderer = StreamingHtmlRenderer(ui_config)

    # ---- 기존 구현 ----

    def create_streaming_ai_bubble(self) -> AIChatBubble:  # noqa: D401
        """스트리밍용 AI 버블 생성"""
        if self.main_window.chat_layout.count() > 0:
            last_item = self.main_window.chat_layout.itemAt(
                self.main_window.chat_layout.count() - 1
            )
            if last_item and last_item.spacerItem():
                self.main_window.chat_layout.removeItem(last_item)

        current_ui_config = self.main_window.ui_config
        ai_bubble = AIChatBubble("▌", ui_config=current_ui_config)

        ai_bubble.is_streaming = True
        ai_bubble.streaming_content = ""
        ai_bubble.original_content = ""
        ai_bubble.original_message = ""

        if ai_bubble.toggle_button:
            ai_bubble.toggle_button.hide()

        self.main_window.chat_layout.addWidget(ai_bubble)
        self.main_window.message_manager.current_ai_bubble = ai_bubble
        self.main_window.chat_layout.addStretch()
        self.main_window.scroll_to_bottom()

        return ai_bubble

    def update_streaming_bubble(self, bubble: AIChatBubble, state: StreamingState) -> None:
        """스트리밍 버블 업데이트"""
        if not bubble or not state.streaming_content:
            return

        logger.debug(
            "🔄 버블 업데이트: %s자, 추론모델: %s, 추론내용: %s자",
            len(state.streaming_content),
            state.is_reasoning_model,
            len(state.reasoning_content) if state.reasoning_content else 0,
        )

        text_browser = bubble.text_browser
        if not text_browser:
            return

        current_ui_config = self.main_window.ui_config

        # 추론 모델인 경우 추론 과정과 최종 답변을 분리해서 표시
        if state.is_reasoning_model and state.reasoning_content:
            self.html_renderer.ui_config = current_ui_config

            # 스트리밍 중에는 추론 과정을 "진행중" 상태로 표시
            is_reasoning_complete = (
                "</think>" in state.streaming_content
                or "</thinking>" in state.streaming_content
                or "</reasoning>" in state.streaming_content
            )

            styled_html = self.html_renderer.create_streaming_reasoning_html(
                state.reasoning_content, state.final_answer, is_complete=is_reasoning_complete
            )
        else:
            self.html_renderer.ui_config = current_ui_config
            styled_html = self.html_renderer.create_regular_streaming_html(state.streaming_content)

        text_browser.setHtml(styled_html)
        bubble.adjust_browser_height(text_browser)

        QTimer.singleShot(10, self.main_window.scroll_to_bottom)

    def finalize_bubble(
        self,
        bubble: AIChatBubble,
        final_content: str,
        is_reasoning_model: bool,
        reasoning_content: str,
        final_answer: str,
        used_tools: List[Any],
    ) -> None:
        """버블 최종화"""
        if not bubble:
            return

        text_browser = bubble.text_browser
        if not text_browser:
            return

        current_ui_config = self.main_window.ui_config

        if used_tools:
            bubble.set_used_tools(used_tools)

        # 최종 내용을 버블에 반영 (렌더링 전에 message 값 갱신)
        bubble.original_message = final_content
        bubble.message = final_content  # 이후 set_reasoning_info 에서 렌더링
        bubble.is_streaming = False

        logger.info(
            f"🔄 버블 최종화: 추론모델={is_reasoning_model}, 추론내용={len(reasoning_content)}자, 답변={len(final_answer)}자"
        )

        # 추론 정보를 먼저 설정 (렌더링이 포함됨)
        bubble.set_reasoning_info(is_reasoning_model, reasoning_content, final_answer)

        # 사용 도구 정보 표시
        if used_tools:
            bubble.show_raw_button()

        # 모든 설정이 완료된 후 높이 조정
        if text_browser:
            bubble.adjust_browser_height(text_browser)

    def show_stopped_bubble(self, bubble: AIChatBubble, content: str) -> None:
        """중단된 버블 표시"""
        if not bubble:
            return

        text_browser = bubble.text_browser
        if text_browser:
            final_html = self.html_renderer.create_stopped_html(content)
            text_browser.setHtml(final_html)
            bubble.adjust_browser_height(text_browser)

    # copy rest of methods without change ㅌ
