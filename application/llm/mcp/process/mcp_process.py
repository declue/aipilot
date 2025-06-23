from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Any

# 연결 테스트에 필요한 MCP SDK
from agents.mcp import MCPServerStdio  # type: ignore
from mcp.shared.exceptions import McpError  # type: ignore

from application.llm.mcp.config.models.mcp_server import MCPServer
from application.llm.mcp.config.models.mcp_server_status import MCPServerStatus
from application.util.logger import setup_logger


class MCPProcess:
    """하나의 MCP 서버 인스턴스를 관리한다."""

    def __init__(self, server: MCPServer):
        self.server: MCPServer = server
        self.process: subprocess.Popen | None = None
        self.status: MCPServerStatus = MCPServerStatus(name=server.name, connected=False)
        # 개별 로거 ‒ 서버 이름을 서브 로거로 사용
        self.logger: logging.Logger = setup_logger("llm") or logging.getLogger("llm")

    def start(self) -> bool:
        """서버 프로세스 시작.

        실제로는 MCP 서버 바이너리/스크립트를 실행해야 하지만,
        현재 프로젝트에서는 별도 런처가 구현되지 않았으므로
        placeholder 로직을 유지한다.
        """
        if self.process:
            self.logger.warning("이미 실행 중인 프로세스가 있습니다: %s", self.server.name)
            return False

        try:
            # 플레이스홀더: 실제 실행 로직은 추후 구현
            self.logger.debug("(placeholder) MCP 서버 시작: %s", self.server.name)
            # 예: self.process = subprocess.Popen([...])
            return True
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error("MCP 서버 시작 실패 (%s): %s", self.server.name, exc)
            return False

    def stop(self) -> bool:
        """서버 프로세스 중단"""
        if not self.process:
            self.logger.debug("중단할 프로세스가 없습니다: %s", self.server.name)
            return False
        try:
            self.process.terminate()
            self.process = None
            self.logger.debug("MCP 서버 중지 완료: %s", self.server.name)
            return True
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error("MCP 서버 중지 실패 (%s): %s", self.server.name, exc)
            return False

    # ---------------------------------------------------------------------
    # 상태
    # ---------------------------------------------------------------------
    def is_running(self) -> bool:
        """프로세스가 실행 중인지 여부"""
        return self.process is not None and self.process.poll() is None

    async def test_connection(self) -> MCPServerStatus:
        """서버 연결 테스트 → status 캐싱 및 반환"""
        self.logger.debug("서버 연결 테스트 시작: %s", self.server.name)

        command = self.server.command
        args = self.server.args or []
        env = self.server.env or {}
        server_name = self.server.name

        try:
            async with MCPServerStdio(
                cache_tools_list=True, params={"command": command, "args": args, "env": env}
            ) as mcp_server:
                tools = await mcp_server.list_tools()
                self.status = MCPServerStatus(
                    name=server_name,
                    connected=True,
                    tools=[{"name": t.name, "description": t.description} for t in tools],
                )
        except McpError as exc:  # pylint: disable=broad-except
            self.status = MCPServerStatus(
                name=server_name,
                connected=False,
                error_message=f"MCP 오류: {str(exc)}",
            )
        except asyncio.TimeoutError:
            self.status = MCPServerStatus(
                name=server_name,
                connected=False,
                error_message="연결 시간 초과: 서버가 30초 내에 응답하지 않았습니다.",
            )
        except FileNotFoundError:
            self.status = MCPServerStatus(
                name=server_name,
                connected=False,
                error_message=(
                    f"명령어를 찾을 수 없음: 명령어 '{command}'를 찾을 수 없습니다. PATH를 확인하세요."
                ),
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.status = MCPServerStatus(
                name=server_name,
                connected=False,
                error_message=f"알 수 없는 오류: {type(exc).__name__} - {str(exc)}",
            )

        self.logger.debug(
            "서버 연결 테스트 완료: %s, connected=%s", self.server.name, self.status.connected
        )
        return self.status

    # ---------------------------------------------------------------------
    # 직렬화 / 헬퍼
    # ---------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """상태 포함 정보를 dict 로 직렬화 (UI/API 용)"""
        return {
            "name": self.server.name,
            "config": self.server.model_dump(exclude_none=True),
            "status": self.status.model_dump(exclude_none=True),
        } 