from typing import Dict, Optional

from pydantic import BaseModel

from application.llm.mcp.config.models.mcp_server import MCPServer


class MCPConfig(BaseModel):
    """전체 MCP 설정 모델"""

    mcpServers: Dict[str, MCPServer] = {}
    defaultServer: Optional[str] = None
    enabled: bool = True

    class Config:
        extra = "allow"
