from __future__ import annotations

import asyncio
import json
import logging
import re
from functools import partial
from typing import Any, Callable, Dict, List, cast

from agents import Agent, ModelSettings, Runner, set_default_openai_client
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI  # type: ignore
from openai.types.chat import ChatCompletionMessageParam  # type: ignore

from application.config.config_manager import ConfigManager
from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.tool.cache import ToolCache
from application.llm.mcp.tool.converter import ToolConverter
from application.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class ToolExecutor:  # pylint: disable=too-few-public-methods
    """단일 MCP 도구 호출을 실행한다. (Strategy 패턴 적용 가능 지점)"""

    def __init__(
        self, mcp_manager: MCPManager, config_manager: ConfigManager, cache: ToolCache
    ) -> None:
        self._mcp_manager = mcp_manager
        self._config_manager = config_manager
        self._cache = cache

    async def __call__(self, tool_key: str, arguments: Dict[str, Any]) -> str:  # noqa: D401
        """`await executor(tool_key, args)` 형태로 사용하기 위한 호출 가능 객체."""
        # 1) 캐시 확인
        if tool_key not in self._cache:
            return f"오류: 도구 '{tool_key}'을 찾을 수 없습니다."

        tool_meta = self._cache.get(tool_key)
        server_name = tool_meta["server_name"]
        actual_tool_name = tool_meta["tool_name"]        # 2) 서버 설정 조회
        server_config = self._mcp_manager.get_enabled_servers().get(server_name)
        if not server_config:
            return f"오류: 서버 '{server_name}' 설정을 찾을 수 없습니다."

        # 4) OpenAI 클라이언트 재설정 (ConfigManager로부터)
        cfg = self._config_manager.get_llm_config()
        try:
            client = AsyncOpenAI(
                api_key=cfg.get("api_key"), 
                base_url=cfg.get("base_url"),
                timeout=60.0  # 타임아웃 설정 추가
            )
            set_default_openai_client(client)
        except Exception as exc:  # pragma: no cover
            logger.error("OpenAI 클라이언트 설정 실패: %s", exc)
            return f"오류: OpenAI 클라이언트 설정 실패 - {exc}"        # 5) MCPServerStdio 를 이용해 실제 도구 호출 실행
        try:
            async with MCPServerStdio(
                cache_tools_list=True,
                params={
                    "command": server_config.command,
                    "args": server_config.args,
                    "env": server_config.env or {},
                },
            ) as mcp_server:
                agent = Agent(
                    name=f"{server_name}_agent",
                    model=cfg.get("model", "gpt-3.5-turbo"),
                    instructions="도구를 사용하여 질문에 답하세요.",
                    mcp_servers=[mcp_server],
                    model_settings=ModelSettings(tool_choice="required"),
                )

                # arguments 딕셔너리를 프롬프트 문자열로 단순 변환 (향후 개선 가능)
                args_str = ", ".join(f"{k}={v}" for k, v in arguments.items())
                prompt = f"Use the {actual_tool_name} tool with these parameters: {args_str}"

                result = await Runner.run(starting_agent=agent, input=prompt, max_turns=10)
                return getattr(result, "final_output", str(result))
                
        except Exception as exc:
            logger.error("MCP 서버 연결 또는 도구 실행 실패: %s", exc)
            return f"오류: MCP 도구 실행 실패 - {exc}"


class MCPToolManager:  # pylint: disable=too-many-instance-attributes
    """고수준 퍼사드(Facade) 역할을 하는 MCPToolManager.

    실제 로직은 `ToolCache`, `ToolConverter`, `ToolExecutor` 에 위임한다.
    """

    def __init__(self, mcp_manager: MCPManager, config_manager: ConfigManager) -> None:
        self._mcp_manager = mcp_manager
        self._config_manager = config_manager
        self._cache = ToolCache()
        self._converter = ToolConverter()
        self._executor = ToolExecutor(mcp_manager, config_manager, self._cache)

        # 비동기 환경이 아닌 곳에서 생성될 수도 있으므로, 이벤트 루프가 있으면 즉시 갱신.
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():  # pragma: no cover (일반 테스트 환경에서는 False)
                loop.create_task(self.refresh_tools())
        except RuntimeError:
            # 이벤트 루프가 없으면 무시
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def get_openai_tools(self) -> List[Dict[str, Any]]:
        """OpenAI function call 포맷으로 변환된 MCP 도구 목록을 반환합니다."""
        if not self._cache:  # type: ignore[truthy-bool]
            await self.refresh_tools()
        return [tool for tool in self._build_openai_tools_response()]

    async def call_mcp_tool(self, tool_key: str, arguments: Dict[str, Any]) -> str:
        """지정된 MCP 도구를 호출합니다."""
        return await self._executor(tool_key, arguments)

    def get_tool_descriptions(self) -> str:
        """현재 캐시에 저장된 도구 설명 문자열을 반환합니다."""
        if not self._cache:
            return "현재 사용 가능한 MCP 도구가 없습니다."

        lines: List[str] = ["=== 사용 가능한 MCP 도구들 ===\n"]
        for tool_key, meta in self._cache.items():
            lines.append(
                f"- **{tool_key}** ({meta['server_name']}): {meta['tool_info']['description']}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 임시 ReAct-style 실행 (간소화)
    # ------------------------------------------------------------------

    async def run_agent_with_tools(self, user_msg: str, streaming_cb: Callable[[str], None] | None = None) -> Dict[str, Any]:  # noqa: D401
        """OpenAI function-call 기반 ReAct(Reason-Act-Observe) 루프.

        1. 사용자 질문 → LLM 호출
        2. LLM 이 tool_call 을 반환하면 해당 MCP 도구 실행(Act)
        3. 실행 결과를 Observation 으로 LLM 에 전달 후 반복
        4. LLM 이 finish_reason == "stop" 으로 답변을 제출하면 종료

        실패하거나 OpenAI 사용이 불가능한 환경에서는 간소화 버전으로 폴백합니다.
        """
        tools = await self.get_openai_tools()
        if not tools:
            logger.info("사용 가능한 MCP 도구가 없습니다 – 간소화 모드로 전환")
            return await self._run_agent_with_tools_simple(user_msg, streaming_cb)

        cfg = self._config_manager.get_llm_config()
        
        # API 키와 base_url 검증
        api_key = cfg.get("api_key")
        base_url = cfg.get("base_url")
        
        if not api_key:
            logger.error("OpenAI API 키가 설정되지 않았습니다")
            return await self._run_agent_with_tools_simple(user_msg, streaming_cb)
            
        # 초기 진단 로깅
        logger.info("=== ReAct 루프 시작 ===")
        logger.info("사용자 메시지: %s", user_msg[:100] + "..." if len(user_msg) > 100 else user_msg)
        logger.info("사용 가능한 도구: %d개", len(tools))
        logger.info("모델: %s", cfg.get("model", "unknown"))

        try:
            client = AsyncOpenAI(
                api_key=api_key, 
                base_url=base_url, 
                timeout=300.0
            )
            logger.info("OpenAI 클라이언트 생성 완료")
        except Exception as exc:
            logger.error("OpenAI 클라이언트 생성 실패: %s", exc)
            return await self._run_agent_with_tools_simple(user_msg, streaming_cb)

        messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": (
                    "당신은 사용자 질문에 답하기 위해 MCP 도구를 능숙하게 사용하는 AI 비서입니다. "
                    "필요한 경우 함수를 호출하여 문제를 해결하고, 충분한 관찰 결과를 얻은 후 최종 답변을 제공합니다."
                ),
            },
            {"role": "user", "content": user_msg},
        ]

        used_tools: List[str] = []
        reasoning_parts: List[str] = []
        show_cot_flag_global = str(cfg.get("show_cot", "false")).lower() == "true"

        max_turns_cfg = int(self._config_manager.get_llm_config().get("react_max_turns", 5))

        for turn in range(max_turns_cfg):
            if streaming_cb:
                streaming_cb(f"\n🤔 LLM 응답 생성 (turn {turn + 1})...\n")

            _create_any = cast(Any, client.chat.completions.create)

            completion_factory = partial(
                _create_any,
                model=cfg.get("model"),
                messages=messages,
                tools=cast(Any, tools),  # typing stub 미지원
                tool_choice="auto",  # type: ignore[call-arg]
                temperature=cfg.get("temperature", 0.7),
                max_tokens=cfg.get("max_tokens", 1024),
            )

            try:
                response = await _retry_async(
                    completion_factory,  # type: ignore[arg-type]
                    attempts=int(cfg.get("llm_retry_attempts", 3)),
                    backoff=float(cfg.get("retry_backoff_sec", 1)),
                )
            except Exception as exc:
                logger.error("OpenAI API 호출 실패: %s", exc)
                return {
                    "response": "죄송합니다. AI 서비스에 연결할 수 없습니다.",
                    "reasoning": f"OpenAI API 오류: {exc}",
                    "used_tools": used_tools,
                }

            choice = response.choices[0]
            assistant_msg = choice.message

            if choice.finish_reason == "stop":
                # 최종 답변 확보
                final_answer = assistant_msg.content or ""

                if assistant_msg.content:
                    reasoning_parts.append(assistant_msg.content)

                if not show_cot_flag_global:
                    try:
                        from application.llm.llm_agent import (
                            _is_reasoning_model as _irm,  # pylint: disable=import-outside-toplevel; type: ignore
                        )
                        from application.llm.llm_agent import _strip_reasoning as _sr

                        if _irm(cfg.get("model", "")):
                            final_answer = _sr(final_answer)
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.debug("reasoning 처리 실패: %s", exc)

                reasoning_text = "\n".join(reasoning_parts) if show_cot_flag_global else ""

                return {
                    "response": final_answer,
                    "reasoning": reasoning_text,
                    "used_tools": used_tools,
                }

            if choice.finish_reason != "tool_calls":
                # 예상치 못한 종료 – 그대로 반환
                return {
                    "response": assistant_msg.content or "",
                    "reasoning": ("\n".join(reasoning_parts) if show_cot_flag_global else ""),
                    "used_tools": used_tools,
                }

            # tool_calls 처리
            tool_calls = assistant_msg.tool_calls or []
            if streaming_cb:
                streaming_cb(f"🔨 {len(tool_calls)}개 도구 호출 감지\n")

            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    args_dict = json.loads(tc.function.arguments)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("도구 인수 파싱 실패: %s", exc)
                    args_dict = {}

                if streaming_cb:
                    streaming_cb(f"🛠️ '{tool_name}' 실행 중...\n")

                try:
                    tool_result = await _retry_async(
                        partial(self.call_mcp_tool, tool_name, args_dict),
                        attempts=int(cfg.get("llm_retry_attempts", 3)),
                        backoff=float(cfg.get("retry_backoff_sec", 1)),
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("도구 실행 중 예외: %s", exc)
                    tool_result = f"도구 실행 실패: {exc}"

                used_tools.append(tool_name)

                # assistant tool_call 메시지를 기록 (id 유지)
                messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tc],  # type: ignore[arg-type]
                    }
                )

                # observation 메시지 추가
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result,
                    }
                )

                if streaming_cb:
                    streaming_cb(f"✅ '{tool_name}' 완료\n")

        # 반복 초과
        logger.warning("ReAct 루프 최대 반복 초과")
        return {
            "response": "죄송합니다. 요청을 완료하지 못했습니다.",
            "reasoning": "Max iterations exceeded",
            "used_tools": used_tools,
        }

    # ------------------------------------------------------------------
    # 간단한 패턴 기반 폴백 구현 (이전 버전)
    # ------------------------------------------------------------------

    async def _run_agent_with_tools_simple(self, user_msg: str, streaming_cb: Callable[[str], None] | None = None) -> Dict[str, Any]:  # noqa: D401
        """간단한 '<tool>(args)' 패턴 파싱 버전 (네트워크 호출 없이도 동작)."""

        tool_pattern = re.compile(r"(?P<tool>[\w_]+)\s*\((?P<args>[^)]*)\)")
        match = tool_pattern.search(user_msg)

        if not match:
            return {
                "response": "도구 호출 패턴을 찾지 못했습니다.",
                "reasoning": "No tool pattern detected",
                "used_tools": [],
            }

        tool_key = match.group("tool")
        args_str = match.group("args")

        args_dict: Dict[str, Any] = {}
        if args_str.strip():
            for part in args_str.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    args_dict[k.strip()] = v.strip().strip("'\"")

        if streaming_cb:
            streaming_cb(f"🛠️ MCP 도구 '{tool_key}' 호출 중...\n")

        try:
            result_text = await self.call_mcp_tool(tool_key, args_dict)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("도구 실행 실패: %s", exc)
            return {
                "response": "도구 실행 중 오류가 발생했습니다.",
                "reasoning": str(exc),
                "used_tools": [tool_key],
            }

        return {
            "response": result_text,
            "reasoning": "MCP tool executed (simple mode)",
            "used_tools": [tool_key],
        }

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------

    async def refresh_tools(self) -> None:
        """활성화된 MCP 서버로부터 도구 메타데이터를 새로 가져와 캐시를 갱신합니다."""
        self._cache.clear()
        enabled_servers = self._mcp_manager.get_enabled_servers()
        if not enabled_servers:
            logger.info("활성화된 MCP 서버가 없습니다.")
            return

        async def _process_server(server_name: str, _server_config: Any) -> None:
            try:
                status = await self._mcp_manager.test_server_connection(server_name)
                if not getattr(status, "connected", False):
                    logger.warning("%s 서버 연결 실패", server_name)
                    return

                for tool in getattr(status, "tools", []):
                    key = f"{server_name}_{tool['name']}"
                    self._cache.add(key, server_name, tool["name"], tool)
            except Exception as exc:
                logger.error("%s 서버 처리 중 예외 발생: %s", server_name, exc)

        # 병렬로 각 서버 상태 확인 (예외 처리 포함)
        try:
            await asyncio.gather(*[_process_server(name, cfg) for name, cfg in enabled_servers.items()], return_exceptions=True)
        except Exception as exc:
            logger.error("서버 처리 중 예상치 못한 오류: %s", exc)

    # ------------------------------------------------------------------
    # 연결 상태 확인 및 진단
    # ------------------------------------------------------------------
    
    async def check_connection_status(self) -> Dict[str, Any]:
        """현재 연결 상태를 확인하고 진단 정보를 반환합니다."""
        status: Dict[str, Any] = {
            "openai_client": False,
            "mcp_servers": {},
            "config_valid": False,
            "errors": []
        }
        
        # 1. 설정 확인
        try:
            cfg = self._config_manager.get_llm_config()
            api_key = cfg.get("api_key")
            if api_key:
                status["config_valid"] = True
            else:
                status["errors"].append("OpenAI API 키가 설정되지 않았습니다")
        except Exception as exc:
            status["errors"].append(f"설정 로드 실패: {exc}")
        
        # 2. OpenAI 클라이언트 테스트
        if status["config_valid"]:
            try:
                cfg = self._config_manager.get_llm_config()
                client = AsyncOpenAI(
                    api_key=cfg.get("api_key"), 
                    base_url=cfg.get("base_url"),
                    timeout=10.0
                )
                # 간단한 모델 목록 요청으로 연결 테스트
                await client.models.list()
                status["openai_client"] = True
            except Exception as exc:
                status["errors"].append(f"OpenAI 연결 실패: {exc}")
        
        # 3. MCP 서버 상태 확인
        enabled_servers = self._mcp_manager.get_enabled_servers()
        for server_name, server_config in enabled_servers.items():
            try:
                server_status = await self._mcp_manager.test_server_connection(server_name)
                status["mcp_servers"][server_name] = {
                    "connected": getattr(server_status, "connected", False),
                    "tools_count": len(getattr(server_status, "tools", [])),
                    "command": server_config.command
                }
            except Exception as exc:
                status["mcp_servers"][server_name] = {
                    "connected": False,
                    "error": str(exc),
                    "command": server_config.command
                }
        
        return status

    def validate_configuration(self) -> List[str]:
        """설정의 유효성을 검증하고 문제점을 반환합니다."""
        issues = []
        
        try:
            cfg = self._config_manager.get_llm_config()
            
            # API 키 확인
            if not cfg.get("api_key"):
                issues.append("OpenAI API 키가 설정되지 않았습니다")
            
            # 모델 확인
            if not cfg.get("model"):
                issues.append("LLM 모델이 설정되지 않았습니다")
              # base_url 확인 (선택사항이지만 설정된 경우 유효성 확인)
            base_url = cfg.get("base_url")
            if base_url and not (
                base_url.startswith("http://") or 
                base_url.startswith("https://") or
                base_url.startswith("localhost") or
                "localhost" in base_url
            ):
                issues.append("base_url이 올바른 형식이 아닙니다")
                
        except Exception as exc:
            issues.append(f"설정 로드 중 오류: {exc}")
        
        # MCP 서버 설정 확인
        enabled_servers = self._mcp_manager.get_enabled_servers()
        if not enabled_servers:
            issues.append("활성화된 MCP 서버가 없습니다")
        
        return issues

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------
    def _build_openai_tools_response(self) -> List[Dict[str, Any]]:
        """ToolCache 내용을 OpenAI 함수 포맷 리스트로 변환하는 도우미."""
        response: List[Dict[str, Any]] = []
        for key, meta in self._cache.items():
            tool_info = meta["tool_info"]
            response.append(
                {
                    "type": "function",
                    "function": {
                        "name": key,
                        "description": self._converter.enhance_description(
                            meta["server_name"], meta["tool_name"], tool_info["description"]
                        ),
                        "parameters": self._converter.convert_schema(tool_info.get("inputSchema", {})),
                    },
                }
            )
        return response

    async def diagnose_llm_issue(self, user_msg: str = "테스트") -> Dict[str, Any]:
        """LLM 연결 및 응답 문제를 진단합니다."""
        diagnosis: Dict[str, Any] = {
            "timestamp": "2025-06-21",
            "config_status": "unknown",
            "connection_test": "unknown", 
            "simple_test": "unknown",
            "tools_available": 0,
            "recommendations": []
        }
        
        # 1. 설정 검증
        config_issues = self.validate_configuration()
        if config_issues:
            diagnosis["config_status"] = "failed"
            diagnosis["recommendations"].extend([f"설정 문제: {issue}" for issue in config_issues])
        else:
            diagnosis["config_status"] = "ok"
        
        # 2. 도구 가용성 확인
        try:
            tools = await self.get_openai_tools()
            diagnosis["tools_available"] = len(tools)
            if not tools:
                diagnosis["recommendations"].append("사용 가능한 MCP 도구가 없습니다. MCP 서버 상태를 확인하세요.")
        except Exception as exc:
            diagnosis["recommendations"].append(f"도구 로드 실패: {exc}")
        
        # 3. 연결 상태 테스트
        try:
            connection_status = await self.check_connection_status()
            if connection_status["openai_client"]:
                diagnosis["connection_test"] = "ok"
            else:
                diagnosis["connection_test"] = "failed"
                diagnosis["recommendations"].extend(connection_status["errors"])
        except Exception as exc:
            diagnosis["connection_test"] = "error"
            diagnosis["recommendations"].append(f"연결 테스트 실패: {exc}")
        
        # 4. 간단한 응답 테스트
        try:
            simple_result = await self._run_agent_with_tools_simple(user_msg)
            diagnosis["simple_test"] = "ok" if simple_result["response"] else "failed"
        except Exception as exc:
            diagnosis["simple_test"] = "error"
            diagnosis["recommendations"].append(f"간단한 테스트 실패: {exc}")
        
        # 5. 구체적인 권장사항 추가
        if diagnosis["config_status"] == "ok" and diagnosis["connection_test"] == "failed":
            diagnosis["recommendations"].append("API 키나 base_url 설정을 확인하세요.")
        
        if diagnosis["tools_available"] == 0:
            diagnosis["recommendations"].append("MCP 서버를 시작하고 도구를 새로고침하세요.")
        
        return diagnosis


# ------------------------------------------------------------------
# 내부 헬퍼: 비동기 재시도
# ------------------------------------------------------------------

def _retry_async(coro_factory: Callable[[], Any], *, attempts: int = 3, backoff: float = 1.0) -> Any:
    """주어진 awaitable factory 에 대해 재시도(backoff) 수행."""

    async def _inner() -> Any:
        delay = backoff
        for attempt in range(1, attempts + 1):
            try:
                return await coro_factory()
            except Exception as exc:  # pylint: disable=broad-except
                if attempt == attempts:
                    raise
                logger.warning("재시도 %s/%s: %s", attempt, attempts, exc)
                await asyncio.sleep(delay)
                delay *= 2

    return _inner()