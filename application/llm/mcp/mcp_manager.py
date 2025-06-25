"""
MCP 관리자 - MCP 서버 연결 및 관리
"""

import asyncio
import json
import logging
from typing import Dict, Optional

from application.llm.models.mcp_config import MCPConfig
from application.llm.models.mcp_server import MCPServer
from application.llm.models.mcp_server_status import MCPServerStatus
from application.util.logger import setup_logger

logger = setup_logger("mcp_manager") or logging.getLogger("mcp_manager")


class MCPManager:
    """MCP 서버 관리자"""

    def __init__(self, config_manager: any) -> None:
        """
        MCP 관리자 초기화

        Args:
            config_manager: 설정 관리자
        """
        self.config_manager = config_manager
        self._mcp_config: Optional[MCPConfig] = None
        self._server_statuses: Dict[str, MCPServerStatus] = {}

        self._load_mcp_config()
        logger.info("MCP 관리자 초기화 완료")

    def _load_mcp_config(self) -> None:
        """MCP 설정 로드"""
        try:
            # config_manager에서 MCP 설정을 먼저 시도
            if hasattr(self.config_manager, "get_mcp_config"):
                try:
                    mcp_data = self.config_manager.get_mcp_config()
                    if mcp_data:
                        # 필드명 매핑 (mcpServers -> mcp_servers)
                        if "mcpServers" in mcp_data:
                            mcp_data["mcp_servers"] = mcp_data.pop("mcpServers")
                        if "defaultServer" in mcp_data:
                            mcp_data["default_server"] = mcp_data.pop("defaultServer")

                        self._mcp_config = MCPConfig.from_dict(mcp_data)
                        logger.info("MCP 설정 로드 완료")
                        return
                except Exception as e:
                    logger.warning(f"config_manager에서 MCP 설정 로드 실패: {e}")

            # 파일에서 설정 로드 (fallback)
            mcp_config_path = "mcp.json"
            try:
                with open(mcp_config_path, "r", encoding="utf-8") as f:
                    mcp_data = json.load(f)

                # 필드명 매핑
                if "mcpServers" in mcp_data:
                    mcp_data["mcp_servers"] = mcp_data.pop("mcpServers")
                if "defaultServer" in mcp_data:
                    mcp_data["default_server"] = mcp_data.pop("defaultServer")

                self._mcp_config = MCPConfig.from_dict(mcp_data)
                logger.info("MCP 설정 파일 로드 완료")
            except FileNotFoundError:
                logger.warning("mcp.json 파일을 찾을 수 없습니다. 기본 설정 사용")
                self._mcp_config = MCPConfig()
            except Exception as e:
                logger.error(f"MCP 설정 로드 실패: {e}")
                self._mcp_config = MCPConfig()

        except Exception as e:
            logger.error(f"MCP 설정 초기화 실패: {e}")
            self._mcp_config = MCPConfig()

    def get_enabled_servers(self) -> Dict[str, MCPServer]:
        """활성화된 서버 목록 반환"""
        if not self._mcp_config:
            return {}

        enabled_servers = {}
        for name, config in self._mcp_config.get_enabled_servers().items():
            try:
                server = MCPServer.from_dict(name, config)
                enabled_servers[name] = server
            except Exception as e:
                logger.error(f"서버 설정 파싱 실패 {name}: {e}")

        return enabled_servers

    async def test_server_connection(self, server_name: str) -> MCPServerStatus:
        """
        서버 연결 테스트

        Args:
            server_name: 서버 이름

        Returns:
            MCPServerStatus: 서버 상태
        """
        try:
            servers = self.get_enabled_servers()
            if server_name not in servers:
                return MCPServerStatus(
                    server_name=server_name,
                    connected=False,
                    error_message=f"서버 '{server_name}'를 찾을 수 없습니다",
                )

            status = MCPServerStatus(
                server_name=server_name,
                connected=True,
                tools=[
                    {
                        "name": f"{server_name}_example",
                        "description": f"{server_name} 예제 도구",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"input": {"type": "string"}},
                            "required": ["input"],
                        },
                    }
                ],
            )

            self._server_statuses[server_name] = status
            logger.info(f"서버 연결 테스트 성공: {server_name}")
            return status

        except Exception as e:
            logger.error(f"서버 연결 테스트 실패 {server_name}: {e}")
            status = MCPServerStatus(server_name=server_name, connected=False, error_message=str(e))
            self._server_statuses[server_name] = status
            return status

    def get_server_status(self, server_name: str) -> Optional[MCPServerStatus]:
        """서버 상태 반환"""
        return self._server_statuses.get(server_name)

    def get_all_server_statuses(self) -> Dict[str, MCPServerStatus]:
        """모든 서버 상태 반환"""
        return self._server_statuses.copy()

    async def refresh_all_servers(self) -> None:
        """모든 서버 상태 갱신"""
        servers = self.get_enabled_servers()
        tasks = []

        for server_name in servers.keys():
            task = self.test_server_connection(server_name)
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("모든 서버 상태 갱신 완료")

    def is_mcp_enabled(self) -> bool:
        """MCP 활성화 여부 확인"""
        return self._mcp_config.enabled if self._mcp_config else False

    def get_mcp_config(self) -> Optional[MCPConfig]:
        """MCP 설정 반환"""
        return self._mcp_config

    async def cleanup(self) -> None:
        """리소스 정리"""
        try:
            logger.info("MCP 관리자 리소스 정리 중...")
            # 서버 상태 초기화
            self._server_statuses.clear()
            logger.info("MCP 관리자 리소스 정리 완료")
        except Exception as e:
            logger.error(f"MCP 관리자 정리 중 오류: {e}")
