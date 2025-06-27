from typing import Optional

from pydantic import BaseModel


class NotificationMessage(BaseModel):
    type: str  # "auto", "confirm", "info", "warning", "error"
    title: str
    message: str
    html_message: Optional[str] = None  # HTML 형식 메시지 (선택적)
    duration: Optional[int] = 5000  # 자동 사라지는 시간 (밀리초)
    width: Optional[int] = 350  # 알림 창 너비
    height: Optional[int] = 150  # 알림 창 높이
