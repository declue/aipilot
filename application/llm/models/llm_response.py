"""
LLM 응답 모델
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LLMResponse(BaseModel):
    """LLM 응답 모델"""

    model_config = ConfigDict(extra="allow")

    response: str = Field(..., description="응답 메시지")
    reasoning: str = Field("", description="추론 과정")
    used_tools: List[str] = Field(default_factory=list, description="사용된 도구 목록")
    workflow: Optional[str] = Field(None, description="사용된 워크플로우")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMResponse":
        """딕셔너리에서 생성"""
        return cls(**data)
