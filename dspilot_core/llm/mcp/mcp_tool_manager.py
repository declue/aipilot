"""
MCP 도구 관리자 - langchain-mcp-adapters 0.1.0+ 사용 + 캐싱 시스템
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from langchain_mcp_adapters.client import MultiServerMCPClient

from dspilot_core.llm.mcp.mcp_manager import MCPManager
from dspilot_core.util.logger import setup_logger

logger = setup_logger("mcp_tool_manager") or logging.getLogger(
    "mcp_tool_manager")

# MCP 서버 프로세스의 출력을 완전히 차단하기 위한 전역 패치
_original_popen = subprocess.Popen


def _silent_popen(*args, **kwargs):
    """MCP 서버 관련 프로세스의 출력을 자동으로 숨기는 Popen 래퍼"""
    # 명령어 확인
    if args and len(args) > 0:
        cmd = args[0]
        if isinstance(cmd, (list, tuple)) and len(cmd) > 0:
            cmd_str = str(cmd[0])
        else:
            cmd_str = str(cmd)

        # MCP 도구 관련 프로세스인지 확인
        mcp_indicators = [
            "mcp", "duckduckgo.py", "coder_mcp.py", "file_mcp_tool.py",
            "time.py", "weather.py", "github-mcp-server", "process_mcp.py",
            "chrome_mcp_tool.py", "remote_desktop.py", "bitbucket_mcp_tool.py"
        ]

        is_mcp_process = any(indicator in cmd_str.lower()
                             for indicator in mcp_indicators)

        if is_mcp_process:
            # MCP 프로세스의 경우 stdout/stderr를 DEVNULL로 리다이렉트
            kwargs.setdefault('stdout', subprocess.DEVNULL)
            kwargs.setdefault('stderr', subprocess.DEVNULL)

    return _original_popen(*args, **kwargs)


# 전역 패치 적용 (한 번만 실행)
if not hasattr(subprocess.Popen, '_mcp_patched'):
    subprocess.Popen = _silent_popen
    subprocess.Popen._mcp_patched = True

# MCP 관련 로거들의 출력 레벨을 ERROR로 설정하여 불필요한 로그 억제


def _suppress_mcp_logging():
    """MCP 관련 로거들의 출력을 억제"""
    mcp_loggers = [
        "mcp.server.lowlevel.server",
        "mcp.server.fastmcp",
        "fastmcp",
        "langchain_mcp_adapters",
        "langchain_mcp_adapters.client",
        "stdio_server",
        "__main__",  # MCP 도구들이 직접 실행될 때
    ]

    for logger_name in mcp_loggers:
        mcp_logger = logging.getLogger(logger_name)
        mcp_logger.setLevel(logging.ERROR)
        mcp_logger.propagate = False  # 상위 로거로 전파 방지


# 로깅 억제 적용
_suppress_mcp_logging()


@contextmanager
def suppress_stdout():
    """stdout을 임시로 숨기는 컨텍스트 매니저"""
    # 원본 stdout 저장
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    try:
        # devnull로 리디렉션
        with open(os.devnull, 'w') as devnull:
            sys.stdout = devnull
            sys.stderr = devnull
            yield
    finally:
        # 원본 stdout 복원
        sys.stdout = original_stdout
        sys.stderr = original_stderr


@contextmanager
def suppress_subprocess_output():
    """subprocess 출력을 숨기는 컨텍스트 매니저 (더 강력한 방법)"""
    # 파일 디스크립터 레벨에서 리디렉션
    original_stdout_fd = os.dup(1)  # stdout 복사
    original_stderr_fd = os.dup(2)  # stderr 복사
    devnull_fd = None

    try:
        # devnull로 리디렉션
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, 1)  # stdout을 devnull로
        os.dup2(devnull_fd, 2)  # stderr을 devnull로

        yield

    finally:
        # 원본 파일 디스크립터 복원
        os.dup2(original_stdout_fd, 1)
        os.dup2(original_stderr_fd, 2)
        os.close(original_stdout_fd)
        os.close(original_stderr_fd)
        if devnull_fd is not None:
            os.close(devnull_fd)


@contextmanager
def suppress_all_output():
    """모든 출력을 완전히 차단하는 더 강력한 컨텍스트 매니저"""
    import contextlib
    import io

    # 원본 출력 스트림 저장
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # 파일 디스크립터 레벨 억제
    original_stdout_fd = os.dup(1)
    original_stderr_fd = os.dup(2)
    devnull_fd = None

    try:
        # Python 레벨 출력 억제
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        # 파일 디스크립터 레벨 출력 억제
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)

        # 로그 핸들러 임시 비활성화
        root_logger = logging.getLogger()
        handlers_states = []
        for handler in root_logger.handlers:
            handlers_states.append(handler.disabled)
            handler.disabled = True

        yield

    finally:
        # 로그 핸들러 복원
        try:
            for handler, was_disabled in zip(root_logger.handlers, handlers_states):
                handler.disabled = was_disabled
        except:
            pass

        # 파일 디스크립터 복원
        try:
            os.dup2(original_stdout_fd, 1)
            os.dup2(original_stderr_fd, 2)
            os.close(original_stdout_fd)
            os.close(original_stderr_fd)
            if devnull_fd is not None:
                os.close(devnull_fd)
        except:
            pass

        # Python 출력 스트림 복원
        sys.stdout = original_stdout
        sys.stderr = original_stderr


class MCPToolCache:
    """MCP 도구 캐싱 시스템"""

    def __init__(self, cache_ttl: int = 300):  # 5분 TTL
        self.cache_ttl = cache_ttl
        # (tools, timestamp)
        self._tools_cache: Optional[Tuple[List[Any], float]] = None
        self._descriptions_cache: Optional[Tuple[str, float]] = None
        self._openai_tools_cache: Optional[Tuple[List[Dict[str, Any]], float]] = None
        self._tool_name_mapping: Dict[str, Any] = {}  # 빠른 이름 기반 조회

    def is_expired(self, timestamp: float) -> bool:
        """캐시가 만료되었는지 확인"""
        return time.time() - timestamp > self.cache_ttl

    def get_tools(self) -> Optional[List[Any]]:
        """캐시된 도구 목록 반환"""
        if self._tools_cache and not self.is_expired(self._tools_cache[1]):
            return self._tools_cache[0]
        return None

    def set_tools(self, tools: List[Any]) -> None:
        """도구 목록 캐싱"""
        self._tools_cache = (tools, time.time())
        # 이름 매핑도 업데이트
        self._tool_name_mapping = {tool.name: tool for tool in tools}
        logger.debug(f"도구 캐시 업데이트: {len(tools)}개 도구")

    def get_tool_by_name(self, name: str) -> Optional[Any]:
        """이름으로 도구 빠른 조회"""
        if self._tools_cache and not self.is_expired(self._tools_cache[1]):
            return self._tool_name_mapping.get(name)
        return None

    def get_descriptions(self) -> Optional[str]:
        """캐시된 도구 설명 반환"""
        if self._descriptions_cache and not self.is_expired(self._descriptions_cache[1]):
            return self._descriptions_cache[0]
        return None

    def set_descriptions(self, descriptions: str) -> None:
        """도구 설명 캐싱"""
        self._descriptions_cache = (descriptions, time.time())

    def get_openai_tools(self) -> Optional[List[Dict[str, Any]]]:
        """캐시된 OpenAI 형식 도구 반환"""
        if self._openai_tools_cache and not self.is_expired(self._openai_tools_cache[1]):
            return self._openai_tools_cache[0]
        return None

    def set_openai_tools(self, openai_tools: List[Dict[str, Any]]) -> None:
        """OpenAI 형식 도구 캐싱"""
        self._openai_tools_cache = (openai_tools, time.time())

    def clear_cache(self) -> None:
        """모든 캐시 초기화"""
        self._tools_cache = None
        self._descriptions_cache = None
        self._openai_tools_cache = None
        self._tool_name_mapping.clear()
        logger.info("MCP 도구 캐시 초기화 완료")


class MCPToolManager:
    """
    진정한 MCP 통합을 위한 도구 관리자
    langchain-mcp-adapters 0.1.0+ 사용 + 고성능 캐싱 시스템
    """

    def __init__(self, mcp_manager: MCPManager, config_manager: Any, cache_ttl: int = 300):
        self.mcp_manager = mcp_manager
        self.config_manager = config_manager
        self.mcp_client: Optional[MultiServerMCPClient] = None
        self.langchain_tools: List[Any] = []
        self._initialized = False
        self._lock = asyncio.Lock()

        # 캐싱 시스템 추가
        self.cache = MCPToolCache(cache_ttl)
        logger.debug(f"MCP 도구 관리자 초기화 (캐시 TTL: {cache_ttl}초)")

    @property
    def tools(self) -> List[Any]:
        """tools 속성 - CLI에서 참조용"""
        cached_tools = self.cache.get_tools()
        if cached_tools:
            return cached_tools
        return self.langchain_tools

    async def initialize(self) -> bool:
        """MCP 클라이언트 초기화"""
        async with self._lock:
            if self._initialized:
                return True

            try:
                # 기존 클라이언트 정리
                await self._cleanup_client()

                # MCP 설정 로드
                mcp_config = self.mcp_manager.get_mcp_config()
                if not mcp_config or not mcp_config.enabled:
                    logger.info("MCP가 비활성화되어 있습니다")
                    return False

                # 서버 설정 구성
                server_configs = self._build_server_configs(mcp_config)

                if not server_configs:
                    logger.warning("활성화된 MCP 서버가 없습니다")
                    return False

                logger.debug(f"MCP 서버 설정: {list(server_configs.keys())}")

                # MultiServerMCPClient 초기화 시 모든 출력 완전 억제
                with suppress_all_output():
                    self.mcp_client = MultiServerMCPClient(server_configs)

                # 직접 도구 로드 (langchain-mcp-adapters 0.1.0+ 방식)
                await self._load_tools()

                self._initialized = True
                logger.debug(
                    f"MCP 도구 관리자 초기화 완료: {len(self.langchain_tools)}개 도구")
                return True

            except Exception as e:
                logger.error(f"MCP 도구 관리자 초기화 실패: {e}")
                await self._cleanup_client()
                return False

    def _build_server_configs(self, mcp_config: Any) -> Dict[str, Dict[str, Any]]:
        """서버 설정 구성"""
        import subprocess
        server_configs = {}
        enabled_servers = mcp_config.get_enabled_servers()

        for server_name, server_data in enabled_servers.items():
            try:
                config = {"transport": "stdio"}  # 기본값

                # 명령어 설정
                if "command" in server_data:
                    config["command"] = server_data["command"]
                    config["args"] = server_data.get("args", [])

                    # subprocess 출력을 완전히 숨기기 위한 설정 추가
                    config["stdout"] = subprocess.DEVNULL
                    config["stderr"] = subprocess.DEVNULL

                elif "url" in server_data:
                    # SSE 전송 방식
                    config["url"] = server_data["url"]
                    config["transport"] = "sse"
                else:
                    logger.warning(f"서버 {server_name}: command 또는 url이 필요합니다")
                    continue

                # 환경 변수 설정 (기존 + 로그 제어)
                env = server_data.get("env", {}).copy()

                # 모든 MCP 도구들의 출력을 최소화하기 위한 환경 변수 설정
                env.update({
                    "PYTHONUNBUFFERED": "0",  # Python 출력 버퍼링 비활성화
                    "PYTHONIOENCODING": "utf-8",  # 인코딩 설정
                })

                # 개별 도구별 로그 제어
                if server_name == "web_search":
                    env["DUCKDUCKGO_LOG_LEVEL"] = "ERROR"
                elif server_name == "coder":
                    env["CODER_MCP_VERBOSE"] = "false"
                elif server_name == "file_explorer":
                    env["FILE_MCP_VERBOSE"] = "false"
                elif server_name == "time":
                    env["TIME_MCP_VERBOSE"] = "false"
                elif server_name == "weather":
                    env["WEATHER_MCP_VERBOSE"] = "false"
                elif server_name == "github":
                    env["GITHUB_MCP_VERBOSE"] = "false"
                elif server_name == "process":
                    env["PROCESS_MCP_VERBOSE"] = "false"

                config["env"] = env

                server_configs[server_name] = config

            except Exception as e:
                logger.error(f"서버 {server_name} 설정 구성 실패: {e}")

        return server_configs

    async def _load_tools(self) -> None:
        """Langchain 도구 로드 (새로운 API 사용) + 캐싱"""
        try:
            if not self.mcp_client:
                logger.warning("MCP 클라이언트가 초기화되지 않았습니다")
                return

            # langchain-mcp-adapters 0.1.0+ 방식: 직접 get_tools() 호출
            # 모든 출력을 완전히 숨기기 위해 강력한 컨텍스트 매니저 사용
            with suppress_all_output():
                self.langchain_tools = await self.mcp_client.get_tools()

            # 캐시에 저장
            self.cache.set_tools(self.langchain_tools)

            logger.debug(
                f"Langchain 도구 {len(self.langchain_tools)}개 로드 완료 (캐시됨)")
            for tool in self.langchain_tools:
                logger.debug(f"  - {tool.name}: {tool.description}")

        except Exception as e:
            logger.error(f"도구 로드 실패: {e}")
            # 에러 로그에 더 자세한 정보 추가
            import traceback

            logger.error(f"도구 로드 실패 상세: {traceback.format_exc()}")
            self.langchain_tools = []

    async def get_langchain_tools(self) -> List[Any]:
        """Langchain 도구 목록 반환 (캐시 우선)"""
        # 캐시에서 먼저 확인
        cached_tools = self.cache.get_tools()
        if cached_tools:
            logger.debug(f"캐시에서 도구 목록 반환: {len(cached_tools)}개")
            return cached_tools.copy()

        # 캐시 미스 시 초기화 후 반환
        if not self._initialized:
            await self.initialize()

        # 다시 캐시 확인
        cached_tools = self.cache.get_tools()
        if cached_tools:
            return cached_tools.copy()

        return self.langchain_tools.copy()

    def get_tool_by_name(self, name: str) -> Optional[Any]:
        """이름으로 도구 빠른 조회 (캐시 사용)"""
        cached_tool = self.cache.get_tool_by_name(name)
        if cached_tool:
            logger.debug(f"캐시에서 도구 조회: {name}")
            return cached_tool

        # 캐시 미스 시 직접 검색
        for tool in self.langchain_tools:
            if tool.name == name:
                return tool
        return None

    async def refresh_tools(self) -> None:
        """도구 목록 새로고침 (캐시 초기화 포함)"""
        async with self._lock:
            try:
                # 캐시 초기화
                self.cache.clear_cache()

                if self.mcp_client and self._initialized:
                    await self._load_tools()
                    logger.info("MCP 도구 목록 새로고침 완료 (캐시 재생성)")
                else:
                    logger.warning("MCP 클라이언트가 초기화되지 않아 새로고침을 건너뜁니다")
            except Exception as e:
                logger.error(f"도구 새로고침 실패: {e}")

    def get_tool_descriptions(self) -> str:
        """도구 설명 텍스트 반환 (캐시 사용)"""
        # 캐시에서 먼저 확인
        cached_descriptions = self.cache.get_descriptions()
        if cached_descriptions:
            logger.debug("캐시에서 도구 설명 반환")
            return cached_descriptions

        # 캐시 미스 시 생성
        if not self.langchain_tools:
            descriptions = "사용 가능한 MCP 도구가 없습니다."
        else:
            descriptions_list = []
            for tool in self.langchain_tools:
                descriptions_list.append(f"- {tool.name}: {tool.description}")
            descriptions = "\n".join(descriptions_list)

        # 캐시에 저장
        self.cache.set_descriptions(descriptions)
        return descriptions

    def get_tool_count(self) -> int:
        """도구 개수 반환 (캐시 우선)"""
        cached_tools = self.cache.get_tools()
        if cached_tools:
            return len(cached_tools)
        return len(self.langchain_tools)

    async def get_openai_tools(self) -> List[Dict[str, Any]]:
        """OpenAI 형식의 도구 스키마 반환 (캐시 사용)"""
        # 캐시에서 먼저 확인
        cached_openai_tools = self.cache.get_openai_tools()
        if cached_openai_tools:
            logger.debug(f"캐시에서 OpenAI 도구 스키마 반환: {len(cached_openai_tools)}개")
            return cached_openai_tools.copy()

        # 캐시 미스 시 생성
        tools = []
        for langchain_tool in self.langchain_tools:
            try:
                # Langchain 도구를 OpenAI 형식으로 변환
                args_schema = {}
                if hasattr(langchain_tool, "args_schema") and langchain_tool.args_schema:
                    try:
                        args_schema = langchain_tool.args_schema.model_json_schema()
                    except Exception as schema_e:
                        logger.warning(
                            f"도구 {langchain_tool.name} 스키마 변환 실패: {schema_e}")
                        args_schema = {"type": "object",
                                       "properties": {}, "required": []}

                tool_schema = {
                    "type": "function",
                    "function": {
                        "name": langchain_tool.name,
                        "description": langchain_tool.description,
                        "parameters": args_schema
                        or {"type": "object", "properties": {}, "required": []},
                    },
                }
                tools.append(tool_schema)
            except Exception as e:
                logger.warning(f"도구 {langchain_tool.name} 스키마 변환 실패: {e}")

        # 캐시에 저장
        self.cache.set_openai_tools(tools)
        logger.debug(f"OpenAI 도구 스키마 생성 및 캐시 저장: {len(tools)}개")
        return tools

    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """MCP 도구 호출 (빠른 이름 조회 사용)"""
        try:
            # 캐시를 통한 빠른 도구 조회
            target_tool = self.get_tool_by_name(tool_name)

            if not target_tool:
                return f"도구 '{tool_name}'을 찾을 수 없습니다."

            # 도구 실행 시 출력 억제 (특히 GitHub MCP Server 같은 바이너리 도구)
            with suppress_all_output():
                result = await target_tool.ainvoke(arguments)
            return str(result)

        except Exception as e:
            logger.error(f"MCP 도구 {tool_name} 호출 실패: {e}")
            return f"도구 호출 실패: {e}"

    async def _cleanup_client(self) -> None:
        """MCP 클라이언트 정리 (컨텍스트 매니저 사용 안 함)"""
        if self.mcp_client:
            try:
                # langchain-mcp-adapters 0.1.0+에서는 명시적 정리가 필요하지 않음
                # 단순히 None으로 설정
                self.mcp_client = None
                logger.debug("MCP 클라이언트 정리 완료")
            except Exception as e:
                logger.warning(f"MCP 클라이언트 정리 중 오류: {e}")

    async def cleanup(self) -> None:
        """리소스 정리"""
        async with self._lock:
            try:
                await self._cleanup_client()
                self.langchain_tools = []
                self._initialized = False
                logger.debug("MCP 도구 관리자 정리 완료")

            except Exception as e:
                logger.error(f"MCP 도구 관리자 정리 실패: {e}")

    # 하위 호환성을 위한 메서드들
    async def start_servers(self) -> None:
        """서버 시작 (하위 호환성)"""
        await self.initialize()

    async def run_agent_with_tools(self, user_message: str) -> Dict[str, Any]:
        """에이전트 실행 (하위 호환성 - 사용하지 않음)"""
        logger.warning(
            "run_agent_with_tools는 더 이상 사용되지 않습니다. ReAct 에이전트를 직접 사용하세요."
        )
        return {
            "response": "이 메서드는 더 이상 사용되지 않습니다. LLMAgent를 직접 사용하세요.",
            "used_tools": [],
        }

    def stop_all_servers(self) -> None:
        """서버 중지 (하위 호환성)"""
        asyncio.create_task(self.cleanup())

    # 컨텍스트 매니저 지원 (사용하지 않는 것을 권장)
    async def __aenter__(self) -> "MCPToolManager":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.cleanup()
