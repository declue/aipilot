from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MCPServerStatus(BaseModel):
    """MCP 서버 상태 정보"""

    name: str
    connected: bool
    tools: List[Dict[str, Any]] = []
    resources: List[Dict[str, Any]] = []
    prompts: List[Dict[str, Any]] = []
    error_message: Optional[str] = None
