"""작업 실행자 테스트"""

from typing import Any, Dict, Optional

import pytest

from application.tasks.exceptions import TaskExecutionError
from application.tasks.interfaces.http_client import IHttpClient
from application.tasks.models.task_config import TaskConfig
from application.tasks.services.task_executor import TaskExecutor


class MockHttpClient(IHttpClient):
    """Mock HTTP 클라이언트"""
    
    def __init__(self) -> None:
        self.responses: Dict[str, Any] = {}
        self.called_methods: list = []
        
    async def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        self.called_methods.append(("GET", url, headers))
        return self.responses.get("GET", {"status": "success"})
        
    async def post(self, url: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        self.called_methods.append(("POST", url, data, headers))
        return self.responses.get("POST", {"status": "success"})
        
    async def put(self, url: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        self.called_methods.append(("PUT", url, data, headers))
        return self.responses.get("PUT", {"status": "success"})
        
    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        self.called_methods.append(("DELETE", url, headers))
        return self.responses.get("DELETE", {"status": "success"})
        
    async def close(self) -> None:
        pass


class TestTaskExecutor:
    """작업 실행자 테스트 클래스"""

    @pytest.fixture
    def mock_http_client(self) -> MockHttpClient:
        """Mock HTTP 클라이언트 인스턴스"""
        return MockHttpClient()

    @pytest.fixture
    def task_executor(self, mock_http_client: MockHttpClient) -> TaskExecutor:
        """TaskExecutor 인스턴스"""
        return TaskExecutor(mock_http_client)

    @pytest.fixture
    def llm_task(self) -> TaskConfig:
        """LLM 요청 작업 생성"""
        return TaskConfig(
            id="test_llm",
            name="Test LLM Task",
            description="테스트용 LLM 작업",
            action_type="llm_request",
            action_params={
                "prompt": "테스트 프롬프트",
                "api_url": "http://localhost:8000/llm/request"
            },
            cron_expression="0 0 * * *"
        )

    @pytest.fixture
    def api_task(self) -> TaskConfig:
        """API 호출 작업 생성"""
        return TaskConfig(
            id="test_api",
            name="Test API Task",
            description="테스트용 API 작업",
            action_type="api_call",
            action_params={
                "url": "https://api.example.com/data",
                "method": "GET",
                "headers": {"Authorization": "Bearer token"}
            },
            cron_expression="0 0 * * *"
        )

    @pytest.fixture
    def notification_task(self) -> TaskConfig:
        """알림 작업 생성"""
        return TaskConfig(
            id="test_notification",
            name="Test Notification Task",
            description="테스트용 알림 작업",
            action_type="notification",
            action_params={
                "message": "테스트 알림 메시지",
                "type": "info",
                "title": "테스트 알림"
            },
            cron_expression="0 0 * * *"
        )

    @pytest.mark.asyncio
    async def test_execute_llm_request_success(self, task_executor: TaskExecutor, llm_task: TaskConfig, mock_http_client: MockHttpClient):
        """LLM 요청 실행 성공 테스트"""
        # Mock 응답 설정
        mock_http_client.responses["POST"] = {"result": "LLM 응답"}
        
        # 실행
        result = await task_executor.execute_llm_request(llm_task)
        
        # 검증
        assert result == {"result": "LLM 응답"}
        assert len(mock_http_client.called_methods) == 1
        method, url, data, headers = mock_http_client.called_methods[0]
        assert method == "POST"
        assert url == "http://localhost:8000/llm/request"
        assert data == {"prompt": "테스트 프롬프트"}

    @pytest.mark.asyncio
    async def test_execute_llm_request_no_prompt(self, task_executor: TaskExecutor):
        """LLM 요청 - 프롬프트 없음 테스트"""
        task = TaskConfig(
            id="test_llm_no_prompt",
            name="Test LLM No Prompt",
            description="테스트용 LLM 작업 (프롬프트 없음)",
            action_type="llm_request",
            action_params={},
            cron_expression="0 0 * * *"
        )
        
        with pytest.raises(TaskExecutionError) as exc_info:
            await task_executor.execute_llm_request(task)
        
        assert "LLM 요청에 prompt가 없습니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_api_call_get_success(self, task_executor: TaskExecutor, api_task: TaskConfig, mock_http_client: MockHttpClient):
        """API 호출 (GET) 성공 테스트"""
        # Mock 응답 설정
        mock_http_client.responses["GET"] = {"data": "API 응답"}
        
        # 실행
        result = await task_executor.execute_api_call(api_task)
        
        # 검증
        assert result == {"data": "API 응답"}
        assert len(mock_http_client.called_methods) == 1
        method, url, headers = mock_http_client.called_methods[0]
        assert method == "GET"
        assert url == "https://api.example.com/data"
        assert headers == {"Authorization": "Bearer token"}

    @pytest.mark.asyncio
    async def test_execute_api_call_post_success(self, task_executor: TaskExecutor, mock_http_client: MockHttpClient):
        """API 호출 (POST) 성공 테스트"""
        task = TaskConfig(
            id="test_api_post",
            name="Test API POST",
            description="테스트용 API POST 작업",
            action_type="api_call",
            action_params={
                "url": "https://api.example.com/create",
                "method": "POST",
                "payload": {"name": "테스트"},
                "headers": {"Content-Type": "application/json"}
            },
            cron_expression="0 0 * * *"
        )
        
        # Mock 응답 설정
        mock_http_client.responses["POST"] = {"id": 123, "status": "created"}
        
        # 실행
        result = await task_executor.execute_api_call(task)
        
        # 검증
        assert result == {"id": 123, "status": "created"}
        assert len(mock_http_client.called_methods) == 1
        method, url, data, headers = mock_http_client.called_methods[0]
        assert method == "POST"
        assert url == "https://api.example.com/create"
        assert data == {"name": "테스트"}
        assert headers == {"Content-Type": "application/json"}

    @pytest.mark.asyncio
    async def test_execute_api_call_no_url(self, task_executor: TaskExecutor):
        """API 호출 - URL 없음 테스트"""
        task = TaskConfig(
            id="test_api_no_url",
            name="Test API No URL",
            description="테스트용 API 작업 (URL 없음)",
            action_type="api_call",
            action_params={},
            cron_expression="0 0 * * *"
        )
        
        with pytest.raises(TaskExecutionError) as exc_info:
            await task_executor.execute_api_call(task)
        
        assert "API 호출에 URL이 없습니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_api_call_unsupported_method(self, task_executor: TaskExecutor):
        """API 호출 - 지원하지 않는 메서드 테스트"""
        task = TaskConfig(
            id="test_api_patch",
            name="Test API PATCH",
            description="테스트용 API PATCH 작업",
            action_type="api_call",
            action_params={
                "url": "https://api.example.com/update",
                "method": "PATCH"
            },
            cron_expression="0 0 * * *"
        )
        
        with pytest.raises(TaskExecutionError) as exc_info:
            await task_executor.execute_api_call(task)
        
        assert "지원하지 않는 HTTP 메서드: PATCH" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_notification_success(self, task_executor: TaskExecutor, notification_task: TaskConfig, mock_http_client: MockHttpClient):
        """알림 실행 성공 테스트"""
        # Mock 응답 설정
        mock_http_client.responses["POST"] = {"status": "sent"}
        
        # 실행
        result = await task_executor.execute_notification(notification_task)
        
        # 검증
        assert result == {"status": "sent"}
        assert len(mock_http_client.called_methods) == 1
        method, url, data, headers = mock_http_client.called_methods[0]
        assert method == "POST"
        assert url == "http://127.0.0.1:8000/notifications/info"
        assert data == {"title": "테스트 알림", "message": "테스트 알림 메시지"}

    @pytest.mark.asyncio
    async def test_execute_notification_no_message(self, task_executor: TaskExecutor):
        """알림 실행 - 메시지 없음 테스트"""
        task = TaskConfig(
            id="test_notification_no_msg",
            name="Test Notification No Message",
            description="테스트용 알림 작업 (메시지 없음)",
            action_type="notification",
            action_params={},
            cron_expression="0 0 * * *"
        )
        
        with pytest.raises(TaskExecutionError) as exc_info:
            await task_executor.execute_notification(task)
        
        assert "알림에 메시지가 없습니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_task_success(self, task_executor: TaskExecutor, llm_task: TaskConfig, mock_http_client: MockHttpClient):
        """작업 실행 성공 테스트"""
        mock_http_client.responses["POST"] = {"result": "success"}
        
        result = await task_executor.execute_task(llm_task)
        
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_execute_task_unknown_type(self, task_executor: TaskExecutor):
        """알 수 없는 작업 타입 테스트"""
        task = TaskConfig(
            id="test_unknown",
            name="Test Unknown Task",
            description="테스트용 알 수 없는 작업",
            action_type="unknown_type",
            action_params={},
            cron_expression="0 0 * * *"
        )
        
        with pytest.raises(TaskExecutionError) as exc_info:
            await task_executor.execute_task(task)
        
        assert "알 수 없는 작업 타입: unknown_type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_task_http_error(self, task_executor: TaskExecutor, llm_task: TaskConfig, mock_http_client: MockHttpClient):
        """HTTP 오류 처리 테스트"""
        # HTTP 클라이언트에서 예외 발생하도록 설정
        async def mock_post_error(*args, **kwargs):
            raise Exception("Network error")
        
        mock_http_client.post = mock_post_error
        
        with pytest.raises(TaskExecutionError) as exc_info:
            await task_executor.execute_task(llm_task)
        
        assert "Network error" in str(exc_info.value) 