"""알림 처리 핸들러"""

import logging
from typing import Any, Dict

from application.api.handlers.base_handler import BaseHandler
from application.api.models.dialog_notification_request import DialogNotificationRequest
from application.api.models.notification_message import NotificationMessage
from application.api.models.notification_request import NotificationRequest
from application.api.models.system_notification_request import SystemNotificationRequest
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("api") or logging.getLogger("api")


class NotificationHandler(BaseHandler):
    """알림 관련 API 처리를 담당하는 핸들러"""

    async def send_system_notification(
        self, request: SystemNotificationRequest
    ) -> Dict[str, Any]:
        """시스템 알림 전송 (notifypy 사용)"""
        try:
            self._log_request("send_system_notification", request.model_dump())

            # 시스템 알림 시그널 전송
            self.notification_signals.show_system_notification.emit(
                request.title, request.message, request.icon_path or ""
            )

            # 대화창에도 메시지 추가
            notification_content = (
                f"**[시스템 알림] {request.title}**\n\n{request.message}"
            )
            self.notification_signals.add_api_message.emit(
                "system", notification_content
            )

            return self._create_success_response(
                "시스템 알림이 전송되었습니다",
                {
                    "type": "system",
                    "title": request.title,
                    "message": request.message,
                    "icon_path": request.icon_path,
                },
            )
        except Exception as exception:
            return self._create_error_response("시스템 알림 전송 실패", exception)

    async def send_dialog_notification(
        self, request: DialogNotificationRequest
    ) -> Dict[str, Any]:
        """다이얼로그 알림 전송 (TrayNotificationDialog 사용)"""
        try:
            self._log_request("send_dialog_notification", request.model_dump())

            # 다이얼로그 데이터 준비
            dialog_data = {
                "title": request.title,
                "message": request.message,
                "html_message": request.html_message,
                "notification_type": request.notification_type,
                "width": request.width,
                "height": request.height,
                "duration": request.duration,
            }

            # 다이얼로그 알림 시그널 전송
            self.notification_signals.show_dialog_notification.emit(dialog_data)

            # 대화창에도 메시지 추가
            message_content = (
                request.html_message or request.message or "다이얼로그 알림"
            )
            notification_content = (
                f"**[다이얼로그] {request.title}**\n\n{message_content}"
            )
            self.notification_signals.add_api_message.emit(
                "notification", notification_content
            )

            return self._create_success_response(
                f"'{request.notification_type}' 다이얼로그 알림이 전송되었습니다",
                dialog_data,
            )
        except Exception as exception:
            return self._create_error_response("다이얼로그 알림 전송 실패", exception)

    async def send_html_dialog(
        self, request: DialogNotificationRequest
    ) -> Dict[str, Any]:
        """HTML 다이얼로그 알림 전송"""
        try:
            self._log_request("send_html_dialog", request.model_dump())

            # 다이얼로그 데이터 준비
            dialog_data = {
                "title": request.title,
                "message": request.message,
                "html_message": request.html_message,
                "notification_type": request.notification_type,
                "width": request.width,
                "height": request.height,
                "duration": request.duration,
            }

            # 다이얼로그 알림 시그널 전송 (메인 스레드에서 처리)
            self.notification_signals.show_dialog_notification.emit(dialog_data)

            # 채팅창에 HTML 메시지 추가
            self.notification_signals.add_api_message.emit(
                "html_notification", request.html_message or request.message
            )

            return self._create_success_response(
                "HTML 다이얼로그가 성공적으로 전송되었습니다.", dialog_data
            )

        except Exception as e:
            logger.error(f"HTML 다이얼로그 전송 실패: {str(e)}")
            return self._create_error_response("HTML 다이얼로그 전송 실패", e)

    async def send_info_notification(
        self, request: NotificationRequest
    ) -> Dict[str, Any]:
        """정보 알림 전송"""
        return await self._send_notification_by_type("info", request)

    async def send_warning_notification(
        self, request: NotificationRequest
    ) -> Dict[str, Any]:
        """경고 알림 전송"""
        return await self._send_notification_by_type("warning", request)

    async def send_error_notification(
        self, request: NotificationRequest
    ) -> Dict[str, Any]:
        """오류 알림 전송"""
        return await self._send_notification_by_type("error", request)

    async def send_confirm_notification(
        self, request: NotificationRequest
    ) -> Dict[str, Any]:
        """확인 알림 전송"""
        return await self._send_notification_by_type("confirm", request)

    async def send_auto_notification(
        self, request: NotificationRequest
    ) -> Dict[str, Any]:
        """자동 알림 전송"""
        return await self._send_notification_by_type("auto", request)

    async def _send_notification_by_type(
        self, notification_type: str, request: NotificationRequest
    ) -> Dict[str, Any]:
        """알림 타입별 공통 처리 메서드 (기존 채팅창 알림용)"""
        try:
            self._log_request(
                f"send_{notification_type}_notification", request.model_dump()
            )

            # GUI 스레드로 알림 시그널 전송
            self.notification_signals.show_notification.emit(  # pyright: ignore
                notification_type,
                request.title,
                request.message,
                request.duration,
            )

            # 대화창에도 알림 메시지 추가 (show_bubble 설정에 따라)
            if request.show_bubble:
                notification_content = f"**{request.title}**\n\n{request.message}"
                self.notification_signals.add_api_message.emit(
                    "notification", notification_content
                )

            return self._create_success_response(
                f"'{notification_type}' 채팅창 알림이 전송되었습니다",
                {
                    "type": notification_type,
                    "title": request.title,
                    "message": request.message,
                    "duration": request.duration,
                },
            )
        except Exception as exception:
            return self._create_error_response(
                f"{notification_type} 알림 전송 실패", exception
            )

    # 레거시 호환성을 위한 메서드
    async def send_notification_legacy(
        self, notification: NotificationMessage
    ) -> Dict[str, Any]:
        """
        [DEPRECATED] 기존 알림 API - 호환성을 위해 유지
        대신 /notifications/{type} 엔드포인트를 사용하세요
        """
        try:
            self._log_request("send_notification_legacy", notification.model_dump())

            # 새로운 형식으로 변환
            request = NotificationRequest(
                title=notification.title,
                message=notification.message,
                html_message=notification.html_message,
                duration=notification.duration,
                width=notification.width,
                height=notification.height,
            )

            result = await self._send_notification_by_type(notification.type, request)
            result["deprecated"] = True
            result["message"] += " (deprecated API 사용)"

            return result
        except Exception as exception:
            return self._create_error_response("레거시 알림 API 처리 오류", exception)
