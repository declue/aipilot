import logging

import markdown
from PySide6.QtCore import QTimer

from application.ui.ai_chat_bubble import AIChatBubble
from application.ui.managers.streaming_html_renderer import \
    StreamingHtmlRenderer
from application.ui.managers.streaming_state import StreamingState
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("streaming_bubble_manager") or logging.getLogger(
    "streaming_bubble_manager"
)


class StreamingBubbleManager:
    """스트리밍 버블 UI를 관리하는 클래스"""

    def __init__(self, main_window, ui_config):
        self.main_window = main_window
        self.ui_config = ui_config
        self.html_renderer = StreamingHtmlRenderer(ui_config)

    def create_streaming_ai_bubble(self) -> AIChatBubble:
        """스트리밍용 AI 버블 생성"""
        # 마지막 스페이서 제거 (있다면)
        if self.main_window.chat_layout.count() > 0:
            last_item = self.main_window.chat_layout.itemAt(
                self.main_window.chat_layout.count() - 1
            )
            if last_item and last_item.spacerItem():
                self.main_window.chat_layout.removeItem(last_item)

        # 최신 UI 설정 사용
        current_ui_config = self.main_window.ui_config
        ai_bubble = AIChatBubble("▌", ui_config=current_ui_config)

        # 스트리밍용 속성 추가
        ai_bubble.is_streaming = True
        ai_bubble.streaming_content = ""
        ai_bubble.original_content = ""
        ai_bubble.original_message = ""

        # Raw 버튼 숨김 (스트리밍 완료 후 표시)
        if ai_bubble.toggle_button:
            ai_bubble.toggle_button.hide()

        # 채팅 컨테이너에 추가
        self.main_window.chat_layout.addWidget(ai_bubble)

        # MessageManager의 current_ai_bubble에도 설정
        self.main_window.message_manager.current_ai_bubble = ai_bubble

        # 스페이서 다시 추가
        self.main_window.chat_layout.addStretch()

        # 스크롤을 맨 아래로 (자동 스크롤 활성화 시에만)
        self.main_window.scroll_to_bottom()

        return ai_bubble

    def update_streaming_bubble(self, bubble: AIChatBubble, state: StreamingState):
        """스트리밍 버블 업데이트"""
        if not bubble or not state.streaming_content:
            return

        logger.debug(
            f"💬 버블 업데이트: {len(state.streaming_content)}자, 추론모델: {state.is_reasoning_model}"
        )

        text_browser = bubble.text_browser
        if not text_browser:
            return

        # 최신 UI 설정 사용
        current_ui_config = self.main_window.ui_config

        # 추론 모델인 경우와 일반 모델인 경우 구분
        if state.is_reasoning_model and state.reasoning_content:
            # HTML 렌더러도 최신 설정으로 업데이트
            self.html_renderer.ui_config = current_ui_config
            styled_html = self.html_renderer.create_streaming_reasoning_html(
                state.reasoning_content, state.final_answer
            )
        else:
            # 일반 스트리밍용 HTML
            self.html_renderer.ui_config = current_ui_config
            styled_html = self.html_renderer.create_regular_streaming_html(
                state.streaming_content
            )

        text_browser.setHtml(styled_html)
        bubble.adjust_browser_height(text_browser)

        # 스크롤을 맨 아래로 이동 (자동 스크롤 활성화 시에만)
        QTimer.singleShot(10, self.main_window.scroll_to_bottom)

    def finalize_bubble(
        self,
        bubble: AIChatBubble,
        final_content: str,
        is_reasoning_model: bool,
        reasoning_content: str,
        final_answer: str,
        used_tools: list,
    ):
        """버블 최종화"""
        if not bubble:
            return

        text_browser = bubble.text_browser
        if not text_browser:
            return

        # 최신 UI 설정 사용
        current_ui_config = self.main_window.ui_config

        # 도구 정보 설정 (있는 경우)
        if used_tools:
            bubble.set_used_tools(used_tools)

        # AIChatBubble의 원본 메시지 업데이트 (마크다운 변환 전에 저장)
        bubble.original_message = final_content
        logger.debug(f"finalize_bubble - original_message 설정: {len(final_content)}자")

        # 추론 모델인 경우 폴딩 가능한 UI 구성
        if is_reasoning_model and reasoning_content:
            # HTML 렌더러도 최신 설정으로 업데이트
            self.html_renderer.ui_config = current_ui_config
            styled_html = self.html_renderer.create_reasoning_html(
                reasoning_content, final_answer
            )
        else:
            # 일반 모델의 경우 기존 방식
            html_content = markdown.markdown(
                final_content,
                extensions=["codehilite", "fenced_code", "tables", "toc"],
            )
            styled_html = f"""
            <div style="
                color: #1F2937;
                line-height: 1.6;
                font-family: '{current_ui_config['font_family']}';
                font-size: {current_ui_config['font_size']}px;
            ">
                {html_content}
            </div>
            """

        text_browser.setHtml(styled_html)
        bubble.adjust_browser_height(text_browser)

        # 스트리밍 완료 표시
        bubble.is_streaming = False

        # 추론 관련 정보 설정
        bubble.set_reasoning_info(is_reasoning_model, reasoning_content, final_answer)

        # 새로운 메서드를 사용하여 메시지 내용 업데이트
        bubble.update_message_content(final_content)

        # Raw 버튼 표시
        bubble.show_raw_button()

        # 최종 스크롤 조정 (자동 스크롤 활성화 시에만)
        QTimer.singleShot(100, self.main_window.scroll_to_bottom)

    def show_stopped_bubble(self, bubble: AIChatBubble, content: str):
        """중단된 버블 표시"""
        if not bubble:
            return

        text_browser = bubble.text_browser
        if text_browser:
            final_html = self.html_renderer.create_stopped_html(content)
            text_browser.setHtml(final_html)
            bubble.adjust_browser_height(text_browser)
