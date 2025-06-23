import asyncio
from typing import Dict, List

from PySide6.QtCore import QThread, Signal

from application.llm.mcp.config.models.mcp_server_status import MCPServerStatus


class MCPDataLoader(QThread):
    """MCP 데이터 로드를 처리하는 워커 스레드"""

    data_loaded = Signal(dict, list)  # server_data, tools_data
    error_occurred = Signal(str)  # error_message

    def __init__(self, mcp_manager, mcp_tool_manager):
        super().__init__()
        self.mcp_manager = mcp_manager
        self.mcp_tool_manager = mcp_tool_manager

    def run(self):
        """스레드에서 실행될 메서드"""
        try:
            # 새 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 서버 데이터 로드
                server_data = loop.run_until_complete(self._load_server_data())

                # 도구 데이터 로드
                tools_data = loop.run_until_complete(self._load_tools_data())

                # 성공 시그널 발출
                self.data_loaded.emit(server_data, tools_data)

            finally:
                loop.close()

        except Exception as e:
            self.error_occurred.emit(str(e))

    async def _load_server_data(self):
        """서버 데이터 로드"""
        server_data = {}

        try:
            server_list = self.mcp_manager.get_server_list()
            print(f"[MCP] 전체 서버 목록: {server_list}")

            enabled_servers = self.mcp_manager.get_enabled_servers()
            print(f"[MCP] 활성화된 서버: {list(enabled_servers.keys())}")

            for server_name in server_list:
                try:
                    # 서버 정보 가져오기
                    server = self.mcp_manager.get_server(server_name)
                    if not server:
                        print(f"[MCP] 서버 {server_name} 정보를 가져올 수 없음")
                        continue

                    print(
                        f"[MCP] 서버 {server_name}: enabled={server.enabled}, command={server.command}"
                    )

                    # 서버 상태 테스트 (활성화된 서버만)
                    if server.enabled:
                        print(f"[MCP] 서버 {server_name} 연결 테스트 시작...")
                        status = await self.mcp_manager.test_server_connection(
                            server_name
                        )
                        print(
                            f"[MCP] 서버 {server_name} 연결 결과: connected={status.connected}"
                        )
                        if not status.connected and status.error_message:
                            print(
                                f"[MCP] 서버 {server_name} 오류: {status.error_message}"
                            )
                        if status.connected:
                            print(
                                f"[MCP] 서버 {server_name} 도구: {len(status.tools)}개, 리소스: {len(status.resources)}개"
                            )
                    else:
                        # 비활성화된 서버는 빈 상태 객체 생성

                        status = MCPServerStatus(
                            name=server_name,
                            connected=False,
                            tools=[],
                            resources=[],
                            prompts=[],
                            error_message="서버가 비활성화됨",
                        )

                    server_data[server_name] = {
                        "config": server,
                        "status": status,
                        "name": server_name,
                    }

                except Exception as e:
                    print(f"⚠️  서버 {server_name} 상태 확인 실패: {str(e)}")
                    import traceback

                    traceback.print_exc()

        except Exception as e:
            print(f"❌ 서버 데이터 로드 중 오류: {str(e)}")
            import traceback

            traceback.print_exc()

        return server_data

    async def _load_tools_data(self):
        """도구 데이터 로드"""
        try:
            if not self.mcp_tool_manager:
                print("❌ MCP 도구 관리자가 None입니다")
                return []

            tools_data = await self.mcp_tool_manager.get_openai_tools()
            print(f"🔧 도구 {len(tools_data)}개 로드됨")

            # 도구 목록 상세 로깅
            for i, tool in enumerate(tools_data):
                func_info = tool.get("function", {})
                tool_name = func_info.get("name", "Unknown")
                print(f"  [{i+1}] {tool_name}")

            return tools_data
        except Exception as e:
            print(f"❌ 도구 로드 실패: {str(e)}")
            import traceback

            traceback.print_exc()
            return []


class MCPDataManager:
    """MCP 데이터 관리 클래스"""

    def __init__(self, mcp_manager, mcp_tool_manager):
        self.mcp_manager = mcp_manager
        self.mcp_tool_manager = mcp_tool_manager

        # 데이터 캐시
        self.server_data: Dict = {}
        self.tools_data: List = []

        # 데이터 로더 스레드
        self.data_loader = None

    def refresh_data(self, on_success=None, on_error=None):
        """데이터 새로고침"""
        # 이미 로딩 중이면 무시
        if self.data_loader and self.data_loader.isRunning():
            return

        # 워커 스레드로 데이터 로드
        self.data_loader = MCPDataLoader(self.mcp_manager, self.mcp_tool_manager)

        if on_success:
            self.data_loader.data_loaded.connect(on_success)
        if on_error:
            self.data_loader.error_occurred.connect(on_error)

        self.data_loader.start()

    def update_cache(self, server_data, tools_data):
        """캐시 업데이트"""
        self.server_data = server_data
        self.tools_data = tools_data

    def get_server_data(self):
        """서버 데이터 반환"""
        return self.server_data

    def get_tools_data(self):
        """도구 데이터 반환"""
        return self.tools_data

    def is_loading(self):
        """데이터 로딩 중인지 확인"""
        return self.data_loader and self.data_loader.isRunning()

    def cleanup(self):
        """리소스 정리"""
        if self.data_loader and self.data_loader.isRunning():
            self.data_loader.quit()
            self.data_loader.wait()
