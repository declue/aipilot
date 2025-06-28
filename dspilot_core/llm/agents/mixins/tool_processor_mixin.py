#!/usr/bin/env python3
"""ToolProcessorMixin: 도구 결과 포맷팅 및 LLM 분석."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from dspilot_core.llm.models.conversation_message import ConversationMessage
from dspilot_core.llm.processors.base_processor import ToolResultProcessorRegistry
from dspilot_core.llm.processors.search_processor import SearchToolResultProcessor
from dspilot_core.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class ToolProcessorMixin:
    """도구 결과 처리 및 LLM 분석 기능"""

    _processor_registry: Optional[ToolResultProcessorRegistry] = None

    # BaseAgent 쪽에서 llm_service 를 주입
    llm_service: Any

    # ------------------------------------------------------------------
    # Processor Registry ------------------------------------------------
    # ------------------------------------------------------------------
    def _get_processor_registry(self) -> ToolResultProcessorRegistry:  # noqa: D401, pylint: disable=protected-access
        if self._processor_registry is None:
            self._processor_registry = ToolResultProcessorRegistry()
            self._processor_registry.register(SearchToolResultProcessor())
            logger.debug("도구 결과 프로세서 레지스트리 초기화 완료")
        return self._processor_registry

    # ------------------------------------------------------------------
    # 결과 포맷팅 --------------------------------------------------------
    # ------------------------------------------------------------------
    def _format_tool_results(self, used_tools: List[str], tool_results: Dict[str, str]) -> str:  # noqa: D401, pylint: disable=protected-access
        try:
            return self._get_processor_registry().process_tool_results(used_tools, tool_results)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("도구 결과 포맷팅 오류: %s", exc)
            return "도구 결과를 처리하는 중 오류가 발생했습니다."

    # ------------------------------------------------------------------
    # 결과 LLM 분석 ------------------------------------------------------
    # ------------------------------------------------------------------
    async def _analyze_tool_results_with_llm(  # noqa: D401, pylint: disable=protected-access
        self,
        user_message: str,
        used_tools: List[str],
        tool_results: Dict[str, str],
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        try:
            logger.debug("LLM 분석 시작 (%d개 도구)", len(used_tools))

            # error 키워드 탐지 -------------------------------------------
            errors: List[str] = []
            for raw in tool_results.values():
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict) and "error" in data:
                        errors.append(str(data["error"]))
                except Exception:
                    if "error" in str(raw).lower():
                        errors.append(str(raw))

            if errors:
                msg = "\n".join(f"- {e}" for e in errors)
                logger.info("도구 결과에 error 발견 → 그대로 반환")
                return f"요청을 처리할 수 없습니다.\n도구 오류:\n{msg}"

            formatted_results = self._format_tool_results(
                used_tools, tool_results)
            tools_count = len(used_tools)
            tools_summary = ", ".join(used_tools)

            analysis_prompt = (
                f"사용자 요청: {user_message}\n\n"
                f"실행된 도구들 ({tools_count}개): {tools_summary}\n\n"
                f"수집된 정보:\n{formatted_results}\n\n"
                "위 정보들을 종합하여 사용자의 요청에 대한 완전하고 유용한 답변을 제공해주세요.\n\n"
                "**다중 도구 결과 종합 지침:**\n"
                "- 여러 도구의 결과를 논리적으로 연결하여 통합된 답변 제공\n"
                "- 각 도구 결과의 핵심 정보를 효과적으로 활용\n"
                "- 사용자가 원하는 모든 정보를 포괄적으로 포함\n"
                "- 정보 간의 관련성이나 차이점이 있다면 명확히 설명\n"
                "- 간결하면서도 완전한 답변으로 구성\n"
                "- 필요시 시간순, 중요도순 등으로 정보를 구조화\n\n"
                "사용자의 질문 의도를 정확히 파악하여 가장 유용한 형태로 정보를 제공해주세요."
            )

            if not analysis_prompt.strip():
                logger.warning("분석 프롬프트가 비어있음")
                return formatted_results

            temp_messages = [ConversationMessage(
                role="user", content=analysis_prompt)]
            response = await self.llm_service.generate_response(temp_messages, streaming_callback)

            if not response or not hasattr(response, "response"):
                logger.warning("LLM 응답 객체가 유효하지 않음")
                return formatted_results

            result = response.response.strip() if response.response else ""
            return result or formatted_results
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("LLM 분석 오류: %s", exc)
            return self._format_tool_results(used_tools, tool_results)

    # ------------------------------------------------------------------
    # 플레이스홀더 치환 --------------------------------------------------
    # ------------------------------------------------------------------
    def _substitute_tool_placeholders(self, text: str, tool_results: Dict[str, str]) -> str:  # noqa: D401, pylint: disable=protected-access
        out = str(text)
        for tool_name, raw in tool_results.items():
            try:
                data = json.loads(raw)
                result_str = data.get("result", raw)
            except Exception:  # pylint: disable=broad-except
                result_str = raw

            patterns = [
                rf"`[^`]*{tool_name}\([^`]*`",  # 백틱 포함 호출
                rf"{tool_name}\([^)]*\)",  # 일반 호출
            ]
            for pat in patterns:
                out = re.sub(pat, result_str, out)
        return out
