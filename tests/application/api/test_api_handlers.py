"""API 핸들러 테스트"""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.api.handlers import *
from application.api.models import *


class MockMCPManager:
    """Mock MCP Manager"""
    
    def get_enabled_servers(self) -> Dict[str, Any]:
        return {"test_server": MagicMock()}
    
    def get_server_list(self) -> list[str]:
        return ["test_server"]
    
    def get_server(self, name: str) -> Any:
        return MagicMock(command="test", args=[], description="test", enabled=True)
    
    async def test_server_connection(self, name: str) -> Any:
        return MagicMock(
            connected=True, 
            tools=[], 
            resources=[], 
            prompts=[],
            error_message=""
        )


class MockMCPToolManager:
    """Mock MCP Tool Manager"""
    
    async def get_openai_tools(self) -> list[Any]:
        return []
    
    async def call_mcp_tool(self, tool_key: str, arguments: Dict[str, Any]) -> str:
        return "Tool executed successfully"


class MockNotificationSignals:
    """Mock Notification Signals"""
    
    def __init__(self) -> None:
        self.show_notification = MagicMock()
        self.add_api_message = MagicMock()
        self.clear_chat = MagicMock()
        self.save_chat = MagicMock()
        self.load_chat = MagicMock()
        self.trigger_llm_response = MagicMock()
        self.update_ui_settings = MagicMock()
        self.show_system_notification = MagicMock()
        self.show_dialog_notification = MagicMock()


@pytest.fixture
def mock_dependencies() -> Dict[str, Any]:
    """Mock 의존성들"""
    return {
        "mcp_manager": MockMCPManager(),
        "mcp_tool_manager": MockMCPToolManager(),
        "notification_signals": MockNotificationSignals()
    }


class TestChatHandler:
    """채팅 핸들러 테스트"""
    
    @pytest.fixture
    def chat_handler(self, mock_dependencies: Dict[str, Any]) -> ChatHandler:
        return ChatHandler(
            mock_dependencies["mcp_manager"],
            mock_dependencies["mcp_tool_manager"],
            mock_dependencies["notification_signals"]
        )
    
    @pytest.mark.asyncio
    async def test_add_chat_message_user(self, chat_handler: ChatHandler) -> None:
        """사용자 메시지 추가 테스트"""
        request = ChatMessageRequest(message="Hello", type="user")
        
        result = await chat_handler.add_chat_message(request)
        
        assert result["status"] == "success"
        assert "user 메시지가 추가되었습니다" in result["message"]
        assert result["data"]["type"] == "user"
        assert result["data"]["message"] == "Hello"
    
    @pytest.mark.asyncio  
    async def test_add_chat_message_invalid_type(self, chat_handler: Any) -> None:
        """잘못된 메시지 타입 테스트"""
        request = ChatMessageRequest(message="Hello", type="invalid")
        
        result = await chat_handler.add_chat_message(request)
        
        assert result["status"] == "error"
        assert "지원하지 않는 메시지 타입" in result["message"]
    
    @pytest.mark.asyncio
    async def test_clear_chat(self, chat_handler: Any) -> None:
        """채팅 지우기 테스트"""
        result = await chat_handler.clear_chat()
        
        assert result["status"] == "success"
        assert "채팅 내용이 지워졌습니다" in result["message"]
    
    @pytest.mark.asyncio
    async def test_chat_history_save(self, chat_handler: Any) -> None:
        """채팅 기록 저장 테스트"""
        request = ChatHistoryRequest(action="save", file_path="/test/path.json")
        
        result = await chat_handler.chat_history_action(request)
        
        assert result["status"] == "success"
        assert "저장되었습니다" in result["message"]


class TestUIHandler:
    """UI 핸들러 테스트"""
    
    @pytest.fixture
    def ui_handler(self, mock_dependencies: Dict[str, Any]) -> Any:
        return UIHandler(
            mock_dependencies["mcp_manager"],
            mock_dependencies["mcp_tool_manager"], 
            mock_dependencies["notification_signals"]
        )
    
    @pytest.mark.asyncio
    async def test_change_font_size_valid(self, ui_handler: Any) -> None:
        """유효한 폰트 크기 변경 테스트"""
        request = UIFontRequest(font_size=16)
        
        result = await ui_handler.change_font_size(request)
        
        assert result["status"] == "success"
        assert "16px로 변경되었습니다" in result["message"]
        assert result["data"]["font_size"] == 16
    
    @pytest.mark.asyncio
    async def test_change_font_size_validation(self) -> None:
        """폰트 크기 검증 테스트"""
        # Pydantic 모델 자체의 검증 테스트
        with pytest.raises(ValueError):
            UIFontRequest(font_size=100)  # 범위 초과
            
        with pytest.raises(ValueError):
            UIFontRequest(font_size=5)    # 범위 미만
    
    @pytest.mark.asyncio
    async def test_update_ui_settings(self, ui_handler: Any) -> None:
        """UI 설정 업데이트 테스트"""
        request = UISettingsRequest(
            font_family="Arial",
            font_size=14,
            theme="dark"
        )
        
        result = await ui_handler.update_ui_settings(request)
        
        assert result["status"] == "success"
        assert "업데이트되었습니다" in result["message"]
        assert "font_family" in result["data"]["updated_settings"]


class TestConversationHandler:
    """대화 핸들러 테스트"""
    
    @pytest.fixture
    def conversation_handler(self, mock_dependencies: Dict[str, Any]) -> Any:
        return ConversationHandler(
            mock_dependencies["mcp_manager"],
            mock_dependencies["mcp_tool_manager"], 
            mock_dependencies["notification_signals"]
        )
    
    @pytest.mark.asyncio
    async def test_save_conversation(self, conversation_handler: Any) -> None:
        """대화 저장 테스트"""
        request = ConversationFileRequest(file_path="/test/save.json", action="save")
        
        result = await conversation_handler.save_conversation(request)
        
        assert result["status"] == "success"
        assert "저장되었습니다" in result["message"]
        assert result["data"]["file_path"] == "/test/save.json"
    
    @pytest.mark.asyncio
    async def test_load_conversation(self, conversation_handler: Any) -> None:
        """대화 불러오기 테스트"""
        request = ConversationFileRequest(file_path="/test/load.json", action="load")
        
        result = await conversation_handler.load_conversation(request)
        
        assert result["status"] == "success"
        assert "불러와졌습니다" in result["message"]
        assert result["data"]["file_path"] == "/test/load.json"
    
    @pytest.mark.asyncio
    async def test_handle_conversation_file_operation_save(self, conversation_handler: Any) -> None:
        """통합 파일 작업 핸들러 - 저장 테스트"""
        request = ConversationFileRequest(file_path="/test/file.json", action="save")
        
        result = await conversation_handler.handle_conversation_file_operation(request)
        
        assert result["status"] == "success"
        assert "저장되었습니다" in result["message"]
    
    @pytest.mark.asyncio
    async def test_handle_conversation_file_operation_invalid_action(self, conversation_handler: Any) -> None:
        """통합 파일 작업 핸들러 - 잘못된 액션 테스트"""
        request = ConversationFileRequest(file_path="/test/file.json", action="invalid")
        
        result = await conversation_handler.handle_conversation_file_operation(request)
        
        assert result["status"] == "error"
        assert "지원하지 않는 작업" in result["message"]


class TestLLMHandler:
    """LLM 핸들러 테스트"""
    
    @pytest.fixture
    def llm_handler(self, mock_dependencies: Dict[str, Any]) -> Any:
        return LLMHandler(
            mock_dependencies["mcp_manager"],
            mock_dependencies["mcp_tool_manager"], 
            mock_dependencies["notification_signals"]
        )
    
    @pytest.mark.asyncio
    async def test_send_llm_request(self, llm_handler: Any) -> None:
        """LLM 요청 테스트"""
        request = LLMRequest(prompt="Hello AI")
        
        result = await llm_handler.send_llm_request(request)
        
        assert result["status"] == "success"
        assert "대화창에 전송되었습니다" in result["message"]
        assert result["data"]["prompt"] == "Hello AI"
    
    @pytest.mark.asyncio
    async def test_send_streaming_request(self, llm_handler: Any) -> None:
        """스트리밍 요청 테스트"""
        request = LLMRequest(prompt="Stream this")
        
        result = await llm_handler.send_streaming_request(request)
        
        assert result["status"] == "success"
        assert "스트리밍 요청이 전송되었습니다" in result["message"]
        assert result["data"]["mode"] == "streaming"


class TestMCPHandler:
    """MCP 핸들러 테스트"""
    
    @pytest.fixture
    def mcp_handler(self, mock_dependencies: Dict[str, Any]) -> Any:
        return MCPHandler(
            mock_dependencies["mcp_manager"],
            mock_dependencies["mcp_tool_manager"], 
            mock_dependencies["notification_signals"]
        )
    
    @pytest.mark.asyncio
    async def test_get_mcp_servers(self, mcp_handler: Any) -> None:
        """MCP 서버 목록 조회 테스트"""
        result = await mcp_handler.get_mcp_servers()
        
        assert result["status"] == "success" 
        assert "서버 목록 조회 완료" in result["message"]
        assert "servers" in result["data"]
    
    @pytest.mark.asyncio
    async def test_get_mcp_server_status(self, mcp_handler: Any) -> None:
        """MCP 서버 상태 조회 테스트"""
        result = await mcp_handler.get_mcp_server_status("test_server")
        
        assert result["status"] == "success"
        assert "상태 조회 완료" in result["message"]
        assert result["data"]["server_name"] == "test_server"
        assert result["data"]["connected"] == True


class TestNotificationHandler:
    """알림 핸들러 테스트"""
    
    @pytest.fixture
    def notification_handler(self, mock_dependencies: Dict[str, Any]) -> Any:
        return NotificationHandler(
            mock_dependencies["mcp_manager"],
            mock_dependencies["mcp_tool_manager"], 
            mock_dependencies["notification_signals"]
        )
    
    @pytest.mark.asyncio
    async def test_send_info_notification(self, notification_handler: Any) -> None:
        """정보 알림 테스트"""
        request = NotificationRequest(
            title="Info",
            message="This is info",
            duration=3000
        )
        
        result = await notification_handler.send_info_notification(request)
        
        assert result["status"] == "success"
        assert "info" in result["message"]
        assert result["data"]["type"] == "info"
    
    @pytest.mark.asyncio
    async def test_send_system_notification(self, notification_handler: Any) -> None:
        """시스템 알림 테스트"""
        request = SystemNotificationRequest(
            title="System Alert",
            message="System message",
            type="warning"
        )
        
        result = await notification_handler.send_system_notification(request)
        
        assert result["status"] == "success"
        assert "시스템 알림이 전송되었습니다" in result["message"]
        assert result["data"]["title"] == "System Alert"
    
    @pytest.mark.asyncio
    async def test_send_dialog_notification(self, notification_handler: Any) -> None:
        """다이얼로그 알림 테스트"""
        request = DialogNotificationRequest(
            title="Dialog",
            message="Dialog message",
            notification_type="confirm",
            width=400,
            height=200
        )
        
        result = await notification_handler.send_dialog_notification(request)
        
        assert result["status"] == "success"
        assert "다이얼로그 알림이 전송되었습니다" in result["message"]
        assert result["data"]["width"] == 400 
