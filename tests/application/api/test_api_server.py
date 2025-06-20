"""API 서버 테스트"""

from typing import Any, Dict, cast
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from application.api.api_server import APIServer
from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager
from application.ui.signals.notification_signals import NotificationSignals


class _StubManager:
    """간단한 스텁 매니저 (MCPManager, MCPToolManager 대체용)"""

    def get_server_list(self) -> list[str]:
        """서버 목록 반환"""
        return ["test_server"]
    
    def get_enabled_servers(self) -> Dict[str, Any]:
        """활성화된 서버 목록 반환"""
        return {"test_server": MagicMock(command="test", args=[], description="test")}
    
    def get_server(self, name: str) -> Any:
        """특정 서버 반환"""
        return MagicMock(command="test", args=[], description="test", enabled=True)
    
    def get_server_status(self, name: str) -> Any:
        """서버 상태 반환"""
        return MagicMock(connected=True, tools=[], resources=[], prompts=[])

    def __getattr__(self, item: str) -> Any:
        # 호출되는 메서드가 테스트 대상이 아니므로 예외 대신 무시
        def _noop(*_args: Any, **_kwargs: Any) -> None:
            return None

        return _noop


class _StubNotificationSignals:
    """간단한 스텁 NotificationSignals"""

    def __getattr__(self, item: str) -> Any:
        return MagicMock()


@pytest.fixture
def client() -> TestClient:
    """테스트 클라이언트 생성"""
    stub_mcp_manager = _StubManager()
    stub_mcp_tool_manager = _StubManager()
    stub_signals = _StubNotificationSignals()

    # APIServer 인스턴스 생성
    api_server = APIServer(
        stub_mcp_manager,  # type: ignore
        stub_mcp_tool_manager,  # type: ignore
        stub_signals  # type: ignore
    )
    api_server.register_endpoints()

    # FastAPI 앱을 TestClient로 래핑
    return TestClient(api_server.api_app)


def test_index_endpoint(client: TestClient) -> None:
    """루트 엔드포인트 테스트"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "메신저 알림 API 서버가 실행 중입니다"}


def test_health_check_endpoint(client: TestClient) -> None:
    """헬스 체크 엔드포인트 테스트"""
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    assert "정상 작동" in json_data["message"]


# UI 관련 테스트


def test_change_font_size_success(client: TestClient) -> None:
    """폰트 크기 변경 성공 테스트"""
    response = client.post("/ui/font-size", json={"font_size": 16})
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["data"]["font_size"] == 16


def test_change_font_size_validation_error(client: TestClient) -> None:
    """폰트 크기 검증 오류 테스트"""
    # 100은 허용 범위 초과(8~72)
    response = client.post("/ui/font-size", json={"font_size": 100})
    assert response.status_code == 422  # Pydantic 검증 오류


def test_change_font_size_invalid_request(client: TestClient) -> None:
    """잘못된 요청 형식 테스트"""
    response = client.post("/ui/font-size", json={"invalid_field": 16})
    assert response.status_code == 422  # Pydantic 검증 오류


# 채팅 관련 테스트


def test_add_chat_message_success(client: TestClient) -> None:
    """채팅 메시지 추가 성공 테스트"""
    response = client.post(
        "/chat/messages", 
        json={"message": "Hello", "type": "user"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"


def test_clear_chat_success(client: TestClient) -> None:
    """채팅 지우기 성공 테스트"""
    response = client.post("/chat/clear")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"


# 대화 관련 테스트


def test_conversation_save_success(client: TestClient) -> None:
    """대화 저장 성공 테스트"""
    response = client.post(
        "/conversation/save", 
        json={"file_path": "/test/path.json", "action": "save"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"


def test_conversation_load_success(client: TestClient) -> None:
    """대화 불러오기 성공 테스트"""
    response = client.post(
        "/conversation/load", 
        json={"file_path": "/test/path.json", "action": "load"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"


def test_conversation_file_operation_success(client: TestClient) -> None:
    """통합 대화 파일 작업 성공 테스트"""
    response = client.post(
        "/conversation/file", 
        json={"file_path": "/test/path.json", "action": "save"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"


# LLM 관련 테스트


def test_llm_request_success(client: TestClient) -> None:
    """LLM 요청 성공 테스트"""
    response = client.post(
        "/llm/request", 
        json={"prompt": "Hello AI"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"


def test_llm_streaming_request_success(client: TestClient) -> None:
    """LLM 스트리밍 요청 성공 테스트"""
    response = client.post(
        "/llm/streaming", 
        json={"prompt": "Stream this"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"


# 알림 관련 테스트


def test_notification_info_success(client: TestClient) -> None:
    """정보 알림 성공 테스트"""
    response = client.post(
        "/notifications/info", 
        json={
            "title": "Info", 
            "message": "This is info",
            "duration": 3000
        }
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"


def test_notification_system_success(client: TestClient) -> None:
    """시스템 알림 성공 테스트"""
    response = client.post(
        "/notifications/system", 
        json={
            "title": "System Alert", 
            "message": "System message",
            "type": "warning"
        }
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"


# MCP 관련 테스트


def test_mcp_servers_list_success(client: TestClient) -> None:
    """MCP 서버 목록 조회 성공 테스트"""
    response = client.get("/mcp/servers")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"


def test_mcp_enabled_servers_success(client: TestClient) -> None:
    """활성화된 MCP 서버 조회 성공 테스트"""
    response = client.get("/mcp/enabled")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"


# 레거시 엔드포인트 테스트


def test_legacy_llm_endpoint(client: TestClient) -> None:
    """레거시 LLM 엔드포인트 테스트"""
    response = client.post(
        "/llm", 
        json={"prompt": "Legacy request"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data.get("deprecated") == True


def test_legacy_notification_endpoint(client: TestClient) -> None:
    """레거시 알림 엔드포인트 테스트"""
    response = client.post(
        "/notify", 
        json={
            "type": "info",
            "title": "Legacy Notification", 
            "message": "Legacy message"
        }
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data.get("deprecated") == True


# 오류 처리 테스트


def test_invalid_endpoint_404(client: TestClient) -> None:
    """존재하지 않는 엔드포인트 테스트"""
    response = client.get("/nonexistent")
    assert response.status_code == 404


def test_invalid_method_405(client: TestClient) -> None:
    """잘못된 HTTP 메서드 테스트"""
    response = client.put("/")
    assert response.status_code == 405


def test_invalid_json_422(client: TestClient) -> None:
    """잘못된 JSON 형식 테스트"""
    response = client.post(
        "/chat/messages",
        content="invalid json",
        headers={"content-type": "application/json"}
    )
    assert response.status_code == 422


# API 스키마 테스트


def test_openapi_schema_available(client: TestClient) -> None:
    """OpenAPI 스키마 접근 가능 테스트"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "메신저 알림 API"


def test_docs_available(client: TestClient) -> None:
    """API 문서 접근 가능 테스트"""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"] 
