"""
MCP 서버 상태 모델
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MCPServerStatus(BaseModel):
    """MCP 서버 상태 모델"""

    model_config = ConfigDict(extra="allow")

    server_name: str = Field(..., description="서버 이름")
    connected: bool = Field(False, description="연결 상태")
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="사용 가능한 도구")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    last_check: datetime = Field(default_factory=datetime.now, description="마지막 확인 시간")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = self.model_dump()
        last_check = getattr(self, "last_check", None)
        if last_check and isinstance(last_check, datetime):
            data["last_check"] = last_check.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPServerStatus":
        """딕셔너리에서 생성"""
        if "last_check" in data and isinstance(data["last_check"], str):
            data["last_check"] = datetime.fromisoformat(data["last_check"])
        return cls(**data)

    def is_healthy(self) -> bool:
        """서버가 정상 상태인지 확인"""
        return self.connected and not self.error_message

    def get_tool_count(self) -> int:
        """도구 개수 반환"""
        return len(self.tools)
