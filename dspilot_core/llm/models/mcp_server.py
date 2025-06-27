"""
MCP 서버 모델
"""

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class MCPServer(BaseModel):
    """MCP 서버 모델"""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., description="서버 이름")
    command: str = Field(..., description="실행 명령")
    args: List[str] = Field(default_factory=list, description="명령 인자")
    env: Dict[str, str] = Field(default_factory=dict, description="환경 변수")
    description: str = Field("", description="서버 설명")
    enabled: bool = Field(True, description="활성화 여부")

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "MCPServer":
        """딕셔너리에서 생성"""
        return cls(name=name, **data)

    def get_full_command(self) -> List[str]:
        """전체 명령 반환"""
        return [self.command] + self.args
