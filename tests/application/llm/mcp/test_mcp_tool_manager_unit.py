from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from application.config.config_manager import ConfigManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager, _retry_async
from application.llm.mcp.tool.cache import ToolCache


class DummyServerConfig:  # pylint: disable=too-few-public-methods
    """가벼운 서버 설정 객체 대체품"""

    def __init__(self, command: str = "python", args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
        self.command = command
        self.args = args or []
        self.env = env or {}


class DummyMCPStatus:  # pylint: disable=too-few-public-methods
    """`MCPManager.test_server_connection` 의 반환값을 모방"""

    def __init__(self, connected: bool = True, tools: Optional[List[Dict[str, Any]]] = None):
        self.connected = connected
        self.tools = tools or []


class DummyMCPManager:  # pylint: disable=too-few-public-methods
    """MCPManager 의 최소 동작만 지원하는 스텁"""

    def __init__(self, status_map: Dict[str, DummyMCPStatus]):
        self._status_map = status_map

    def get_enabled_servers(self):  # noqa: D401
        """활성화된 서버 설정 반환"""
        return {name: DummyServerConfig() for name in self._status_map.keys()}

    async def test_server_connection(self, server_name):  # noqa: D401
        """비동기 서버 연결 테스트 – 사전 정의된 상태 반환"""
        return self._status_map.get(server_name)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_tools_and_build_openai_tools(tmp_path):
    """`refresh_tools` 실행 후 캐시와 변환 결과가 올바른지 확인"""

    # 1) MCP 상태 및 매니저 준비
    status = DummyMCPStatus(
        connected=True,
        tools=[
            {
                "name": "add",
                "description": "Add two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    "required": ["a", "b"],
                },
            }
        ],
    )
    mcp_manager = DummyMCPManager({"calc": status})

    # 2) ConfigManager (빈 설정 파일) 준비
    cfg_path = tmp_path / "app.config"
    cm = ConfigManager(config_file=str(cfg_path))

    tool_manager = MCPToolManager(mcp_manager, cm)

    # 3) refresh_tools 실행
    await tool_manager.refresh_tools()

    # 4) 캐시에 키가 존재하는지 확인
    assert "calc_add" in tool_manager._cache  # pylint: disable=protected-access

    # 5) OpenAI 함수 포맷 변환 확인
    openai_tools = tool_manager._build_openai_tools_response()  # pylint: disable=protected-access
    assert len(openai_tools) == 1
    func_meta = openai_tools[0]["function"]
    assert func_meta["name"] == "calc_add"
    # 서버명이 대문자로 설명에 포함되는지 확인
    assert "[CALC]" in func_meta["description"]
    # 파라미터 스키마가 그대로 전달되는지 확인
    assert set(func_meta["parameters"]["properties"].keys()) == {"a", "b"}


@pytest.mark.asyncio
async def test_get_tool_descriptions(tmp_path):
    """`get_tool_descriptions` 가 캐시 내용을 요약해서 보여주는지 테스트"""

    cm = ConfigManager(config_file=str(tmp_path / "cfg"))
    mcp_manager = DummyMCPManager({})
    tool_manager = MCPToolManager(mcp_manager, cm)

    # 캐시에 직접 도구 추가
    cache: ToolCache = tool_manager._cache  # pylint: disable=protected-access
    cache.add(
        "srv_tool",
        "srv",
        "tool",
        {"description": "example", "inputSchema": {}},
    )

    desc = tool_manager.get_tool_descriptions()
    assert "=== 사용 가능한 MCP 도구들 ===" in desc
    assert "srv_tool" in desc


@pytest.mark.asyncio
async def test_run_agent_with_tools_simple_no_pattern(tmp_path):
    """도구 패턴이 없을 때 적절한 오류 메시지 반환"""
    cm = ConfigManager(config_file=str(tmp_path / "cfg"))
    tool_manager = MCPToolManager(DummyMCPManager({}), cm)

    result = await tool_manager._run_agent_with_tools_simple("hello")  # pylint: disable=protected-access

    assert result["used_tools"] == []
    assert "도구 호출 패턴을 찾지 못했습니다" in result["response"]


@pytest.mark.asyncio
async def test_retry_async_retries():
    """`_retry_async` 가 예외 발생 시 재시도 후 성공하는지 확인"""

    attempts: List[int] = []

    async def flaky():  # noqa: D401
        attempts.append(1)
        if len(attempts) < 2:
            raise RuntimeError("fail once")
        return "success"

    result = await _retry_async(flaky, attempts=3, backoff=0)
    assert result == "success"
    # 두 번 호출되었는지 확인 (1 실패 + 1 성공)
    assert len(attempts) == 2


@pytest.mark.asyncio
async def test_run_agent_with_tools_stop(monkeypatch, tmp_path):
    """`run_agent_with_tools` 경로 중 finish_reason == 'stop' 처리를 검증"""
    cm = ConfigManager(config_file=str(tmp_path / "cfg"))
    tool_manager = MCPToolManager(DummyMCPManager({}), cm)

    # (1) `get_openai_tools` 를 비어 있지 않은 리스트로 대체 – 네트워크 호출 방지
    async def fake_get_tools():  # noqa: D401
        return [
            {
                "type": "function",
                "function": {"name": "dummy", "description": "d", "parameters": {}},
            }
        ]

    monkeypatch.setattr(tool_manager, "get_openai_tools", fake_get_tools)

    # (2) `_retry_async` 패치 – 첫 호출에 finish_reason='stop' 을 반환
    async def fake_retry(_factory, *_, **__):  # noqa: D401
        class _Choice:  # pylint: disable=too-few-public-methods
            def __init__(self):
                self.finish_reason = "stop"
                self.message = SimpleNamespace(content="FINAL")

        class _Resp:  # pylint: disable=too-few-public-methods
            choices = [_Choice()]

        return _Resp()

    monkeypatch.setattr("application.llm.mcp.mcp_tool_manager._retry_async", fake_retry)

    result = await tool_manager.run_agent_with_tools("question")

    assert result["response"] == "FINAL"
    assert result["used_tools"] == []


@pytest.mark.asyncio
async def test_run_agent_with_tools_tool_call(monkeypatch, tmp_path):
    """tool_calls → stop 의 2스텝 시나리오 테스트"""
    cm = ConfigManager(config_file=str(tmp_path / "cfg"))
    tool_manager = MCPToolManager(DummyMCPManager({}), cm)

    # dummy tool list
    async def fake_get_tools():  # noqa: D401
        return [
            {
                "type": "function",
                "function": {"name": "calc_add", "description": "d", "parameters": {}},
            }
        ]

    monkeypatch.setattr(tool_manager, "get_openai_tools", fake_get_tools)

    # (1) call_mcp_tool 더미 – 실제 실행 방지
    async def fake_call(tool_key, arguments):  # noqa: D401
        return f"RESULT {tool_key} {arguments}"

    monkeypatch.setattr(tool_manager, "call_mcp_tool", fake_call)

    # (2) `_retry_async`가 두 번 호출되도록 시퀀스 준비
    call_count = {"n": 0}

    async def fake_retry(_factory, *_, **__):  # noqa: D401
        call_count["n"] += 1

        if call_count["n"] == 1:
            # 첫 번째 – tool_calls 반환
            dummy_tool_call = SimpleNamespace(
                id="id1",
                function=SimpleNamespace(name="calc_add", arguments="{}"),
            )

            class _Choice:  # pylint: disable=too-few-public-methods
                finish_reason = "tool_calls"
                message = SimpleNamespace(content=None, tool_calls=[dummy_tool_call])

            class _Resp:  # pylint: disable=too-few-public-methods
                choices = [_Choice()]

            return _Resp()

        # 두 번째 – stop 반환
        class _Choice:  # pylint: disable=too-few-public-methods
            finish_reason = "stop"
            message = SimpleNamespace(content="DONE")

        class _Resp:  # pylint: disable=too-few-public-methods
            choices = [_Choice()]

        return _Resp()

    monkeypatch.setattr("application.llm.mcp.mcp_tool_manager._retry_async", fake_retry)

    result = await tool_manager.run_agent_with_tools("question with function call")

    # tool 이 한 번 사용되었고 최종 응답이 DONE 이어야 함
    assert result["used_tools"] == ["calc_add"]
    assert result["response"] == "DONE"


# ---------------------------------------------------------------------------
# 추가 단위 테스트: call_mcp_tool 위임 확인
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_mcp_tool_delegates(tmp_path):
    """`call_mcp_tool` 이 내부 Executor 에 위임하는지 테스트"""

    cm = ConfigManager(config_file=str(tmp_path / "cfg"))
    tool_manager = MCPToolManager(DummyMCPManager({}), cm)

    # Dummy executor 교체
    class DummyExecutor:  # pylint: disable=too-few-public-methods
        def __init__(self):
            self.called = False

        async def __call__(self, tool_key, arguments):  # noqa: D401
            self.called = True
            assert tool_key == "foo"
            assert arguments == {"x": 1}
            return "BAR"

    dummy_exec = DummyExecutor()
    tool_manager._executor = dummy_exec  # type: ignore[attr-defined]  # pylint: disable=protected-access

    result = await tool_manager.call_mcp_tool("foo", {"x": 1})

    assert result == "BAR"
    assert dummy_exec.called


# ---------------------------------------------------------------------------
# get_openai_tools 동작 확인
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_openai_tools_from_cache(tmp_path):
    cm = ConfigManager(config_file=str(tmp_path / "cfg"))
    tool_manager = MCPToolManager(DummyMCPManager({}), cm)

    # 캐시 미리 채우기
    tool_manager._cache.add(
        "srv_tool",
        "srv",
        "tool",
        {"description": "desc", "inputSchema": {}},
    )  # pylint: disable=protected-access

    tools = await tool_manager.get_openai_tools()

    # 반환 형식 및 개수 확인
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "srv_tool"


@pytest.mark.asyncio
async def test_run_agent_with_tools_simple_with_streaming_callback(tmp_path):
    """간소화 모드에서 streaming callback이 도구 실행 결과를 표시하는지 테스트"""
    cm = ConfigManager(config_file=str(tmp_path / "cfg"))
    tool_manager = MCPToolManager(DummyMCPManager({}), cm)
    
    # call_mcp_tool 모킹
    async def fake_call_tool(tool_key, arguments):
        return "도구 실행 결과: 성공"
    
    tool_manager.call_mcp_tool = fake_call_tool
    
    # streaming callback으로 전달된 메시지들을 수집
    callback_messages = []
    
    def streaming_callback(msg):
        callback_messages.append(msg)
    
    result = await tool_manager._run_agent_with_tools_simple(  # pylint: disable=protected-access
        "test_tool(arg='value')", streaming_callback
    )
    
    # 결과 검증
    assert result["response"] == "도구 실행 결과: 성공"
    assert "test_tool" in result["used_tools"]
    
    # streaming callback 메시지 검증
    callback_text = "".join(callback_messages)
    assert "🛠️ MCP 도구 'test_tool' 호출 중..." in callback_text
    assert "📋 도구 실행 결과:" in callback_text
    assert "도구 실행 결과: 성공" in callback_text


@pytest.mark.asyncio  
async def test_run_agent_with_tools_simple_streaming_with_long_result(tmp_path):
    """간소화 모드에서 긴 도구 실행 결과가 적절히 요약되는지 테스트"""
    cm = ConfigManager(config_file=str(tmp_path / "cfg"))
    tool_manager = MCPToolManager(DummyMCPManager({}), cm)
    
    # 500자를 넘는 긴 결과를 반환하는 모킹
    long_result = "A" * 600
    async def fake_call_tool(tool_key, arguments):
        return long_result
    
    tool_manager.call_mcp_tool = fake_call_tool
    
    callback_messages = []
    def streaming_callback(msg):
        callback_messages.append(msg)
    
    result = await tool_manager._run_agent_with_tools_simple(  # pylint: disable=protected-access
        "test_tool(arg='value')", streaming_callback
    )
    
    # 결과는 원본이어야 함
    assert result["response"] == long_result
    
    # streaming callback에서는 요약된 버전이어야 함
    callback_text = "".join(callback_messages)
    assert "... (결과 생략)" in callback_text
    assert len([msg for msg in callback_messages if "📋 도구 실행 결과:" in msg][0]) < 600 


@pytest.mark.asyncio
async def test_tool_key_mapping_with_prefix(tmp_path):
    """도구 키 매핑 로직 테스트 - prefix가 있는 경우와 없는 경우"""
    cm = ConfigManager(config_file=str(tmp_path / "cfg"))
    mcp_manager = DummyMCPManager({"calc": DummyServerConfig()})
    tool_manager = MCPToolManager(mcp_manager, cm)
    
    # 캐시에 서버명_도구명 형태로 도구 추가
    cache: ToolCache = tool_manager._cache
    cache.add(
        "calc_add",  # 캐시 키
        "calc",      # 서버 이름
        "add",       # 실제 도구 이름
        {"description": "Add two numbers", "inputSchema": {}}
    )
    
    # ToolExecutor 테스트를 위한 모의 구현
    class MockedToolExecutor:
        def __init__(self, cache):
            self._cache = cache
            self.called_with = None
            
        async def __call__(self, tool_key, arguments):
            self.called_with = (tool_key, arguments)
            # 실제 매핑 로직 테스트
            if tool_key not in self._cache:
                # prefix가 있는 경우를 대비해 다른 형태로도 찾아보기
                found_key = None
                for cached_key in self._cache.keys():
                    # 서버명_도구명 형태에서 도구명 부분만 비교
                    if cached_key.endswith(f"_{tool_key}") or cached_key == tool_key:
                        found_key = cached_key
                        break
                    # 도구명이 서버명 없이 직접 일치하는 경우
                    cached_meta = self._cache.get(cached_key)
                    if cached_meta and cached_meta.get("tool_name") == tool_key:
                        found_key = cached_key
                        break
                
                if found_key:
                    tool_key = found_key
                else:
                    return f"오류: 도구 '{tool_key}'을 찾을 수 없습니다."
            
            return f"성공: {tool_key} 호출됨"
    
    # Executor 교체
    mock_executor = MockedToolExecutor(cache)
    tool_manager._executor = mock_executor
    
    # 테스트 케이스 1: 정확한 키로 호출
    result1 = await tool_manager.call_mcp_tool("calc_add", {"a": 1, "b": 2})
    assert "성공: calc_add 호출됨" in result1
    assert mock_executor.called_with == ("calc_add", {"a": 1, "b": 2})
    
    # 테스트 케이스 2: prefix 없는 도구명으로 호출 (매핑되어야 함)
    result2 = await tool_manager.call_mcp_tool("add", {"a": 3, "b": 4})
    assert "성공: calc_add 호출됨" in result2
    assert mock_executor.called_with == ("calc_add", {"a": 3, "b": 4})
    
    # 테스트 케이스 3: 존재하지 않는 도구 호출
    result3 = await tool_manager.call_mcp_tool("nonexistent", {"x": 1})
    assert "오류: 도구 'nonexistent'을 찾을 수 없습니다" in result3 