import asyncio
import logging
import threading
import time
from typing import Any

import uvicorn
from fastapi import FastAPI
from PySide6.QtCore import QThread, Signal

from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("api") or logging.getLogger("api")


class FastAPIThread(QThread):
    """FastAPI 서버를 별도 스레드에서 실행하는 클래스"""

    # 시그널 정의
    server_started = Signal(str, int)  # host, port
    server_stopped = Signal()
    server_error = Signal(str)  # error_message

    def __init__(
        self,
        app_instance: FastAPI,
        host: str = "127.0.0.1",
        port: int = 8000,
        log_level: str = "info",
        access_log: bool = True,
    ) -> None:
        super().__init__()
        self.app_instance: FastAPI = app_instance
        self.host: str = host
        self.port: int = port
        self.log_level: str = log_level
        self.access_log: bool = access_log

        # 서버 상태 관리
        self._server: uvicorn.Server | None = None
        self._shutdown_event = threading.Event()
        self._server_started = False

        # 에러 카운터
        self._restart_count = 0
        self._max_restart_attempts = 3

    def run(self) -> None:
        """스레드에서 FastAPI 서버 실행"""
        try:
            self._run_server()
        except Exception as exception:
            error_msg = f"FastAPI 서버 실행 중 치명적 오류: {exception}"
            logger.error(error_msg, exc_info=True)
            self.server_error.emit(error_msg)

    def _run_server(self) -> None:
        """실제 서버 실행 로직"""
        while (
            not self._shutdown_event.is_set() and self._restart_count < self._max_restart_attempts
        ):
            try:
                logger.info(
                    "FastAPI 서버 시작 시도 (%d/%d): http://%s:%s",
                    self._restart_count + 1,
                    self._max_restart_attempts,
                    self.host,
                    self.port,
                )

                # uvicorn 설정
                config = uvicorn.Config(
                    app=self.app_instance,
                    host=self.host,
                    port=self.port,
                    log_level=self.log_level,
                    access_log=self.access_log,
                    loop="asyncio",
                    # 성능 최적화 설정
                    workers=1,
                    limit_concurrency=100,
                    limit_max_requests=1000,
                    timeout_keep_alive=30,
                )

                self._server = uvicorn.Server(config)

                # 서버 시작
                asyncio.run(self._start_server())

                if self._server_started:
                    logger.info("FastAPI 서버가 정상적으로 종료되었습니다")
                    self.server_stopped.emit()
                    break

            except Exception as exception:
                self._restart_count += 1
                error_msg = f"FastAPI 서버 오류 (시도 {self._restart_count}/{self._max_restart_attempts}): {exception}"
                logger.error(error_msg, exc_info=True)

                if self._restart_count < self._max_restart_attempts:
                    logger.info("5초 후 서버 재시작을 시도합니다...")
                    time.sleep(5)
                else:
                    logger.error("최대 재시작 횟수에 도달했습니다. 서버를 종료합니다.")
                    self.server_error.emit(f"서버 시작 실패: {exception}")
                    break

    async def _start_server(self) -> None:
        """비동기 서버 시작"""
        if not self._server:
            return

        try:
            # 서버 시작
            await self._server.serve()
            self._server_started = True
            self.server_started.emit(self.host, self.port)

        except Exception as exception:
            if not self._shutdown_event.is_set():
                logger.error("서버 시작 실패: %s", exception)
                raise

    def stop_server(self) -> None:
        """서버 안전 종료"""
        logger.info("FastAPI 서버 종료 요청")

        self._shutdown_event.set()

        if self._server:
            try:
                # 서버 종료 신호 전송
                if hasattr(self._server, "should_exit"):
                    self._server.should_exit = True

                # graceful shutdown을 위한 시간 대기
                self.wait(3000)  # 3초 대기

                if self.isRunning():
                    logger.warning("서버가 정상 종료되지 않아 강제 종료합니다")
                    self.terminate()
                    self.wait(1000)  # 1초 대기

            except Exception as exception:
                logger.error("서버 종료 중 오류: %s", exception)
                self.terminate()
                self.wait(1000)  # 강제 종료 후 대기

        # 스레드 정리 확인
        if self.isRunning():
            logger.warning("스레드가 여전히 실행 중입니다. 강제 종료를 시도합니다.")
            self.terminate()
            self.wait(2000)  # 2초 대기

        logger.info("FastAPI 스레드 종료 완료")

    def get_server_info(self) -> dict[str, Any]:
        """서버 정보 반환"""
        return {
            "host": self.host,
            "port": self.port,
            "log_level": self.log_level,
            "access_log": self.access_log,
            "is_running": self.isRunning(),
            "server_started": self._server_started,
            "restart_count": self._restart_count,
            "server_url": f"http://{self.host}:{self.port}",
        }

    def is_server_healthy(self) -> bool:
        """서버 상태 확인"""
        return self.isRunning() and self._server_started and not self._shutdown_event.is_set()

    def __del__(self) -> None:
        """소멸자 - 리소스 정리"""
        try:
            if self.isRunning():
                logger.debug("FastAPIThread 소멸자에서 서버 종료 실행")
                self.stop_server()
        except Exception as e:
            logger.error(f"FastAPIThread 소멸자에서 오류 발생: {e}")
        finally:
            # Python 가비지 컬렉터가 자동으로 정리
            pass
