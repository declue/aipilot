import asyncio

from agents.mcp import MCPServerStdio
from mcp.shared.exceptions import McpError

from application.llm.mcp.models.mcp_server import MCPServer
from application.llm.mcp.models.mcp_server_status import MCPServerStatus


async def test_mcp_server(server: MCPServer) -> MCPServerStatus:
    """비동기적으로 MCP 서버 연결을 테스트합니다."""
    command = server.command
    args = server.args or []
    env = server.env or {}
    server_name = server.name

    try:
        async with MCPServerStdio(
            cache_tools_list=True, params={"command": command, "args": args, "env": env}
        ) as mcp_server:
            tools = await mcp_server.list_tools()
            return MCPServerStatus(
                name=server_name,
                connected=True,
                tools=[
                    {"name": tool.name, "description": tool.description}
                    for tool in tools
                ],
            )
    except McpError as e:
        return MCPServerStatus(
            name=server_name,
            connected=False,
            error_message=f"MCP 오류: {e.message}",
        )
    except asyncio.TimeoutError:
        return MCPServerStatus(
            name=server_name,
            connected=False,
            error_message="연결 시간 초과: 서버가 30초 내에 응답하지 않았습니다.",
        )
    except FileNotFoundError:
        return MCPServerStatus(
            name=server_name,
            connected=False,
            error_message=f"명령어를 찾을 수 없음: 명령어 '{command}'를 찾을 수 없습니다. PATH를 확인하세요.",
        )
    except Exception as e:
        return MCPServerStatus(
            name=server_name,
            connected=False,
            error_message=f"알 수 없는 오류: {type(e).__name__} - {str(e)}",
        )
