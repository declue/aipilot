"""
대화 메시지 모델
"""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class ConversationMessage(BaseModel):
    """대화 메시지 모델"""
    
    model_config = ConfigDict(extra="allow")
    
    role: str = Field(..., description="역할 (user, assistant, system)")
    content: str = Field(..., description="메시지 내용")
    timestamp: datetime = Field(default_factory=datetime.now, description="메시지 시간")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")
        
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        """딕셔너리에서 생성"""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data) 