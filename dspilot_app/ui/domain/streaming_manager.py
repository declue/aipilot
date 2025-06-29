from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from PySide6.QtCore import QTimer

from dspilot_app.ui.domain.reasoning_parser import ReasoningParser
from dspilot_app.ui.domain.streaming_state import StreamingState
from dspilot_core.util.logger import setup_logger

logger: logging.Logger = setup_logger("ui") or logging.getLogger("ui")

if TYPE_CHECKING:
    from dspilot_app.ui.presentation.ai_chat_bubble import AIChatBubble
    from dspilot_app.ui.presentation.streaming_bubble_manager import StreamingBubbleManager


class StreamingManager:
    """스트리밍 관련 처리를 조율하는 메인 클래스 (Domain)"""

    def __init__(self, main_window: Any):
        self.main_window = main_window
        self.ui_config = main_window.ui_config

        # 각 책임별 매니저 초기화
        self.state: StreamingState = StreamingState()
        self.reasoning_parser: ReasoningParser = ReasoningParser()

        # Runtime import to avoid circular dependency
        from dspilot_app.ui.presentation.streaming_bubble_manager import StreamingBubbleManager

        self.bubble_manager: StreamingBubbleManager = StreamingBubbleManager(
            main_window, self.ui_config
        )

        # 실시간 업데이트를 위한 타이머
        self.update_timer: QTimer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.setSingleShot(False)

    # ------------------------------------------------------------------
    # 스트리밍 흐름 제어
    # ------------------------------------------------------------------
    def start_streaming(self) -> None:
        """스트리밍 시작"""
        logger.info("🎬 StreamingManager 스트리밍 시작")
        self.state.start_streaming()
        self.state.current_streaming_bubble = self.bubble_manager.create_streaming_ai_bubble()
        logger.info("📱 스트리밍 버블 생성: %s", self.state.current_streaming_bubble)
        # 실시간 업데이트 타이머 시작 (50 ms 간격)
        self.update_timer.start(50)

    def add_streaming_chunk(self, chunk: str) -> None:
        """스트리밍 청크 추가"""
        logger.debug("📦 StreamingManager 청크 추가: %s...", chunk[:30])
        self.state.add_chunk(chunk)

    def set_used_tools(self, used_tools: List[Any]) -> None:
        """사용된 도구 정보 설정"""
        self.state.used_tools = used_tools
        # 현재 스트리밍 버블에 도구 정보 전달
        if self.state.current_streaming_bubble and hasattr(
            self.state.current_streaming_bubble, "set_used_tools"
        ):
            self.state.current_streaming_bubble.set_used_tools(used_tools)

    # ------------------------------------------------------------------
    # 내부 동작
    # ------------------------------------------------------------------
    def _parse_and_update_reasoning_state(self, content: str) -> None:
        """추론 과정 감지 및 상태 업데이트"""
        (
            is_reasoning,
            reasoning_content,
            final_answer,
        ) = self.reasoning_parser.parse_reasoning_content(content)

        self.state.is_reasoning_model = is_reasoning
        self.state.reasoning_content = reasoning_content
        self.state.final_answer = final_answer

    def _update_display(self) -> None:
        """실시간으로 화면 업데이트"""
        if not self.state.is_streaming:
            return

        # 대기 중인 청크들 처리
        if not self.state.process_pending_chunks():
            return

        logger.debug("🔄 화면 업데이트: %s자", len(self.state.streaming_content))

        # 추론 과정 감지 및 분리
        self._parse_and_update_reasoning_state(self.state.streaming_content)

        if self.state.current_streaming_bubble:
            # 스트리밍 중에도 original_message 업데이트
            self.state.current_streaming_bubble.original_message = self.state.streaming_content
            self.bubble_manager.update_streaming_bubble(
                self.state.current_streaming_bubble, self.state
            )

    def finish_streaming(self, final_content: str) -> None:
        """스트리밍 완료"""
        if not self.state.is_streaming:
            return

        self.state.is_streaming = False
        self.update_timer.stop()

        # 디버깅을 위해 전체 응답 내용 로그 출력
        logger.info(f"🔍 스트리밍 완료 - 전체 응답 내용 ({len(final_content)}자):")
        logger.info(f"📝 응답 내용: {final_content}")

        # 최종 내용 파싱 (기존 추론 모델 상태 유지)
        prev_is_reasoning = self.state.is_reasoning_model
        prev_reasoning_content = self.state.reasoning_content
        prev_final_answer = self.state.final_answer

        self.state.streaming_content = final_content
        self._parse_and_update_reasoning_state(final_content)

        logger.info(
            f"🧠 파싱 결과 - 추론모델: {self.state.is_reasoning_model}, 추론내용: {len(self.state.reasoning_content)}자, 답변: {len(self.state.final_answer)}자"
        )

        # 기존에 추론 모델로 감지되었다면 상태 유지
        if prev_is_reasoning and not self.state.is_reasoning_model:
            self.state.is_reasoning_model = True
            if len(prev_reasoning_content) > len(self.state.reasoning_content):
                self.state.reasoning_content = prev_reasoning_content
                self.state.final_answer = prev_final_answer

        # 버블 최종화
        if self.state.current_streaming_bubble:
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

    def stop_streaming(self) -> None:
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

    def on_streaming_finished(self) -> None:
        """스트리밍 완료 시 호출되는 메서드 (Signal 연결용)"""
        if self.state.is_streaming:
            logger.debug(
                "🔄 스트리밍 완료 - 추론모델: %s, 추론내용: %s자",
                self.state.is_reasoning_model,
                len(self.state.reasoning_content),
            )

            # 남은 청크들 마지막으로 처리
            self.state.process_pending_chunks()

            self._parse_and_update_reasoning_state(self.state.streaming_content)

            # 스트리밍 완료 처리
            self.finish_streaming(self.state.streaming_content)

    # ------------------------------------------------------------------
    # 편의 프로퍼티 & 레거시 호환 메서드
    # ------------------------------------------------------------------
    def current_streaming_bubble(self) -> Any:  # noqa: D401
        return self.state.current_streaming_bubble

    def streaming_content(self) -> str:
        return self.state.streaming_content

    def current_worker(self) -> Any:
        return self.state.current_worker

    def is_streaming(self) -> bool:
        return self.state.is_streaming

    def reasoning_content(self) -> str:
        return self.state.reasoning_content

    def final_answer(self) -> str:
        return self.state.final_answer

    def is_reasoning_model(self) -> bool:
        return self.state.is_reasoning_model

    def used_tools(self) -> List[Any]:
        return self.state.used_tools

    # 하위 호환성을 위한 기존 메서드들
    def create_streaming_ai_bubble(self) -> "AIChatBubble":  # type: ignore[override]
        """하위 호환성 메서드 (기존 코드용)"""
        return self.bubble_manager.create_streaming_ai_bubble()

    def update_streaming_bubble(self, _content: str) -> None:
        """하위 호환성 메서드 (기존 코드용)"""
        if self.state.current_streaming_bubble:
            self.bubble_manager.update_streaming_bubble(
                self.state.current_streaming_bubble, self.state
            )
