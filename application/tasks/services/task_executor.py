"""작업 실행자 서비스 구현"""

import logging
from typing import Any, Dict

from application.tasks.exceptions import TaskExecutionError
from application.tasks.interfaces.http_client import IHttpClient
from application.tasks.interfaces.task_executor import ITaskExecutor
from application.tasks.models.task_config import TaskConfig
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("task") or logging.getLogger("task")


class TaskExecutor(ITaskExecutor):
    """작업 실행자 서비스 구현"""

    def __init__(self, http_client: IHttpClient) -> None:
        self.http_client = http_client

    async def execute_task(self, task: TaskConfig) -> Dict[str, Any]:
        """작업을 실행합니다."""
        logger.info(f"작업 실행 시작: {task.name} ({task.id})")

        try:
            if task.action_type == "llm_request":
                return await self.execute_llm_request(task)
            elif task.action_type == "api_call":
                return await self.execute_api_call(task)
            elif task.action_type == "notification":
                return await self.execute_notification(task)
            else:
                raise TaskExecutionError(task.id, f"알 수 없는 작업 타입: {task.action_type}")
        except Exception as e:
            logger.error(f"작업 실행 중 오류: {task.name} - {e}")
            if isinstance(e, TaskExecutionError):
                raise
            raise TaskExecutionError(task.id, str(e), e)

    async def execute_llm_request(self, task: TaskConfig) -> Dict[str, Any]:
        """LLM 요청을 실행합니다."""
        params = task.action_params
        prompt = params.get("prompt", "")
        api_url = params.get("api_url", "http://127.0.0.1:8000/llm/request")

        if not prompt:
            raise TaskExecutionError(task.id, "LLM 요청에 prompt가 없습니다")

        try:
            payload = {"prompt": prompt}
            result = await self.http_client.post(api_url, payload)
            logger.info(f"LLM 요청 완료: {task.name}")
            logger.debug(f"LLM 응답: {result}")
            return result
        except Exception as e:
            raise TaskExecutionError(task.id, f"LLM 요청 실행 실패: {e}", e)

    async def execute_api_call(self, task: TaskConfig) -> Dict[str, Any]:
        """API 호출을 실행합니다."""
        params = task.action_params
        url = params.get("url", "")
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        payload = params.get("payload", {})

        if not url:
            raise TaskExecutionError(task.id, "API 호출에 URL이 없습니다")

        try:
            if method == "GET":
                result = await self.http_client.get(url, headers)
            elif method == "POST":
                result = await self.http_client.post(url, payload, headers)
            elif method == "PUT":
                result = await self.http_client.put(url, payload, headers)
            elif method == "DELETE":
                result = await self.http_client.delete(url, headers)
            else:
                raise TaskExecutionError(task.id, f"지원하지 않는 HTTP 메서드: {method}")

            logger.info(f"API 호출 완료: {task.name}")
            logger.debug(f"API 응답: {str(result)[:200]}...")
            return result
        except Exception as e:
            raise TaskExecutionError(task.id, f"API 호출 실행 실패: {e}", e)

    async def execute_notification(self, task: TaskConfig) -> Dict[str, Any]:
        """알림을 실행합니다."""
        params = task.action_params
        message = params.get("message", "")
        notification_type = params.get("type", "info")
        api_url = params.get("api_url", f"http://127.0.0.1:8000/notifications/{notification_type}")

        if not message:
            raise TaskExecutionError(task.id, "알림에 메시지가 없습니다")

        try:
            payload = {"title": params.get("title", task.name), "message": message}
            result = await self.http_client.post(api_url, payload)
            logger.info(f"알림 전송 완료: {task.name}")
            logger.debug(f"알림 응답: {result}")
            return result
        except Exception as e:
            raise TaskExecutionError(task.id, f"알림 실행 실패: {e}", e)
