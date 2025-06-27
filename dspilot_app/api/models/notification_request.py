from typing import Optional

from pydantic import BaseModel


class NotificationRequest(BaseModel):
    """알림 요청 모델 (개선된 버전)"""

    title: str
    message: str
    html_message: Optional[str] = None
    duration: Optional[int] = 5000
    width: Optional[int] = 350
    height: Optional[int] = 150
    show_bubble: Optional[bool] = True  # 채팅 버블 표시 여부
