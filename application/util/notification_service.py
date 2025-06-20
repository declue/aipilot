from __future__ import annotations

"""API 서버로 데스크톱 알림을 전송하는 작은 서비스 레이어.

WebhookClient 뿐만 아니라 다른 모듈에서도 재사용 가능하도록 분리했다.
"""

import logging
from typing import Any, Dict

import requests

from application.util.logger import setup_logger

# setup_logger 가 None 을 반환할 수 있으므로 안전하게 기본 로거로 대체
logger: logging.Logger = setup_logger("notification_service") or logging.getLogger("notification_service")


class NotificationService:  # pylint: disable=too-few-public-methods
    """FastAPI-기반 API 서버에 알림을 전송한다."""

    def __init__(self, session: requests.Session, api_server_url: str) -> None:
        self._session: requests.Session = session
        self._api_server_url: str = api_server_url.rstrip("/")

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    @property
    def api_server_url(self) -> str:  # noqa: D401 – simple property
        return self._api_server_url

    @api_server_url.setter
    def api_server_url(self, new_url: str) -> None:  # noqa: D401 – simple setter
        self._api_server_url = new_url.rstrip("/")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def send_info(
        self,
        title: str,
        message: str,
        *,
        duration: int = 5000,
        priority: str = "normal",
        show_bubble: bool | None = None,
    ) -> bool:
        """단순 텍스트 알림(post /notifications/info)"""
        payload: Dict[str, Any] = {
            "title": title or "알림",
            "message": message,
            "duration": duration,
            "priority": priority,
        }
        if show_bubble is not None:
            payload["show_bubble"] = show_bubble

        return self._post_json("/notifications/info", payload)

    def send_dialog_html(
        self,
        *,
        title: str,
        html_message: str,
        message: str,
        notification_type: str = "info",
        width: int = 550,
        height: int = 340,
        duration: int = 0,
    ) -> bool:
        """HTML 다이얼로그 알림(post /notifications/dialog/html)"""
        payload: Dict[str, Any] = {
            "title": title,
            "html_message": html_message,
            "message": message,
            "notification_type": notification_type,
            "width": width,
            "height": height,
            "duration": duration,
        }
        return self._post_json("/notifications/dialog/html", payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _post_json(self, endpoint: str, payload: Dict[str, Any]) -> bool:
        url = f"{self._api_server_url}{endpoint}"
        try:
            response = self._session.post(
                url, json=payload, timeout=5, verify=False
            )  # noqa: S501 SSL off
            response.raise_for_status()
            logger.debug("알림 전송 완료: %s", endpoint)
            return True
        except requests.RequestException as exc:  # noqa: BLE001
            logger.error("알림 전송 실패(%s): %s", endpoint, exc)
            return False
