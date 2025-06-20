from typing import Optional

from pydantic import BaseModel


class SystemNotificationRequest(BaseModel):
    """시스템 알림 요청 모델 (notifypy 사용)"""

    type: str = "info"  # info, warning, error
    title: str
    message: str
    icon_path: Optional[str] = None
