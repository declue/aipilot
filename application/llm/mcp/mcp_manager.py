import logging
from typing import Any

from application.config.config_manager import ConfigManager
from application.llm.mcp.config.mcp_config_manager import MCPConfigManager
from application.llm.mcp.config.models.mcp_server import MCPServer
from application.llm.mcp.config.models.mcp_server_status import MCPServerStatus
from application.llm.mcp.process import MCPProcess
from application.util.logger import setup_logger


# pylint: disable=too-many-instance-attributes
class MCPManager:
    """MCP 서버 관리 클래스"""

    def __init__(
        self,
        config_manager: ConfigManager,
        mcp_config: MCPConfigManager | None = None,
    ) -> None:
        """MCPManager 생성자

        파라미터
        ----------
        config_manager : ConfigManager
            전역 설정을 관리하는 ConfigManager 인스턴스
        mcp_config : Optional[MCPConfigManager]
            별도의 MCPConfigManager 인스턴스를 주입 받아 테스트 용이성을 높입니다. 미지정 시 내부에서 생성합니다.
        """

        self.logger: logging.Logger = setup_logger("mcp_manager") or logging.getLogger(__name__)

        self.config_manager: ConfigManager = config_manager
        self.mcp_config: MCPConfigManager = mcp_config or MCPConfigManager()
        self.processes: dict[str, MCPProcess] = {}
        self.load_config()

    def get_config_manager(self) -> MCPConfigManager:
        """설정 관리자 반환"""
        return self.mcp_config

    def remove_server(self, name: str) -> bool:
        """MCP 서버 제거 (실행 중인 서버 중지 포함)"""
        if self.mcp_config.remove_server(name, self.stop_server):
            self.processes.pop(name, None)
            return True
        return False

    # Config 관련 프록시 메서드들 (하위 호환성 유지)
    def add_server(self, name: str, server: MCPServer) -> bool:
        """MCP 서버 추가"""
        if self.mcp_config.add_server(name, server):
            # 서버 객체에 이름 설정(런타임용)
            server.name = name
            self.processes[name] = MCPProcess(server)
            return True
        return False

    def update_server(self, name: str, server: MCPServer) -> bool:
        """MCP 서버 업데이트"""
        if self.mcp_config.update_server(name, server):
            # 기존 프로세스 삭제 후 새로 등록
            server.name = name
            self.processes[name] = MCPProcess(server)
            return True
        return False

    def get_server_list(self) -> list[str]:
        """MCP 서버 목록 반환"""
        return self.mcp_config.get_server_list()

    def get_server(self, name: str) -> MCPServer | None:
        """특정 MCP 서버 정보 반환"""
        return self.mcp_config.get_server(name)

    def load_config(self) -> None:
        """ConfigManager로부터 MCP 서버 설정을 로드합니다."""
        self.mcp_config.clear_servers()
        self.processes.clear()

        mcp_config: dict[str, Any] = self.config_manager.get_mcp_config()
        server_configs: Any = mcp_config.get("mcpServers", {})
        for server_name, server_config in server_configs.items():
            # server_config가 딕셔너리인 경우 MCPServer 객체로 변환
            if isinstance(server_config, dict):
                server_config["name"] = server_name  # name 필드 추가
                server = MCPServer(**server_config)
                self.mcp_config.add_server(server_name, server)

                # MCPProcess 생성 및 등록
                server.name = server_name
                self.processes[server_name] = MCPProcess(server)

    def save_config(self) -> bool:
        """MCP 설정 파일 저장"""
        return self.mcp_config.save_config()

    def start_server(self, name: str) -> bool:
        """MCP 서버 시작"""
        process = self.processes.get(name)
        if not process:
            self.logger.warning("존재하지 않는 MCP 서버: %s", name)
            return False
        return process.start()

    def stop_server(self, name: str) -> bool:
        """MCP 서버 중지"""
        process = self.processes.get(name)
        if not process:
            self.logger.warning("존재하지 않는 MCP 서버: %s", name)
            return False
        return process.stop()

    def get_server_status(self, name: str) -> MCPServerStatus | None:
        """서버 상태 반환"""
        process = self.processes.get(name)
        return process.status if process else None

    def get_all_server_statuses(self) -> dict[str, MCPServerStatus]:
        """모든 서버 상태 반환"""
        return {name: proc.status for name, proc in self.processes.items()}

    def get_all_servers(self) -> list[MCPServer]:
        """설정된 모든 MCP 서버 목록을 반환합니다."""
        return list(self.mcp_config.get_servers().values())

    def get_server_by_name(self, name: str) -> MCPServer | None:
        """이름으로 MCP 서버를 찾아 반환합니다."""
        return self.mcp_config.get_server(name)

    def get_enabled_servers(self) -> dict[str, MCPServer]:
        """활성화된 서버 목록을 반환합니다."""
        return {
            name: server for name, server in self.mcp_config.get_servers().items() if server.enabled
        }

    async def test_server_connection(self, server_name: str) -> MCPServerStatus:
        """지정된 MCP 서버의 연결을 테스트합니다."""
        process = self.processes.get(server_name)
        if not process:
            return MCPServerStatus(
                name=server_name,
                connected=False,
                error_message="서버를 찾을 수 없습니다.",
            )

        return await process.test_connection()
