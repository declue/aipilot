from typing import Optional

from pydantic import BaseModel


class ChatHistoryRequest(BaseModel):
    """채팅 기록 관련 요청 모델"""

    action: str  # save, load, clear
    file_path: Optional[str] = None
    content: Optional[str] = None
