"""
LLM 설정 모델
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class LLMConfig(BaseModel):
    """LLM 설정 모델"""

    model_config = ConfigDict(extra="allow")

    api_key: str = Field(..., description="API 키")
    base_url: Optional[str] = Field(None, description="기본 URL")
    model: str = Field("gpt-3.5-turbo", description="모델명")
    max_tokens: int = Field(1000, description="최대 토큰 수")
    temperature: float = Field(0.7, description="온도 설정")
    streaming: bool = Field(True, description="스트리밍 활성화")
    mode: str = Field("basic", description="LLM 모드 (basic, workflow, mcp_tools)")
    workflow: Optional[str] = Field(None, description="워크플로우 유형")

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMConfig":
        """딕셔너리에서 생성"""
        return cls(**data)
