"""
MCP 설정 모델
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MCPConfig(BaseModel):
    """MCP 설정 모델"""

    model_config = ConfigDict(extra="allow")

    mcp_servers: Dict[str, Any] = Field(default_factory=dict, description="MCP 서버 설정")
    default_server: Optional[str] = Field(None, description="기본 서버")
    enabled: bool = Field(True, description="MCP 활성화 여부")

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPConfig":
        """딕셔너리에서 생성"""
        return cls(**data)

    def get_server_names(self) -> List[str]:
        """서버 이름 목록 반환"""
        return list(getattr(self, "mcp_servers", {}).keys())

    def get_enabled_servers(self) -> Dict[str, Any]:
        """활성화된 서버 설정 반환"""
        enabled_servers = {}
        servers = getattr(self, "mcp_servers", {})
        for name, config in servers.items():
            if isinstance(config, dict) and config.get("enabled", True):
                enabled_servers[name] = config
        return enabled_servers
