from typing import Any, Dict, List

from pydantic import BaseModel


class MCPServer(BaseModel):
    """MCP 서버 설정 모델"""

    command: str
    args: List[str]
    env: Dict[str, str] = {}
    description: str = ""
    enabled: bool = True

    # 런타임 상태 (JSON에 저장되지 않음)
    connected: bool = False
    tools: List[Dict[str, Any]] = []
    resources: List[Dict[str, Any]] = []
    prompts: List[Dict[str, Any]] = []

    # 식별자(키)로 사용되며 JSON에는 포함되지 않을 수 있음
    name: str = ""

    class Config:
        extra = "allow"
