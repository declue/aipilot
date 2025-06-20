import logging

from fastapi import FastAPI, Query

from application.api.handlers import (
    ChatHandler,
    ConversationHandler,
    LLMHandler,
    MCPHandler,
    NotificationHandler,
    UIHandler,
)
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
    ):
        self.api_app = FastAPI(title="메신저 알림 API", version="1.0.0")
        self.notification_signals = notification_signals  # 호환성을 위해 유지

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

    def register_endpoints(self):
        """API 엔드포인트 등록"""
        # 기본 엔드포인트
        self.api_app.add_api_route("/", self.index)
        self.api_app.add_api_route("/health", self.health_check)

        # 알림 관련 엔드포인트 (NotificationHandler로 위임)
        self.api_app.add_api_route(
            "/notifications/info",
            self.notification_handler.send_info_notification,
            methods=["POST"],
        )
        self.api_app.add_api_route(
            "/notifications/warning",
            self.notification_handler.send_warning_notification,
            methods=["POST"],
        )
        self.api_app.add_api_route(
            "/notifications/error",
            self.notification_handler.send_error_notification,
            methods=["POST"],
        )
        self.api_app.add_api_route(
            "/notifications/confirm",
            self.notification_handler.send_confirm_notification,
            methods=["POST"],
        )
        self.api_app.add_api_route(
            "/notifications/auto",
            self.notification_handler.send_auto_notification,
            methods=["POST"],
        )

        # 시스템 알림 엔드포인트
        self.api_app.add_api_route(
            "/notifications/system",
            self.notification_handler.send_system_notification,
            methods=["POST"],
        )

        # 다이얼로그 알림 엔드포인트
        self.api_app.add_api_route(
            "/notifications/dialog",
            self.notification_handler.send_dialog_notification,
            methods=["POST"],
        )
        self.api_app.add_api_route(
            "/notifications/dialog/html",
            self.notification_handler.send_html_dialog,
            methods=["POST"],
        )

        # 채팅 관련 엔드포인트 (ChatHandler로 위임)
        self.api_app.add_api_route(
            "/chat/messages", self.chat_handler.add_chat_message, methods=["POST"]
        )
        self.api_app.add_api_route(
            "/chat/clear", self.chat_handler.clear_chat, methods=["POST"]
        )
        self.api_app.add_api_route(
            "/chat/history", self.chat_handler.chat_history_action, methods=["POST"]
        )

        # LLM 관련 엔드포인트 (LLMHandler로 위임)
        self.api_app.add_api_route(
            "/llm/request", self.llm_handler.send_llm_request, methods=["POST"]
        )
        self.api_app.add_api_route(
            "/llm/streaming", self.llm_handler.send_streaming_request, methods=["POST"]
        )

        # UI 설정 관련 엔드포인트 (UIHandler로 위임)
        self.api_app.add_api_route(
            "/ui/settings", self.ui_handler.update_ui_settings, methods=["POST"]
        )
        self.api_app.add_api_route(
            "/ui/settings", self.ui_handler.get_ui_settings, methods=["GET"]
        )
        self.api_app.add_api_route(
            "/ui/font-size", self.change_font_size, methods=["POST"]
        )

        # 대화 관련 엔드포인트 (ConversationHandler로 위임)
        self.api_app.add_api_route(
            "/conversation/new",
            self.conversation_handler.start_new_conversation,
            methods=["POST"],
        )
        self.api_app.add_api_route(
            "/conversation/save", self.save_conversation, methods=["POST"]
        )
        self.api_app.add_api_route(
            "/conversation/load", self.load_conversation, methods=["POST"]
        )

        # MCP 관련 엔드포인트 (MCPHandler로 위임)
        self.api_app.add_api_route(
            "/mcp/servers", self.mcp_handler.get_mcp_servers, methods=["GET"]
        )
        self.api_app.add_api_route(
            "/mcp/servers/{server_name}/status",
            self.mcp_handler.get_mcp_server_status,
            methods=["GET"],
        )
        self.api_app.add_api_route(
            "/mcp/servers/{server_name}/tools",
            self.mcp_handler.get_mcp_server_tools,
            methods=["GET"],
        )
        self.api_app.add_api_route(
            "/mcp/enabled", self.mcp_handler.get_enabled_mcp_servers, methods=["GET"]
        )

        # 호환성을 위한 기존 엔드포인트 (deprecated)
        self.api_app.add_api_route(
            "/notify",
            self.notification_handler.send_notification_legacy,
            methods=["POST"],
        )
        self.api_app.add_api_route(
            "/llm", self.llm_handler.send_llm_request_legacy, methods=["POST"]
        )

    def index(self):
        """루트 엔드포인트"""
        return {"message": "메신저 알림 API 서버가 실행 중입니다"}

    async def health_check(self):
        """헬스 체크 엔드포인트"""
        return {"status": "healthy", "message": "API 서버가 정상 작동 중입니다"}

    # Query 파라미터를 사용하는 엔드포인트들은 여기에 유지
    async def change_font_size(
        self, font_size: int = Query(..., description="폰트 크기 (8-72)")
    ):
        """폰트 크기 변경 (Query 파라미터 사용)"""
        return await self.ui_handler.change_font_size(font_size)

    async def save_conversation(
        self, file_path: str = Query(..., description="저장할 파일 경로")
    ):
        """대화 내용 저장 (Query 파라미터 사용)"""
        return await self.conversation_handler.save_conversation(file_path)

    async def load_conversation(
        self, file_path: str = Query(..., description="불러올 파일 경로")
    ):
        """대화 내용 불러오기 (Query 파라미터 사용)"""
        return await self.conversation_handler.load_conversation(file_path)
