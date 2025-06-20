"""기본 핸들러 클래스"""

import logging
from abc import ABC
from typing import Any, Dict

from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager
from application.ui.signals.notification_signals import NotificationSignals
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("base_handler") or logging.getLogger(
    "base_handler"
)


class BaseHandler(ABC):
    """모든 API 핸들러의 기본 클래스"""

    def __init__(
        self,
        mcp_manager: MCPManager,
        mcp_tool_manager: MCPToolManager,
        notification_signals: NotificationSignals,
    ):
        self.mcp_manager = mcp_manager
        self.mcp_tool_manager = mcp_tool_manager
        self.notification_signals = notification_signals
        self.logger = logger

    def _create_success_response(
        self, message: str, data: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """성공 응답 생성"""
        response: Dict[str, Any] = {"status": "success", "message": message}
        if data:
            response["data"] = data
        return response

    def _create_error_response(
        self, message: str, exception: Exception | None = None
    ) -> Dict[str, Any]:
        """오류 응답 생성"""
        if exception and self.logger:
            self.logger.error("%s: %s", message, exception)

        return {
            "status": "error",
            "message": f"{message}: {str(exception)}" if exception else message,
        }

    def _log_request(self, endpoint: str, data: Any = None):
        """요청 로깅"""
        if self.logger:
            if data:
                self.logger.debug("API 요청 - %s: %s", endpoint, str(data)[:100])
            else:
                self.logger.debug("API 요청 - %s", endpoint)
