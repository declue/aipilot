"""
BaseAgent를 QThreadPool에서 실행하기 위한 QRunnable 래퍼
"""

import asyncio
import logging
from typing import Any, Callable, Optional

from PySide6.QtCore import QRunnable, Slot

from dspilot_app.ui.signals.worker_signals import WorkerSignals
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.util.logger import setup_logger

logger: logging.Logger = setup_logger("ui") or logging.getLogger("ui")


class LLMAgentWorker(QRunnable):
    """BaseAgent를 QThreadPool에서 실행하기 위한 워커"""

    def __init__(
        self: "LLMAgentWorker",
        user_message: str,
        llm_agent: BaseAgent,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__()
        self.user_message = user_message
        self.llm_agent = llm_agent
        self.streaming_callback = streaming_callback
        self.signals = WorkerSignals()
        self.signals.result.connect(self.handle_result)
        self.signals.error.connect(self.handle_error)
        # 스트리밍 시그널 연결
        self.signals.streaming_started.connect(self.on_streaming_started)
        self.signals.streaming_chunk.connect(self.on_streaming_chunk)
        self.signals.streaming_finished.connect(self.on_streaming_finished)
        # 실제 스트리밍 데이터 전송 여부를 추적하여, 단일 응답(비-스트리밍)도
        # UI 버블에 표시되도록 한다.
        self._has_streamed: bool = False
        self.is_running = True

    def stop(self) -> None:
        """워커 중지"""
        logger.info("LLM Agent 워커 중지 요청됨")
        self.is_running = False
        if self.llm_agent:
            self.llm_agent.cancel()

    @Slot()
    def run(self) -> None:
        """워커 실행"""
        if not self.is_running:
            return

        try:
            logger.info(f"LLM Agent 워커 시작: {self.user_message[:50]}...")

            # 스트리밍 시작 시그널 발송
            if self.is_running:
                self.signals.streaming_started.emit()

            # 새 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 비동기 메서드 실행
                result = loop.run_until_complete(
                    self.llm_agent.generate_response(self.user_message, self.streaming_callback)
                )
                self.signals.finished.emit(result)

                if self.is_running:
                    logger.info("LLM Agent 응답 생성 완료")

                    # 응답과 도구 정보 분리
                    if isinstance(result, dict):
                        response = result.get("response", "")
                        used_tools = result.get("used_tools", [])
                        reasoning = result.get("reasoning", "")
                        logger.debug(f"응답 파싱 결과: response={len(response)}자, tools={used_tools}, reasoning={len(reasoning)}자")
                    else:
                        response = result
                        used_tools = []
                        logger.debug(f"단순 응답: {len(str(response))}자")

                    # 스트리밍 데이터 전송 여부 로그
                    logger.debug(f"스트리밍 여부: has_streamed={self._has_streamed}, response_length={len(response) if response else 0}")

                    # 스트리밍 단계에서 단 한 글자도 전달되지 않은 경우(예: 비-스트리밍
                    # 워크플로우/도구 응답), 최종 응답 전체를 한 번에 스트리밍 청크로 전송해
                    # UI 버블이 내용을 갖도록 한다.
                    if not self._has_streamed and response:
                        logger.info(f"비스트리밍 응답을 스트리밍 청크로 전송: {len(response)}자")
                        self.signals.streaming_chunk.emit(response)
                        self._has_streamed = True
                    elif not self._has_streamed and not response:
                        logger.warning("⚠️ 스트리밍도 없고 최종 응답도 비어있음!")
                    elif self._has_streamed:
                        logger.debug("스트리밍으로 이미 전송됨")

                    # result(최종 응답) 신호를 먼저 전달
                    final_result = {"response": response, "used_tools": used_tools}
                    logger.debug(f"최종 결과 전송: {final_result}")
                    self.signals.result.emit(final_result)

                    # 모든 데이터가 UI 측에 전달된 뒤에 스트리밍 종료 신호 전송
                    self.signals.streaming_finished.emit()

            except Exception as inner_exception:
                if self.is_running:
                    error_msg = f"LLM Agent 실행 중 내부 오류: {str(inner_exception)}"
                    logger.error(error_msg)
                    import traceback
                    logger.error(f"LLM Agent 내부 오류 상세: {traceback.format_exc()}")
                    self.signals.error.emit(error_msg)
            finally:
                loop.close()

        except Exception as exception:
            if self.is_running:
                error_msg = f"LLM Agent 실행 오류: {str(exception)}"
                logger.error(error_msg)
                import traceback
                logger.error(f"LLM Agent 외부 오류 상세: {traceback.format_exc()}")
                self.signals.error.emit(error_msg)
        finally:
            # 안전한 정리
            self.is_running = False

    def on_streaming_started(self) -> None:
        """스트리밍 시작 처리"""
        if self.is_running:
            logger.info("LLM Agent 스트리밍 응답 시작")

    def on_streaming_chunk(self, chunk: str) -> None:
        """스트리밍 청크 처리"""
        if self.is_running:
            logger.debug(
                "LLM Agent 스트리밍 청크: %s...",
                chunk[:50] if len(chunk) > 50 else chunk,
            )

    def on_streaming_finished(self) -> None:
        """스트리밍 완료 처리"""
        if self.is_running:
            logger.info("LLM Agent 스트리밍 응답 완료")

    def handle_result(self, result: Any) -> None:
        """결과 처리"""
        if self.is_running:
            logger.info("LLM Agent 응답 생성 완료")
            self.signals.finished.emit(result)

    def handle_error(self, error_msg: str) -> None:
        """에러 처리"""
        logger.error(f"LLM Agent 워커 에러: {error_msg}")
        self.signals.error.emit(error_msg)
        self.signals.finished.emit({"response": f"오류가 발생했습니다: {error_msg}", "used_tools": []})
