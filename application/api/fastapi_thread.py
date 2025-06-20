import logging

import uvicorn
from fastapi import FastAPI
from PySide6.QtCore import QThread

from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("fastapi_thread") or logging.getLogger(
    "fastapi_thread"
)


class FastAPIThread(QThread):
    """FastAPI 서버를 별도 스레드에서 실행하는 클래스"""

    def __init__(
        self, app_instance: FastAPI, host: str = "127.0.0.1", port: int = 8000
    ) -> None:
        super().__init__()
        self.app_instance: FastAPI = app_instance
        self.host: str = host
        self.port: int = port

    def run(self) -> None:
        """스레드에서 FastAPI 서버 실행"""
        try:
            logger.info("FastAPI 서버 시작: http://%s:%s", self.host, self.port)
            uvicorn.run(
                self.app_instance,
                log_level="info",
                host=self.host,
                port=self.port,
            )
        except Exception as exception:
            logger.error("FastAPI 서버 실행 오류: %s", exception)

    def stop_server(self) -> None:
        """서버 종료"""
        logger.debug("FastAPI 서버 종료 요청")
        self.quit()
