"""UI 설정 처리 핸들러"""

from typing import Any, Dict

from application.api.handlers.base_handler import BaseHandler
from application.api.models.ui_settings_request import UISettingsRequest


class UIHandler(BaseHandler):
    """UI 설정 관련 API 처리를 담당하는 핸들러"""

    async def get_ui_settings(self) -> Dict[str, Any]:
        """현재 UI 설정 조회"""
        try:
            self._log_request("get_ui_settings")

            # 메인 윈도우에서 현재 UI 설정 가져오기
            if hasattr(self.notification_signals, "main_window"):
                main_window = self.notification_signals.main_window
                ui_config = main_window.ui_config
                return self._create_success_response(
                    "UI 설정 조회 완료",
                    {
                        "settings": {
                            "font_family": ui_config.get("font_family", "시스템 기본"),
                            "font_size": ui_config.get("font_size", 14),
                            "theme": ui_config.get("theme", "default"),
                        }
                    },
                )
            else:
                return self._create_error_response("UI 설정에 접근할 수 없습니다")
        except Exception as exception:
            return self._create_error_response("UI 설정 조회 실패", exception)

    async def update_ui_settings(self, request: UISettingsRequest) -> Dict[str, Any]:
        """UI 설정 업데이트"""
        try:
            self._log_request("update_ui_settings", request.model_dump())

            updated_settings: dict = {}

            if request.font_family:
                updated_settings["font_family"] = request.font_family
            if request.font_size:
                updated_settings["font_size"] = request.font_size
            if request.theme:
                updated_settings["theme"] = request.theme

            if not updated_settings:
                return self._create_error_response("업데이트할 설정이 없습니다")

            # UI 설정 업데이트 시그널 전송
            self.notification_signals.update_ui_settings.emit(updated_settings)

            return self._create_success_response(
                "UI 설정이 업데이트되었습니다", {"updated_settings": updated_settings}
            )
        except Exception as exception:
            return self._create_error_response("UI 설정 업데이트 실패", exception)

    async def change_font_size(self, font_size: int) -> Dict[str, Any]:
        """폰트 크기 변경"""
        try:
            self._log_request("change_font_size", {"font_size": font_size})

            if not 8 <= font_size <= 72:
                return self._create_error_response("폰트 크기는 8-72 사이여야 합니다")

            # 폰트 크기 변경 시그널 전송
            self.notification_signals.update_ui_settings.emit({"font_size": font_size})

            return self._create_success_response(
                f"폰트 크기가 {font_size}px로 변경되었습니다", {"font_size": font_size}
            )
        except Exception as exception:
            return self._create_error_response("폰트 크기 변경 실패", exception)
