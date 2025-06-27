from typing import Optional

from pydantic import BaseModel


class DialogNotificationRequest(BaseModel):
    """다이얼로그 알림 요청 모델 (TrayNotificationDialog 사용)"""

    title: str
    message: Optional[str] = None
    html_message: Optional[str] = None
    notification_type: str = "info"  # info, warning, error, confirm, auto
    width: Optional[int] = 350
    height: Optional[int] = 150
    duration: Optional[int] = 5000
