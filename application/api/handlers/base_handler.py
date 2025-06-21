"""기본 핸들러 클래스"""

import logging
from abc import ABC
from collections.abc import Awaitable, Callable
from typing import Any, Dict, Optional

from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager
from application.ui.signals.notification_signals import NotificationSignals
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("base_handler") or logging.getLogger("base_handler")


class BaseHandler(ABC):
    """모든 API 핸들러의 기본 클래스"""

    def __init__(
        self,
        mcp_manager: MCPManager,
        mcp_tool_manager: MCPToolManager,
        notification_signals: NotificationSignals,
    ) -> None:
        self.mcp_manager = mcp_manager
        self.mcp_tool_manager = mcp_tool_manager
        self.notification_signals = notification_signals
        self.logger = logger

    def _create_success_response(
        self,
        message: str,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """성공 응답 생성"""
        response: dict[str, Any] = {
            "status": "success",
            "message": message,
            "timestamp": self._get_timestamp(),
        }

        if data:
            response["data"] = data

        if metadata:
            response["metadata"] = metadata

        return response

    def _create_error_response(
        self,
        message: str,
        exception: Exception | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """오류 응답 생성"""
        if exception and self.logger:
            self.logger.error("%s: %s", message, exception, exc_info=True)

        response: Dict[str, Any] = {
            "status": "error",
            "message": message,
            "timestamp": self._get_timestamp(),
        }

        if exception:
            response["error_detail"] = str(exception)
            response["error_type"] = type(exception).__name__

        if error_code:
            response["error_code"] = error_code

        if details:
            response["details"] = details

        return response

    def _create_validation_error_response(
        self, field: str, value: Any, expected: str
    ) -> Dict[str, Any]:
        """검증 오류 응답 생성"""
        return self._create_error_response(
            f"입력값 검증 실패: {field}",
            error_code="VALIDATION_ERROR",
            details={"field": field, "provided_value": str(value), "expected": expected},
        )

    def _log_request(
        self, endpoint: str, data: Optional[Any] = None, user_id: Optional[str] = None
    ) -> None:
        """요청 로깅"""
        if self.logger:
            log_data = {"endpoint": endpoint, "user_id": user_id or "anonymous"}

            if data:
                # 민감한 정보 마스킹 (예: 패스워드, API 키 등)
                masked_data = self._mask_sensitive_data(data)
                log_data["data"] = (
                    str(masked_data)[:200] + "..." if len(str(masked_data)) > 200 else masked_data
                )

            self.logger.info("API 요청 - %s", log_data)

    def _log_response(
        self, endpoint: str, response: Dict[str, Any], execution_time_ms: Optional[float] = None
    ) -> None:
        """응답 로깅"""
        if self.logger:
            log_data = {
                "endpoint": endpoint,
                "status": response.get("status"),
                "execution_time_ms": execution_time_ms,
            }

            if response.get("status") == "error":
                log_data["error"] = response.get("message")
                self.logger.warning("API 응답 - %s", log_data)
            else:
                self.logger.info("API 응답 - %s", log_data)

    def _mask_sensitive_data(self, data: Any) -> Any:
        """민감한 데이터 마스킹"""
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                if any(
                    sensitive in key.lower() for sensitive in ["password", "token", "key", "secret"]
                ):
                    masked[key] = "*" * len(str(value)) if value else None
                else:
                    masked[key] = self._mask_sensitive_data(value)
            return masked
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        else:
            return data

    def _get_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime

        return datetime.now().isoformat()

    def _validate_required_fields(
        self, data: Dict[str, Any], required_fields: list[str]
    ) -> Optional[Dict[str, Any]]:
        """필수 필드 검증"""
        missing_fields = []

        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing_fields.append(field)

        if missing_fields:
            return self._create_validation_error_response(
                "required_fields",
                missing_fields,
                f"다음 필드들이 필요합니다: {', '.join(required_fields)}",
            )

        return None

    async def _safe_execute(
        self,
        operation_name: str,
        operation_func: Callable[..., Awaitable[Dict[str, Any]]],
        *args: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """안전한 작업 실행 래퍼"""
        try:
            start_time = self._get_current_time_ms()

            result = await operation_func(*args, **kwargs)

            execution_time = self._get_current_time_ms() - start_time
            self._log_response(operation_name, result, execution_time)

            return result

        except Exception as exception:
            self.logger.error("작업 실행 실패 - %s: %s", operation_name, exception, exc_info=True)
            return self._create_error_response(
                f"{operation_name} 실행 중 오류가 발생했습니다",
                exception,
                error_code="OPERATION_ERROR",
            )

    def _get_current_time_ms(self) -> float:
        """현재 시간을 밀리초로 반환"""
        import time

        return time.time() * 1000
