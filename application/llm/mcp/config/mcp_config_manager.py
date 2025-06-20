import json
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional

from application.llm.mcp.config.models.mcp_config import MCPConfig
from application.llm.mcp.config.models.mcp_server import MCPServer
from application.util.logger import setup_logger

logger = setup_logger("config") or logging.getLogger(__name__)


class MCPConfigManager:
    """MCP 설정 관리 클래스"""

    def __init__(self, config_file: str = "mcp.json"):
        self.config_path = Path(config_file).expanduser().resolve()
        self.config_file = str(self.config_path)
        self.config = MCPConfig()
        self.load_config()

    def load_config(self) -> MCPConfig:
        """MCP 설정 파일 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config = MCPConfig(**data)
                    logger.debug(
                        "MCP 설정 로드 완료: %d개 서버", len(self.config.mcpServers)
                    )
            else:
                logger.warning("MCP 설정 파일이 없습니다: %s", self.config_path)
                self.create_default_config()
        except Exception as exception:
            logger.error("MCP 설정 로드 실패: %s", exception)
            self.create_default_config()

        return self.config

    def save_config(self) -> bool:
        """MCP 설정 파일 저장"""
        try:
            config_dict = self.config.model_dump()
            for _server_name, server_config in config_dict.get(
                "mcpServers", {}
            ).items():
                server_config.pop("connected", None)
                server_config.pop("tools", None)
                server_config.pop("resources", None)
                server_config.pop("prompts", None)
                server_config.pop("name", None)

            # 설정 파일 디렉터리 생성 (존재하지 않는 경우)
            if not self.config_path.parent.exists():
                self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            logger.debug("MCP 설정 저장 완료: %s", self.config_path)
            return True
        except Exception as exception:
            logger.error("MCP 설정 저장 실패: %s", exception)
            return False

    def create_default_config(self):
        """기본 MCP 설정 생성"""
        self.config = MCPConfig(
            mcpServers={
                "github": MCPServer(
                    command="tools/github-mcp-server.exe",
                    args=["stdio"],
                    env={"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
                    description="GitHub repository and issue management",
                    enabled=False,
                ),
                "test": MCPServer(
                    command="python",
                    args=["test_fastmcp_server.py"],
                    env={},
                    description="FastMCP test server",
                    enabled=False,
                ),
            },
            defaultServer="test",
            enabled=True,
        )
        self.save_config()

    def add_server(self, name: str, server: MCPServer) -> bool:
        """MCP 서버 추가"""
        try:
            self.config.mcpServers[name] = server
            self.save_config()
            logger.debug("MCP 서버 추가: %s", name)
            return True
        except Exception as exception:
            logger.error("MCP 서버 추가 실패: %s", exception)
            return False

    def update_server(self, name: str, server: MCPServer) -> bool:
        """MCP 서버 업데이트"""
        try:
            if name in self.config.mcpServers:
                self.config.mcpServers[name] = server
                self.save_config()
                logger.debug("MCP 서버 업데이트: %s", name)
                return True
            else:
                logger.warning("존재하지 않는 MCP 서버: %s", name)
                return False
        except Exception as exception:
            logger.error("MCP 서버 업데이트 실패: %s", exception)
            return False

    def remove_server(
        self, name: str, stop_server_callback: Optional[Callable[[str], bool]] = None
    ) -> bool:
        """MCP 서버 제거"""
        try:
            if name in self.config.mcpServers:
                # 실행 중인 서버 중지 (콜백이 제공된 경우)
                if stop_server_callback:
                    stop_server_callback(name)

                del self.config.mcpServers[name]

                # 기본 서버가 삭제된 경우 다른 서버로 변경
                if self.config.defaultServer == name:
                    servers = list(self.config.mcpServers.keys())
                    self.config.defaultServer = servers[0] if servers else None

                self.save_config()
                logger.debug("MCP 서버 제거: %s", name)
                return True
            else:
                logger.warning("존재하지 않는 MCP 서버: %s", name)
                return False
        except Exception as exception:
            logger.error("MCP 서버 제거 실패: %s", exception)
            return False

    def get_server_list(self) -> List[str]:
        """MCP 서버 목록 반환"""
        return list(self.config.mcpServers.keys())

    def get_server(self, name: str) -> Optional[MCPServer]:
        """특정 MCP 서버 정보 반환"""
        return self.config.mcpServers.get(name)

    def get_enabled_servers(self) -> Dict[str, MCPServer]:
        """활성화된 MCP 서버들 반환"""
        return {
            name: server
            for name, server in self.config.mcpServers.items()
            if server.enabled
        }

    def clear_servers(self):
        """모든 MCP 서버 설정을 지웁니다."""
        self.config.mcpServers.clear()
        self.config.defaultServer = None

    def get_servers(self) -> Dict[str, MCPServer]:
        """모든 MCP 서버 정보를 반환합니다."""
        return self.config.mcpServers

    def get_config(self) -> MCPConfig:
        """현재 설정 반환"""
        return self.config

    def set_default_server(self, name: str) -> bool:
        """기본 서버 설정"""
        try:
            if name in self.config.mcpServers or name is None:
                self.config.defaultServer = name
                self.save_config()
                logger.debug("기본 서버 설정: %s", name)
                return True
            else:
                logger.warning("존재하지 않는 MCP 서버: %s", name)
                return False
        except Exception as exception:
            logger.error("기본 서버 설정 실패: %s", exception)
            return False

    def set_enabled(self, enabled: bool) -> bool:
        """MCP 전체 활성화/비활성화"""
        try:
            self.config.enabled = enabled
            self.save_config()
            logger.debug("MCP 전체 %s", "활성화" if enabled else "비활성화")
            return True
        except Exception as exception:
            logger.error("MCP 활성화 설정 실패: %s", exception)
            return False
