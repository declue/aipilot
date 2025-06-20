from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    """채팅 메시지 요청 모델"""

    message: str
    type: str = "user"  # user, ai, system
