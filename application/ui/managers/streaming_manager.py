import logging

from PySide6.QtCore import QTimer

from application.ui.managers.reasoning_parser import ReasoningParser
from application.ui.managers.streaming_bubble_manager import \
    StreamingBubbleManager
from application.ui.managers.streaming_state import StreamingState
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("streaming_manager") or logging.getLogger(
    "streaming_manager"
)


class StreamingManager:
    """스트리밍 관련 처리를 조율하는 메인 클래스"""

    def __init__(self, main_window):
        self.main_window = main_window
        self.ui_config = main_window.ui_config

        # 각 책임별 매니저 초기화
        self.state = StreamingState()
        self.reasoning_parser = ReasoningParser()
        self.bubble_manager = StreamingBubbleManager(main_window, self.ui_config)

        # 실시간 업데이트를 위한 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.setSingleShot(False)

    def start_streaming(self):
        """스트리밍 시작"""
        logger.info("🎬 StreamingManager 스트리밍 시작")
        self.state.start_streaming()
        self.state.current_streaming_bubble = (
            self.bubble_manager.create_streaming_ai_bubble()
        )
        logger.info(f"📱 스트리밍 버블 생성: {self.state.current_streaming_bubble}")
        # 실시간 업데이트 타이머 시작 (50ms 간격)
        self.update_timer.start(50)

    def add_streaming_chunk(self, chunk: str):
        """스트리밍 청크 추가"""
        logger.debug(f"📦 StreamingManager 청크 추가: {chunk[:30]}...")
        self.state.add_chunk(chunk)

    def set_used_tools(self, used_tools: list):
        """사용된 도구 정보 설정"""
        self.state.used_tools = used_tools
        # 현재 스트리밍 버블에 도구 정보 전달
        if self.state.current_streaming_bubble and hasattr(
            self.state.current_streaming_bubble, "set_used_tools"
        ):
            self.state.current_streaming_bubble.set_used_tools(used_tools)

    def _update_display(self):
        """실시간으로 화면 업데이트"""
        if not self.state.is_streaming:
            return

        # 대기 중인 청크들 처리
        if not self.state.process_pending_chunks():
            return

        logger.debug(f"🔄 화면 업데이트: {len(self.state.streaming_content)}자")

        # 추론 과정 감지 및 분리
        is_reasoning, reasoning_content, final_answer = (
            self.reasoning_parser.parse_reasoning_content(self.state.streaming_content)
        )

        self.state.is_reasoning_model = is_reasoning
        self.state.reasoning_content = reasoning_content
        self.state.final_answer = final_answer

        if self.state.current_streaming_bubble:
            # 스트리밍 중에도 original_message 업데이트
            self.state.current_streaming_bubble.original_message = (
                self.state.streaming_content
            )
            self.bubble_manager.update_streaming_bubble(
                self.state.current_streaming_bubble, self.state
            )

    def finish_streaming(self, final_content: str):
        """스트리밍 완료"""
        if not self.state.is_streaming:
            return

        self.state.is_streaming = False
        self.update_timer.stop()

        # 최종 내용 파싱 (기존 추론 모델 상태 유지)
        prev_is_reasoning = self.state.is_reasoning_model
        prev_reasoning_content = self.state.reasoning_content
        prev_final_answer = self.state.final_answer

        self.state.streaming_content = final_content
        is_reasoning, reasoning_content, final_answer = (
            self.reasoning_parser.parse_reasoning_content(final_content)
        )

        self.state.is_reasoning_model = is_reasoning
        self.state.reasoning_content = reasoning_content
        self.state.final_answer = final_answer

        # 기존에 추론 모델로 감지되었다면 상태 유지
        if prev_is_reasoning and not self.state.is_reasoning_model:
            self.state.is_reasoning_model = True
            if len(prev_reasoning_content) > len(self.state.reasoning_content):
                self.state.reasoning_content = prev_reasoning_content
                self.state.final_answer = prev_final_answer

        # 버블 최종화
        self.bubble_manager.finalize_bubble(
            self.state.current_streaming_bubble,
            final_content,
            self.state.is_reasoning_model,
            self.state.reasoning_content,
            self.state.final_answer,
            self.state.used_tools,
        )

        # 상태 초기화
        self.state.reset()

    def stop_streaming(self):
        """스트리밍 중단"""
        if self.state.current_worker and self.state.is_streaming:
            logger.debug("AI 응답 중단 요청")
            self.state.current_worker.stop()
            self.state.is_streaming = False
            self.update_timer.stop()

            # 현재 스트리밍 버블이 있다면 중단 메시지 추가
            if self.state.current_streaming_bubble:
                self.bubble_manager.show_stopped_bubble(
                    self.state.current_streaming_bubble, self.state.streaming_content
                )

            # 상태 초기화
            self.state.reset()

    def on_streaming_finished(self):
        """스트리밍 완료 시 호출되는 메서드"""
        if self.state.is_streaming:
            logger.debug(
                f"🔄 스트리밍 완료 - 추론모델: {self.state.is_reasoning_model}, "
                f"추론내용: {len(self.state.reasoning_content)}자"
            )

            # 남은 청크들 마지막으로 처리
            self.state.process_pending_chunks()

            is_reasoning, reasoning_content, final_answer = (
                self.reasoning_parser.parse_reasoning_content(
                    self.state.streaming_content
                )
            )
            self.state.is_reasoning_model = is_reasoning
            self.state.reasoning_content = reasoning_content
            self.state.final_answer = final_answer

            # 스트리밍 완료 처리
            self.finish_streaming(self.state.streaming_content)

    # 기존 메서드들과의 호환성을 위한 프로퍼티들
    @property
    def current_streaming_bubble(self):
        return self.state.current_streaming_bubble

    @current_streaming_bubble.setter
    def current_streaming_bubble(self, value):
        self.state.current_streaming_bubble = value

    @property
    def streaming_content(self):
        return self.state.streaming_content

    @property
    def current_worker(self):
        return self.state.current_worker

    @current_worker.setter
    def current_worker(self, value):
        self.state.current_worker = value

    @property
    def is_streaming(self):
        return self.state.is_streaming

    @property
    def reasoning_content(self):
        return self.state.reasoning_content

    @property
    def final_answer(self):
        return self.state.final_answer

    @property
    def is_reasoning_model(self):
        return self.state.is_reasoning_model

    @property
    def used_tools(self):
        return self.state.used_tools

    # 하위 호환성을 위한 기존 메서드들
    def create_streaming_ai_bubble(self):
        """하위 호환성을 위한 메서드"""
        return self.bubble_manager.create_streaming_ai_bubble()

    def update_streaming_bubble(self, _content: str):
        """하위 호환성을 위한 메서드"""
        if self.state.current_streaming_bubble:
            self.bubble_manager.update_streaming_bubble(
                self.state.current_streaming_bubble, self.state
            )
