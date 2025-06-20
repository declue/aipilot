from pydantic import BaseModel


class LLMRequest(BaseModel):
    prompt: str  # 사용자의 질문이나 요청
