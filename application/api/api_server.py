import logging
from typing import Any, Dict

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from application.api.handlers import (
    ChatHandler,
    ConversationHandler,
    LLMHandler,
    MCPHandler,
    NotificationHandler,
    UIHandler,
)
from application.api.models import ConversationFileRequest, UIFontRequest
from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager
from application.ui.signals.notification_signals import NotificationSignals
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("api_app") or logging.getLogger("api_app")


class APIServer:
    """FastAPI 관련 로직을 담당하는 클래스 - 이제 핸들러들을 통해 기능을 위임"""

    def __init__(
        self,
        mcp_manager: MCPManager,
        mcp_tool_manager: MCPToolManager,
        notification_signals: NotificationSignals,
    ) -> None:
        self.api_app = FastAPI(
            title="메신저 알림 API", 
            version="1.0.0",
            description="AI 어시스턴트 메신저 알림 API 서버"
        )
        self.notification_signals = notification_signals

        # 핸들러 인스턴스 생성
        self.notification_handler = NotificationHandler(
            mcp_manager, mcp_tool_manager, notification_signals
        )
        self.llm_handler = LLMHandler(
            mcp_manager, mcp_tool_manager, notification_signals
        )
        self.chat_handler = ChatHandler(
            mcp_manager, mcp_tool_manager, notification_signals
        )
        self.ui_handler = UIHandler(mcp_manager, mcp_tool_manager, notification_signals)
        self.conversation_handler = ConversationHandler(
            mcp_manager, mcp_tool_manager, notification_signals
        )
        self.mcp_handler = MCPHandler(
            mcp_manager, mcp_tool_manager, notification_signals
        )

        # 전역 예외 핸들러 등록
        self.api_app.add_exception_handler(Exception, self._handle_unexpected_exception)

    def register_endpoints(self) -> None:
        """API 엔드포인트 등록"""
        # 기본 엔드포인트
        self.api_app.add_api_route("/", self.index, methods=["GET"])
        self.api_app.add_api_route("/health", self.health_check, methods=["GET"])

        # ------------------------------------------------------------------
        # 알림 관련 라우터
        # ------------------------------------------------------------------
        notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])
        notifications_router.add_api_route(
            "/info", self.notification_handler.send_info_notification, methods=["POST"]
        )
        notifications_router.add_api_route(
            "/warning", self.notification_handler.send_warning_notification, methods=["POST"]
        )
        notifications_router.add_api_route(
            "/error", self.notification_handler.send_error_notification, methods=["POST"]
        )
        notifications_router.add_api_route(
            "/confirm", self.notification_handler.send_confirm_notification, methods=["POST"]
        )
        notifications_router.add_api_route(
            "/auto", self.notification_handler.send_auto_notification, methods=["POST"]
        )
        notifications_router.add_api_route(
            "/system", self.notification_handler.send_system_notification, methods=["POST"]
        )
        notifications_router.add_api_route(
            "/dialog", self.notification_handler.send_dialog_notification, methods=["POST"]
        )
        notifications_router.add_api_route(
            "/dialog/html", self.notification_handler.send_html_dialog, methods=["POST"]
        )
        self.api_app.include_router(notifications_router)

        # ------------------------------------------------------------------
        # 채팅 관련 라우터
        # ------------------------------------------------------------------
        chat_router = APIRouter(prefix="/chat", tags=["chat"])
        chat_router.add_api_route("/messages", self.chat_handler.add_chat_message, methods=["POST"])
        chat_router.add_api_route("/clear", self.chat_handler.clear_chat, methods=["POST"])
        chat_router.add_api_route("/history", self.chat_handler.chat_history_action, methods=["POST"])
        self.api_app.include_router(chat_router)

        # ------------------------------------------------------------------
        # LLM 관련 라우터
        # ------------------------------------------------------------------
        llm_router = APIRouter(prefix="/llm", tags=["llm"])
        llm_router.add_api_route("/request", self.llm_handler.send_llm_request, methods=["POST"])
        llm_router.add_api_route("/streaming", self.llm_handler.send_streaming_request, methods=["POST"])
        self.api_app.include_router(llm_router)

        # ------------------------------------------------------------------
        # UI 설정 라우터
        # ------------------------------------------------------------------
        ui_router = APIRouter(prefix="/ui", tags=["ui"])
        ui_router.add_api_route("/settings", self.ui_handler.get_ui_settings, methods=["GET"])
        ui_router.add_api_route("/settings", self.ui_handler.update_ui_settings, methods=["POST"])
        ui_router.add_api_route("/font-size", self.ui_handler.change_font_size, methods=["POST"])
        self.api_app.include_router(ui_router)

        # ------------------------------------------------------------------
        # 대화 관련 라우터
        # ------------------------------------------------------------------
        convo_router = APIRouter(prefix="/conversation", tags=["conversation"])
        convo_router.add_api_route(
            "/new", self.conversation_handler.start_new_conversation, methods=["POST"]
        )
        convo_router.add_api_route(
            "/file", self.conversation_handler.handle_conversation_file_operation, methods=["POST"]
        )
        # 개별 엔드포인트도 유지 (호환성)
        convo_router.add_api_route(
            "/save", self.conversation_handler.save_conversation, methods=["POST"]
        )
        convo_router.add_api_route(
            "/load", self.conversation_handler.load_conversation, methods=["POST"]
        )
        self.api_app.include_router(convo_router)

        # ------------------------------------------------------------------
        # MCP 관련 라우터
        # ------------------------------------------------------------------
        mcp_router = APIRouter(prefix="/mcp", tags=["mcp"])
        mcp_router.add_api_route("/servers", self.mcp_handler.get_mcp_servers, methods=["GET"])
        mcp_router.add_api_route(
            "/servers/{server_name}/status", 
            self.mcp_handler.get_mcp_server_status, 
            methods=["GET"]
        )
        mcp_router.add_api_route(
            "/servers/{server_name}/tools", 
            self.mcp_handler.get_mcp_server_tools, 
            methods=["GET"]
        )
        mcp_router.add_api_route("/enabled", self.mcp_handler.get_enabled_mcp_servers, methods=["GET"])
        self.api_app.include_router(mcp_router)

        # ------------------------------------------------------------------
        # 호환성 유지용 레거시 엔드포인트
        # ------------------------------------------------------------------
        self.api_app.add_api_route(
            "/notify", 
            self.notification_handler.send_notification_legacy, 
            methods=["POST"]
        )
        self.api_app.add_api_route(
            "/llm", 
            self.llm_handler.send_llm_request_legacy, 
            methods=["POST"]
        )

    def index(self) -> Dict[str, str]:
        """루트 엔드포인트"""
        return {"message": "메신저 알림 API 서버가 실행 중입니다"}

    async def health_check(self) -> Dict[str, str]:
        """헬스 체크 엔드포인트"""
        return {"status": "healthy", "message": "API 서버가 정상 작동 중입니다"}

    # ---------------------------------------------------------------------
    # 내부: 전역 예외 처리
    # ---------------------------------------------------------------------

    @staticmethod
    async def _handle_unexpected_exception(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        """예상하지 못한 예외를 JSON 형태로 변환"""
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error", 
                "message": f"서버 내부 오류: {str(exc)}",
                "type": "internal_server_error"
            },
        )
