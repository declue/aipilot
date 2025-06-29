"""MCP 처리 핸들러"""

from typing import Any, Dict

from dspilot_app.api.handlers.base_handler import BaseHandler


class MCPHandler(BaseHandler):
    """MCP 관련 API 처리를 담당하는 핸들러"""

    async def get_mcp_servers(self) -> Dict[str, Any]:
        """모든 MCP 서버 목록 반환"""
        try:
            self._log_request("get_mcp_servers")

            servers = {}
            for name in self.mcp_manager.get_server_list():
                server = self.mcp_manager.get_server(name)
                if server:
                    servers[name] = {
                        "command": server.command,
                        "args": server.args,
                        "description": server.description,
                        "enabled": server.enabled,
                    }

            return self._create_success_response(
                "MCP 서버 목록 조회 완료", {"servers": servers, "total": len(servers)}
            )
        except Exception as exception:
            return self._create_error_response("MCP 서버 목록 조회 실패", exception)

    async def get_mcp_server_status(self, server_name: str) -> Dict[str, Any]:
        """특정 MCP 서버 상태 반환"""
        try:
            self._log_request("get_mcp_server_status", {"server_name": server_name})

            status = await self.mcp_manager.test_server_connection(server_name)

            return self._create_success_response(
                f"MCP 서버 '{server_name}' 상태 조회 완료",
                {
                    "server_name": server_name,
                    "connected": status.connected,
                    "tools_count": len(status.tools),
                    "resources_count": len(status.resources),
                    "prompts_count": len(status.prompts),
                    "error_message": status.error_message,
                },
            )
        except Exception as exception:
            return self._create_error_response("MCP 서버 상태 확인 실패", exception)

    async def get_mcp_server_tools(self, server_name: str) -> Dict[str, Any]:
        """특정 MCP 서버의 도구 목록 반환"""
        try:
            self._log_request("get_mcp_server_tools", {"server_name": server_name})

            status = await self.mcp_manager.test_server_connection(server_name)

            return self._create_success_response(
                f"MCP 서버 '{server_name}' 도구 목록 조회 완료",
                {
                    "server_name": server_name,
                    "connected": status.connected,
                    "tools": status.tools,
                    "resources": status.resources,
                    "prompts": status.prompts,
                },
            )
        except Exception as exception:
            return self._create_error_response("MCP 서버 도구 목록 조회 실패", exception)

    async def get_enabled_mcp_servers(self) -> Dict[str, Any]:
        """활성화된 MCP 서버들만 반환"""
        try:
            self._log_request("get_enabled_mcp_servers")

            enabled_servers = self.mcp_manager.get_enabled_servers()

            servers_info = {}
            for name, server in enabled_servers.items():
                # 서버 상태도 함께 조회
                status = self.mcp_manager.get_server_status(name)
                servers_info[name] = {
                    "command": server.command,
                    "args": server.args,
                    "description": server.description,
                    "connected": status.connected if status else False,
                    "tools_count": len(status.tools) if status else 0,
                    "resources_count": len(status.resources) if status else 0,
                    "prompts_count": len(status.prompts) if status else 0,
                }

            return self._create_success_response(
                "활성화된 MCP 서버 조회 완료",
                {
                    "enabled_servers": servers_info,
                    "total": len(servers_info),
                },
            )
        except Exception as exception:
            return self._create_error_response("활성화된 MCP 서버 조회 실패", exception)
