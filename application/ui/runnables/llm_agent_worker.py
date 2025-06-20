"""
LLM Agent Worker
LLMAgent를 QThreadPool에서 실행하기 위한 QRunnable 래퍼
"""

import asyncio
import logging

from PySide6.QtCore import QRunnable

from application.llm.llm_agent import LLMAgent
from application.ui.signals.worker_signals import WorkerSignals
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("llm_agent_worker") or logging.getLogger(
    "llm_agent_worker"
)


class LLMAgentWorker(QRunnable):
    """LLMAgent를 QThreadPool에서 실행하기 위한 워커"""

    def __init__(
        self,
        user_message: str,
        llm_agent: LLMAgent,
        callback,
    ):
        super().__init__()
        self.user_message = user_message
        self.llm_agent = llm_agent
        self.callback = callback
        self.signals = WorkerSignals()
        self.signals.result.connect(callback)
        self.signals.error.connect(self.handle_error)
        # 스트리밍 시그널 연결
        self.signals.streaming_started.connect(self.on_streaming_started)
        self.signals.streaming_chunk.connect(self.on_streaming_chunk)
        self.signals.streaming_finished.connect(self.on_streaming_finished)
        self.is_running = True

    def run(self):
        """백그라운드에서 LLM Agent 실행"""
        if not self.is_running:
            return

        try:
            logger.info(f"LLM Agent 워커 시작: {self.user_message[:50]}...")

            # 스트리밍 시작 시그널 발송
            if self.is_running:
                self.signals.streaming_started.emit()

            # 기존 이벤트 루프가 있는지 확인
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                # 새 이벤트 루프 생성
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                # LLM Agent로 응답 생성 (스트리밍 콜백 포함)
                result = loop.run_until_complete(
                    self.llm_agent.generate_response_streaming(
                        self.user_message, self._streaming_callback
                    )
                )

                if self.is_running:
                    logger.info("LLM Agent 응답 생성 완료")
                    self.signals.streaming_finished.emit()

                    # 응답과 도구 정보 분리
                    if isinstance(result, dict):
                        response = result.get("response", "")
                        used_tools = result.get("used_tools", [])

                        # 도구 정보도 함께 전달
                        self.signals.result.emit(
                            {"response": response, "used_tools": used_tools}
                        )
                    else:
                        self.signals.result.emit({"response": result, "used_tools": []})

            except Exception as inner_exception:
                if self.is_running:
                    error_msg = f"LLM Agent 실행 중 내부 오류: {str(inner_exception)}"
                    logger.error(error_msg)
                    self.signals.error.emit(error_msg)
            finally:
                # 이벤트 루프 정리 (신중하게)
                try:
                    if not loop.is_closed():
                        loop.close()
                except Exception as cleanup_exception:
                    logger.warning(f"이벤트 루프 정리 중 경고: {cleanup_exception}")

        except Exception as exception:
            if self.is_running:
                error_msg = f"LLM Agent 실행 오류: {str(exception)}"
                logger.error(error_msg)
                self.signals.error.emit(error_msg)
        finally:
            # 안전한 정리
            self.is_running = False

    def _streaming_callback(self, chunk: str):
        """스트리밍 콜백"""
        if self.is_running:
            self.signals.streaming_chunk.emit(chunk)

    def stop(self):
        """워커 중지"""
        logger.debug("LLM Agent 워커 중지 요청")
        self.is_running = False

    def on_streaming_started(self):
        """스트리밍 시작 처리"""
        if self.is_running:
            logger.info("LLM Agent 스트리밍 응답 시작")

    def on_streaming_chunk(self, chunk):
        """스트리밍 청크 처리"""
        if self.is_running:
            logger.debug(
                "LLM Agent 스트리밍 청크: %s...",
                chunk[:50] if len(chunk) > 50 else chunk,
            )

    def on_streaming_finished(self):
        """스트리밍 완료 처리"""
        if self.is_running:
            logger.info("LLM Agent 스트리밍 응답 완료")

    def handle_error(self, error_msg):
        """에러 처리"""
        logger.error(f"LLM Agent 워커 에러: {error_msg}")
