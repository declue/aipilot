"""채팅 처리 핸들러"""

from typing import Any, Dict

from application.api.handlers.base_handler import BaseHandler
from application.api.models.chat_history_request import ChatHistoryRequest
from application.api.models.chat_message_request import ChatMessageRequest


class ChatHandler(BaseHandler):
    """채팅 관련 API 처리를 담당하는 핸들러"""

    async def add_chat_message(self, request: ChatMessageRequest) -> Dict[str, Any]:
        """채팅 메시지 추가"""
        try:
            self._log_request("add_chat_message", request.model_dump())

            message_type = request.type.lower()

            if message_type == "user":
                self.notification_signals.add_api_message.emit("user", request.message)
            elif message_type == "ai":
                self.notification_signals.add_api_message.emit("ai", request.message)
            elif message_type == "system":
                self.notification_signals.add_api_message.emit("system", request.message)
            else:
                return self._create_error_response(
                    f"지원하지 않는 메시지 타입: {message_type} (user, ai, system만 지원)"
                )

            return self._create_success_response(
                f"{message_type} 메시지가 추가되었습니다",
                {"type": message_type, "message": request.message},
            )
        except Exception as exception:
            return self._create_error_response("채팅 메시지 추가 실패", exception)

    async def clear_chat(self) -> Dict[str, Any]:
        """채팅 내용 지우기"""
        try:
            self._log_request("clear_chat")

            self.notification_signals.clear_chat.emit()
            return self._create_success_response("채팅 내용이 지워졌습니다")
        except Exception as exception:
            return self._create_error_response("채팅 지우기 실패", exception)

    async def chat_history_action(self, request: ChatHistoryRequest) -> Dict[str, Any]:
        """채팅 기록 관련 작업 (저장/불러오기)"""
        try:
            self._log_request("chat_history_action", request.model_dump())

            action = request.action.lower()

            if action == "save":
                if not request.file_path:
                    return self._create_error_response("파일 경로가 필요합니다")
                self.notification_signals.save_chat.emit(request.file_path)
                return self._create_success_response(
                    f"채팅 기록이 저장되었습니다: {request.file_path}"
                )
            elif action == "load":
                if not request.file_path:
                    return self._create_error_response("파일 경로가 필요합니다")
                self.notification_signals.load_chat.emit(request.file_path)
                return self._create_success_response(
                    f"채팅 기록이 불러와졌습니다: {request.file_path}"
                )
            elif action == "clear":
                self.notification_signals.clear_chat.emit()
                return self._create_success_response("채팅 기록이 지워졌습니다")
            else:
                return self._create_error_response(
                    f"지원하지 않는 작업: {action} (save, load, clear만 지원)"
                )

        except Exception as exception:
            return self._create_error_response("채팅 기록 작업 실패", exception)
