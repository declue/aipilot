"""대화 처리 핸들러"""

from typing import Any, Dict

from application.api.handlers.base_handler import BaseHandler


class ConversationHandler(BaseHandler):
    """대화 관련 API 처리를 담당하는 핸들러"""

    async def start_new_conversation(self) -> Dict[str, Any]:
        """새 대화 시작"""
        try:
            self._log_request("start_new_conversation")

            self.notification_signals.clear_chat.emit()
            return self._create_success_response("새 대화가 시작되었습니다")
        except Exception as exception:
            return self._create_error_response("새 대화 시작 실패", exception)

    async def save_conversation(self, file_path: str) -> Dict[str, Any]:
        """대화 내용 저장"""
        try:
            self._log_request("save_conversation", {"file_path": file_path})

            self.notification_signals.save_chat.emit(file_path)
            return self._create_success_response(
                f"대화 내용이 저장되었습니다: {file_path}", {"file_path": file_path}
            )
        except Exception as exception:
            return self._create_error_response("대화 저장 실패", exception)

    async def load_conversation(self, file_path: str) -> Dict[str, Any]:
        """대화 내용 불러오기"""
        try:
            self._log_request("load_conversation", {"file_path": file_path})

            self.notification_signals.load_chat.emit(file_path)
            return self._create_success_response(
                f"대화 내용이 불러와졌습니다: {file_path}", {"file_path": file_path}
            )
        except Exception as exception:
            return self._create_error_response("대화 불러오기 실패", exception)
