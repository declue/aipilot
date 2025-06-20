from __future__ import annotations

import asyncio
import json
import logging
import re
from functools import partial
from typing import Any, Dict, List, cast

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
        actual_tool_name = tool_meta["tool_name"]

        # 2) 서버 설정 조회
        server_config = self._mcp_manager.get_enabled_servers().get(server_name)
        if not server_config:
            return f"오류: 서버 '{server_name}' 설정을 찾을 수 없습니다."

        # 4) OpenAI 클라이언트 재설정 (ConfigManager로부터)
        cfg = self._config_manager.get_llm_config()
        try:
            client = AsyncOpenAI(api_key=cfg.get("api_key"), base_url=cfg.get("base_url"))
            set_default_openai_client(client)
        except Exception as exc:  # pragma: no cover
            logger.warning("OpenAI 클라이언트 설정 실패: %s", exc)

        # 5) MCPServerStdio 를 이용해 실제 도구 호출 실행
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

    async def run_agent_with_tools(self, user_msg: str, streaming_cb=None) -> Dict[str, Any]:  # noqa: D401
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
        client = AsyncOpenAI(api_key=cfg.get("api_key"), base_url=cfg.get("base_url"), timeout=300.0)

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

            response = await _retry_async(
                completion_factory,  # type: ignore[arg-type]
                attempts=int(cfg.get("llm_retry_attempts", 3)),
                backoff=float(cfg.get("retry_backoff_sec", 1)),
            )

            choice = response.choices[0]
            assistant_msg = choice.message

            if choice.finish_reason == "stop":
                # 최종 답변 확보
                final_answer = assistant_msg.content or ""

                if assistant_msg.content:
                    reasoning_parts.append(assistant_msg.content)

                if not show_cot_flag_global:
                    try:
                        from application.llm.llm_agent import \
                            _is_reasoning_model as \
                            _irm  # pylint: disable=import-outside-toplevel; type: ignore
                        from application.llm.llm_agent import \
                            _strip_reasoning as _sr

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

    async def _run_agent_with_tools_simple(self, user_msg: str, streaming_cb=None) -> Dict[str, Any]:  # noqa: D401
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

        async def _process_server(server_name: str, _server_config):  # type: ignore[valid-type]
            status = await self._mcp_manager.test_server_connection(server_name)
            if not getattr(status, "connected", False):
                logger.warning("%s 서버 연결 실패", server_name)
                return

            for tool in getattr(status, "tools", []):
                key = f"{server_name}_{tool['name']}"
                self._cache.add(key, server_name, tool["name"], tool)

        # 병렬로 각 서버 상태 확인
        await asyncio.gather(*[_process_server(name, cfg) for name, cfg in enabled_servers.items()])

    # -------------------------------------------------
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

# ------------------------------------------------------------------
# 내부 헬퍼: 비동기 재시도
# ------------------------------------------------------------------

def _retry_async(coro_factory, *, attempts: int = 3, backoff: float = 1.0):  # noqa: D401
    """주어진 awaitable factory 에 대해 재시도(backoff) 수행."""

    async def _inner():
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