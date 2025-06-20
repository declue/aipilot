from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional, cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from application.config.config_manager import ConfigManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("llm") or logging.getLogger("llm_agent")
# 디버깅을 위한 로그 레벨 INFO 설정
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _is_reasoning_model(model: str) -> bool:
    """Heuristic check for models that emit visible chain‑of‑thought."""
    reasoning_names = (
        "o1",
        "claude-3-5",
        "deepseek-r1",
        "qwen-qvq",
        "qwen3:32b-q8_0",
        "gemini-2.5-pro-preview-06-05",
        "deepseek-chat",
        "llama-3.3-70b-reasoning",
    )
    return any(name in model.lower() for name in reasoning_names)


def _strip_reasoning(raw: str) -> str:
    """Drop `<think>` … `</think>` or similar sections, keep the answer only."""
    if "</think>" in raw:
        return raw.split("</think>")[-1].strip()
    for pat in (
        r"<thinking>[\s\S]*?</thinking>",
        r"<thought>[\s\S]*?</thought>",
        r"추론 과정:[\s\S]*?(?=답변:|$)",
    ):
        raw = re.sub(pat, "", raw, flags=re.I)
    return raw.strip()


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------


class LLMAgent:
    """MCPToolManager를 사용하는 LLM 에이전트"""

    def __init__(self, config_manager: ConfigManager, mcp_tool_manager: MCPToolManager):
        self.config_manager = config_manager
        self.history: List[ChatCompletionMessageParam] = []
        self._client: Optional[AsyncOpenAI] = None
        self.mcp_tool_manager = mcp_tool_manager

    def reinitialize_client(self) -> None:
        """설정 변경 시 클라이언트를 재초기화합니다."""
        self._client = None

        # 새로운 설정 확인을 위한 로그
        try:
            cfg = self.config_manager.get_llm_config()
            logger.info(
                f"LLM Agent 클라이언트 재초기화: 모델={cfg.get('model')}, base_url={cfg.get('base_url')}"
            )
        except Exception as e:
            logger.error(f"LLM Agent 설정 로드 실패: {e}")

        logger.info("LLM Agent 클라이언트가 재초기화되었습니다.")

    @property
    def client(self) -> AsyncOpenAI:
        """OpenAI 클라이언트를 반환합니다."""
        if not self._client:
            cfg = self.config_manager.get_llm_config()
            self._client = AsyncOpenAI(
                api_key=cfg["api_key"], base_url=cfg["base_url"], timeout=300.0
            )
        return self._client

    @staticmethod
    async def test_connection(
        api_key: str, base_url: str, model: str
    ) -> Dict[str, Any]:
        """LLM 서버 연결 테스트"""
        try:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=300.0)
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
            )

            return {
                "success": True,
                "message": "연결 성공",
                "response": response.choices[0].message.content or "",
                "model": model,
            }

        except Exception as exception:
            return {
                "success": False,
                "message": f"연결 실패: {str(exception)}",
                "error": str(exception),
            }

    @staticmethod
    async def get_available_models(api_key: str, base_url: str) -> Dict[str, Any]:
        """사용 가능한 모델 목록 가져오기"""
        try:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=300.0)
            models_response = await client.models.list()

            models = []
            async for model in models_response:
                models.append(model.id)
            models.sort()

            return {
                "success": True,
                "models": models,
                "message": f"{len(models)}개 모델을 찾았습니다",
            }

        except Exception as exception:
            return {
                "success": False,
                "models": [],
                "message": f"모델 목록 가져오기 실패: {str(exception)}",
                "error": str(exception),
            }

    def add_user_message(self, text: str) -> None:
        self.history.append({"role": "user", "content": text})

    def add_assistant_message(self, text: str) -> None:
        self.history.append({"role": "assistant", "content": text})

    def clear_conversation(self) -> None:
        self.history.clear()

    async def generate_response(self, user_message: str) -> str:
        result = await self._respond(user_message)
        return cast(str, result["response"])

    async def generate_response_streaming(
        self, user_message: str, streaming_callback: Optional[Callable[[str], None]]
    ) -> Dict[str, Any]:
        return await self._respond(user_message, streaming_callback)

    async def _respond(
        self, user_msg: str, streaming_cb: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """사용자 메시지에 대한 응답을 생성합니다."""
        logger.info(f"사용자 메시지: {user_msg}")
        self.add_user_message(user_msg)
        response_data = {}

        # ------------------------------------------------------------------
        # 1) LLM Workflow 모드 우선 처리
        # ------------------------------------------------------------------
        llm_mode: str = (
            self.config_manager.get_config_value("LLM", "mode", "basic") or "basic"
        ).lower()

        if llm_mode == "workflow":
            # 워크플로우 이름 가져오기 (없으면 basic_chat)
            workflow_name: str = (
                self.config_manager.get_config_value("LLM", "workflow", "basic_chat")
                or "basic_chat"
            )

            try:
                from application.llm.workflow import (
                    get_workflow,  # pylint: disable=import-outside-toplevel
                )

                workflow_cls = get_workflow(workflow_name)
                if workflow_cls is None:
                    logger.warning(
                        "워크플로우 '%s' 을 찾을 수 없어 기본 워크플로우로 대체합니다.",
                        workflow_name,
                    )
                    workflow_cls = get_workflow("basic_chat")

                assert (
                    workflow_cls is not None
                ), "기본 워크플로우가 레지스트리에 등록되지 않았습니다"

                workflow = workflow_cls()
                response_text: str = await workflow.run(self, user_msg, streaming_cb)
                self.add_assistant_message(response_text)
                return {
                    "response": response_text,
                    "reasoning": "",  # 추후 워크플로우 세부 reasoning 추가 가능
                    "used_tools": [],
                    "workflow": workflow_name,
                }

            except Exception as exc:  # pylint: disable=broad-except
                logger.error("워크플로우 실행 중 예외 발생: %s", exc)
                fallback_response = "죄송합니다. 워크플로우 처리 중 문제가 발생했습니다."
                self.add_assistant_message(fallback_response)
                return {
                    "response": fallback_response,
                    "reasoning": str(exc),
                    "used_tools": [],
                }

        # MCPToolManager를 사용하는 경우
        if self.mcp_tool_manager:
            try:
                # 도구가 필요한지 확인
                if await self._should_use_tools(user_msg):
                    # MCP 도구를 사용하여 응답 생성
                    openai_tools = await self.mcp_tool_manager.get_openai_tools()

                    if openai_tools:
                        tool_result = await self._generate_with_tools(
                            user_msg, openai_tools, streaming_cb
                        )
                        response_data = {
                            "response": tool_result.get("response", ""),
                            "reasoning": tool_result.get("reasoning", ""),
                            "used_tools": [],  # 추후 확장
                        }
                    else:
                        response_text = await self._generate_basic_response(
                            user_msg, streaming_cb
                        )
                        response_data = {
                            "response": response_text,
                            "reasoning": "",
                            "used_tools": [],
                        }
                else:
                    response_text = await self._generate_basic_response(
                        user_msg, streaming_cb
                    )
                    response_data = {
                        "response": response_text,
                        "reasoning": "",
                        "used_tools": [],
                    }

                self.add_assistant_message(response_data["response"])
                return response_data

            except Exception as exc:
                logger.error(f"MCPToolManager 사용 중 예외 발생: {exc}")
                response = "죄송합니다. 도구 처리 중 문제가 발생했습니다."
                self.add_assistant_message(response)
                return {"response": response, "reasoning": "", "used_tools": []}

        # 기본 응답 생성
        try:
            response_text = await self._generate_basic_response(user_msg, streaming_cb)
            self.add_assistant_message(response_text)
            return {
                "response": response_text,
                "reasoning": "",
                "used_tools": [],
            }
        except Exception as exc:
            logger.error(f"응답 생성 중 예외 발생: {exc}")
            response = "죄송합니다. 응답 생성 중 문제가 발생했습니다."
            self.add_assistant_message(response)
            return {"response": response, "reasoning": "", "used_tools": []}

    async def _should_use_tools(self, msg: str) -> bool:
        """도구 사용 여부를 결정합니다."""
        if not self.mcp_tool_manager:
            return False

        # MCP 도구 사용을 나타내는 키워드들
        tool_keywords = [
            "github",
            "깃허브",
            "MCP",
            "도구",
            "tool",
            "검색",
            "시간",
            "실행",
            "execute",
        ]
        msg_lower = msg.lower()

        # 특수 패턴 확인 (예: owner/repo, @서버명 등)

        special_patterns = [
            r"@\w+",  # @로 시작하는 패턴 (예: @github)
            r"\b\w+/\w+\b",  # owner/repo 형식
            r"\b\w+\.\w+\b",  # domain.extension 형식
        ]

        has_special_pattern = any(
            re.search(pattern, msg) for pattern in special_patterns
        )
        has_keyword = any(keyword in msg_lower for keyword in tool_keywords)

        return has_special_pattern or has_keyword

    async def _generate_with_tools(
        self, user_msg: str, tools: List[Dict], streaming_cb: Optional[Callable[[str], None]]
    ) -> Dict[str, Any]:
        """OpenAI agents SDK를 사용하여 복합적인 도구 작업을 수행합니다."""
        try:
            if streaming_cb:
                # 사용 가능한 도구 정보 표시
                tool_count = len(tools)
                streaming_cb(f"🔧 {tool_count}개의 MCP 도구가 준비되었습니다.\n\n")

                streaming_cb("🚀 복합적인 도구 작업을 시작합니다...\n\n")

            # MCPToolManager를 통해 agents SDK 기반 응답 생성
            result = await self.mcp_tool_manager.run_agent_with_tools(
                user_msg, streaming_cb
            )

            return result

        except Exception as exc:
            logger.error(f"agents SDK 기반 도구 사용 실패: {exc}")
            error_msg = "죄송합니다. 도구를 사용한 응답 생성에 실패했습니다."
            if streaming_cb:
                streaming_cb(f"\n❌ **오류 발생:** {error_msg}\n")
                streaming_cb(f"**상세 오류:** {str(exc)}\n")
            return {"response": error_msg, "reasoning": str(exc)}

    async def _generate_basic_response(
        self, _user_msg: str, streaming_cb: Optional[Callable[[str], None]]
    ) -> str:
        """기본 응답을 생성합니다."""
        cfg = self.config_manager.get_llm_config()

        try:
            if streaming_cb is None:
                response = await self.client.chat.completions.create(
                    model=cfg["model"],
                    messages=self.history,
                    max_tokens=cfg["max_tokens"],
                    temperature=cfg["temperature"],
                )

                content = response.choices[0].message.content or ""

                show_cot_flag = str(cfg.get("show_cot", "false")).lower() == "true"
                if not show_cot_flag and _is_reasoning_model(cfg["model"]):
                    content = _strip_reasoning(content)

                return content

            # 스트리밍 응답
            acc: List[str] = []
            stream = await self.client.chat.completions.create(
                model=cfg["model"],
                messages=self.history,
                stream=True,
                max_tokens=cfg["max_tokens"],
                temperature=cfg["temperature"],
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        streaming_cb(delta.content)
                        acc.append(delta.content)

            content_joined = "".join(acc)

            show_cot_flag = str(cfg.get("show_cot", "false")).lower() == "true"
            if not show_cot_flag and _is_reasoning_model(cfg["model"]):
                # reasoning 을 숨겨야 할 때는 최종 합쳐진 콘텐츠에서 제거 후 UI 로 보냄
                return _strip_reasoning(content_joined)

            return content_joined

        except Exception as exc:
            logger.error(f"기본 응답 생성 실패: {exc}")
            raise
