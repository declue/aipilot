import json
import logging
from typing import Any, Callable, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from application.llm.agents.base_agent import BaseAgent
from application.llm.workflow.workflow_utils import astream_graph

logger = logging.getLogger(__name__)


class ReactAgent(BaseAgent):
    """
    ReAct + MCP 툴 모드 전용 Agent
    ReAct 에이전트를 사용하여 사용자 요청을 처리하고, MCP 도구를 활용하여 추가 정보를 수집합니다.
    범용적인 Agent로 특정 도구를 위한 처리를 하지 않습니다.
    대화 컨텍스트를 유지하고, 도구 결과를 분석하여 최종 응답을 생성합니다.

    """

    # ------------------------------------------------------------------
    # 기초 초기화 --------------------------------------------------------
    # ------------------------------------------------------------------
    def __init__(self, config_manager: Any, mcp_tool_manager: Optional[Any] = None) -> None:
        super().__init__(config_manager, mcp_tool_manager)
        self.react_agent: Optional[Any] = None
        self.checkpointer: Optional[Any] = MemorySaver()

    # ------------------------------------------------------------------
    # 퍼사드 헬퍼 ---------------------------------------------------------
    # ------------------------------------------------------------------
    def is_available(self) -> bool:  # noqa: D401
        return MemorySaver and self.mcp_tool_manager is not None

    # ------------------------------------------------------------------
    # 공개 API -----------------------------------------------------------
    # ------------------------------------------------------------------
    async def generate_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """ReAct 기반 응답 생성. 기존 LLMAgent._handle_react_agent_mode 와 동일한 흐름"""
        from application.llm.monitoring.performance_tracker import PerformanceTracker

        # 성능 추적 시작
        tracker = PerformanceTracker(
            operation_name="ReactAgent.generate_response",
            agent_type="ReactAgent",
            model=getattr(self.llm_config, "model", "unknown"),
            track_metrics=True,
        )
        
        async with tracker.atrack():
            logger.info("ReactAgent.generate_response: %s", user_message[:50])
            # 사용 기록
            self.add_user_message(user_message)

            if not self.is_available():
                error_msg = "ReAct 모드를 사용할 수 없습니다. "
                if not MemorySaver:
                    error_msg += "langgraph 라이브러리가 설치되지 않았습니다."
                elif self.mcp_tool_manager is None:
                    error_msg += "MCP 도구 관리자가 초기화되지 않았습니다."

                logger.error(error_msg)
                return self._create_error_response(error_msg)

            # React 에이전트 초기화 (최초 1회)
            if not self.react_agent:
                init_ok = await self._initialize_react_agent()
                if not init_ok:
                    error_msg = "ReactAgent 초기화에 실패했습니다."
                    logger.error(error_msg)
                    return self._create_error_response(error_msg)

            # 실제 실행
            result = await self._run_react_agent(user_message, streaming_callback)

            # ReAct 실행 결과 확인: 비어있거나 오류 메시지인 경우 자동 툴 라우팅 시도
            response_text = result.get("response", "").strip()
            is_empty = not response_text
            is_error = any(
                keyword in response_text.lower() for keyword in ["오류", "error", "실패", "fail"]
            )

            if is_empty or is_error:
                logger.warning("ReAct 결과가 비어있거나 오류임 → 자동 툴 라우팅 시도")
                logger.debug("ReAct 응답: %s", response_text[:100])

                auto_tool_response = await self._auto_tool_flow(user_message, streaming_callback)
                if auto_tool_response is not None:
                    logger.info("자동 툴 라우팅 성공")
                    return auto_tool_response

                logger.warning("자동 툴 라우팅 실패")
                return self._create_error_response(
                    "요청을 처리할 수 없습니다", "ReAct 및 자동 툴 라우팅 모두 실패"
                )

            return {
                "response": result.get("response", ""),
                "reasoning": "ReAct 에이전트를 사용한 응답",
                "used_tools": result.get("used_tools", []),
            }

    def _handle_exceptions(self, exc: Exception) -> Dict[str, Any]:
        """예외 처리 통합"""
        logger.error("ReactAgent 오류: %s", exc)
        return self._create_error_response("ReAct 모드 처리 중 오류가 발생했습니다", str(exc))

    # ------------------------------------------------------------------
    # 내부 메서드 ---------------------------------------------------------
    # ------------------------------------------------------------------
    async def _initialize_react_agent(self) -> bool:
        """langgraph 의 create_react_agent 를 사용해 에이전트 객체 생성"""
        try:
            if not MemorySaver or create_react_agent is None or self.mcp_tool_manager is None:
                return False

            tools = await self.mcp_tool_manager.get_langchain_tools()
            if not tools:
                logger.warning("사용 가능한 MCP 도구가 없습니다")
                return False

            llm = self._create_llm_model()
            if llm is None:
                return False

            prompt = self._get_system_prompt()
            self.react_agent = create_react_agent(
                llm, tools, checkpointer=self.checkpointer, prompt=prompt
            )
            logger.info("ReactAgent 초기화 완료 (도구 %d개)", len(tools))
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("ReactAgent 초기화 실패: %s", exc)
            return False

    def _get_system_prompt(self) -> str:  # noqa: D401
        return (
            "당신은 다양한 도구를 활용하여 정보를 수집하고 분석하는 지능형 AI 어시스턴트입니다.\n\n"
            "**핵심 역할:**\n"
            "- 사용자의 요청을 정확히 이해하고 적절한 도구를 선택하여 정보를 수집\n"
            "- 수집된 정보를 분석하여 사용자에게 맞춤화된 유용한 답변 제공\n"
            "- 단순한 나열이 아닌 깊이 있는 분석과 인사이트 제공\n\n"
            "**작업 절차:**\n\n"
            "1. **요청 분석**: 사용자가 원하는 것을 정확히 파악하고 필요한 도구 결정\n\n"
            "2. **도구 활용**: 적절한 도구를 사용하여 관련 정보 수집\n\n"
            "3. **정보 분석 및 가공** (매우 중요):\n"
            "   - 도구로부터 받은 원시 데이터를 철저히 분석\n"
            "   - 핵심 정보와 패턴을 추출하고 의미있는 인사이트 도출\n"
            "   - 여러 소스의 정보를 연결하고 비교 분석\n"
            "   - 사용자의 원래 질문에 맞게 정보를 재구성\n\n"
            "4. **맞춤형 응답 생성**:\n"
            "   - 수집된 정보를 기반으로 상세하고 유용한 답변 작성\n"
            "   - 관련 세부사항, 인용구, 통계 등을 포함\n"
            "   - 명확하고 논리적으로 정보 구성\n"
            "   - 출처 명시 및 맥락 제공\n\n"
            "**중요 원칙:**\n"
            "- **도구 결과 우선**: 도구로 수집한 데이터를 주요 근거로 사용\n"
            "- **분석적 접근**: 단순 요약이 아닌 해석과 맥락 제공\n"
            "- **한국어 응답**: 모든 응답은 자연스러운 한국어로 작성\n"
            "- **전문적이고 도움이 되는 톤**: 명확하고 유익한 정보 전달\n"
            "- **풍부한 콘텐츠**: 도구가 제공하는 상세 정보를 최대한 활용\n\n"
            "**특별 지침:**\n"
            "도구를 사용한 후에는 반드시 결과를 분석하여 사용자 요청에 맞는 유용한 답변을 생성해야 합니다.\n"
            "원시 데이터를 그대로 나열하지 말고, 사용자가 이해하기 쉽고 실용적인 형태로 가공하여 제공하세요."
        )

    async def _run_react_agent(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """ReAct agent 의 ainvoke / astream_graph 실행 로직 (단순화 버전)"""
        if self.react_agent is None:
            return {"response": "ReAct 에이전트가 초기화되지 않았습니다.", "used_tools": []}

        # 입력 검증
        if not user_message or not user_message.strip():
            logger.warning("빈 사용자 메시지")
            return {"response": "메시지를 입력해 주세요.", "used_tools": []}

        # thread_id 검증 및 기본값 설정
        thread_id = getattr(self, "thread_id", None) or "default-thread"
        if not isinstance(thread_id, str):
            thread_id = str(thread_id)

        try:
            config = RunnableConfig(recursion_limit=100, configurable={"thread_id": thread_id})
            messages = [HumanMessage(content=user_message.strip())]
            inputs = {"messages": messages}

            logger.debug(
                "ReactAgent 실행 설정: thread_id=%s, message_length=%d",
                thread_id,
                len(user_message),
            )
        except Exception as exc:
            logger.error("ReactAgent 설정 생성 실패: %s", exc)
            return {"response": "ReAct 에이전트 설정에 문제가 있습니다.", "used_tools": []}

        # 스트리밍 지원 여부
        if streaming_callback is not None:

            accumulated: str = ""
            used_tools: List[str] = []

            try:
                async for chunk in astream_graph(self.react_agent, inputs, config=config):
                    # 오류 청크 처리
                    if isinstance(chunk, dict) and chunk.get("type") == "error":
                        logger.error(
                            "그래프 스트리밍 오류 청크: %s", chunk.get("error", "Unknown error")
                        )
                        continue

                    # 간단 처리: AIMessage content 만 뽑아 누적
                    if isinstance(chunk, dict) and "agent" in chunk:
                        for msg in chunk["agent"].get("messages", []):
                            if hasattr(msg, "content") and msg.content:
                                content = str(msg.content)
                                if content and content.strip():  # 빈 내용 필터링
                                    accumulated += content
                    # tool usage (간략)
                    if isinstance(chunk, dict) and "tools" in chunk:
                        for msg in chunk["tools"].get("messages", []):
                            if hasattr(msg, "name"):
                                used_tools.append(str(msg.name))

                    # 실제 내용이 있을 때만 콜백 호출
                    if accumulated and accumulated.strip() and streaming_callback is not None:
                        streaming_callback(accumulated)

                logger.debug(
                    "스트리밍 완료: accumulated=%d자, tools=%d개", len(accumulated), len(used_tools)
                )
                return {"response": accumulated, "used_tools": used_tools}
            except Exception as exc:
                logger.error("ReactAgent 스트리밍 실행 중 오류: %s", exc)
                # 스트리밍 실패 시 비스트리밍으로 재시도하지 않고 바로 오류 반환
                return {"response": f"스트리밍 처리 중 오류 발생: {str(exc)}", "used_tools": []}

        # 비스트리밍 모드
        try:
            result = await self.react_agent.ainvoke(inputs, config=config)
            response_text = ""
            used_tools: List[str] = []
            tool_results: Dict[str, str] = {}

            if isinstance(result, dict) and "messages" in result:
                # 마지막 AIMessage 찾기
                for msg in reversed(result["messages"]):
                    if hasattr(msg, "content") and msg.content:
                        content = str(msg.content).strip()
                        if content:  # 빈 내용 필터링
                            response_text = content
                            break
                # 도구 메시지
                for msg in result["messages"]:
                    if str(type(msg)).find("ToolMessage") != -1:
                        if hasattr(msg, "name"):
                            used_tools.append(str(msg.name))
                            if hasattr(msg, "content") and msg.content:
                                tool_results[str(msg.name)] = str(msg.content)

            # 플레이스홀더 치환
            if response_text and tool_results:
                response_text = self._substitute_tool_placeholders(response_text, tool_results)

            logger.debug(
                "비스트리밍 완료: response=%d자, tools=%d개", len(response_text), len(used_tools)
            )
            return {"response": response_text, "used_tools": used_tools}
        except Exception as exc:
            logger.error("ReactAgent 비스트리밍 실행 중 오류: %s", exc)
            return {"response": f"ReAct 처리 중 오류 발생: {str(exc)}", "used_tools": []}

    # ------------------------------------------------------------------
    # 간단 자동 툴 라우팅 ---------------------------------------------------
    # ------------------------------------------------------------------
    async def _auto_tool_flow(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Optional[Dict[str, Any]]:
        """ReAct 실패 시 간단한 규칙 기반으로 MCP 도구를 선택해 실행한다."""
        try:
            if self.mcp_tool_manager is None:
                return None

            # 1) 사용할 도구 결정 ------------------------------------------------
            lowered = user_message.lower()
            selected_tool = None
            arguments: Dict[str, Any] = {}

            langchain_tools = await self.mcp_tool_manager.get_langchain_tools()
            if not langchain_tools:
                return None

            def find_tool(keyword: str):
                for t in langchain_tools:
                    if keyword in t.name.lower():
                        return t.name
                return None

            if any(k in lowered for k in ["날씨", "weather"]):
                selected_tool = find_tool("weather") or find_tool("get_current_weather")
                city_kwds = ["서울", "seoul", "오산", "osan"]
                for ck in city_kwds:
                    if ck in user_message:
                        arguments = {"city": ck}
                        break
            elif any(k in lowered for k in ["시간", "time"]):
                selected_tool = find_tool("time") or find_tool("current_time")
            else:
                selected_tool = (
                    find_tool("search") or find_tool("duckduckgo") or find_tool("web_search")
                )
                if selected_tool:
                    arguments = {"query": user_message}

            if selected_tool is None:
                logger.info("자동 라우팅: 적절한 도구를 찾지 못함")
                return None

            logger.info("자동 라우팅 선택 도구: %s", selected_tool)

            # 2) 도구 호출 -----------------------------------------------------
            tool_result_raw = await self.mcp_tool_manager.call_mcp_tool(selected_tool, arguments)
            tool_results = {selected_tool: tool_result_raw}
            used_tools = [selected_tool]

            # 3) 결과 검사 및 오류 처리 -----------------------------------------
            # 도구 결과에 오류가 있는지 먼저 확인
            if self._has_tool_error(tool_result_raw):
                error_message = self._extract_error_message(tool_result_raw)
                logger.warning("자동 라우팅 도구 오류: %s", error_message)
                return {
                    "response": error_message,
                    "reasoning": "자동 툴 라우팅 (오류)",
                    "used_tools": used_tools,
                }

            # 4) 결과 분석 (오류가 없는 경우에만) ---------------------------------
            analyzed = await self._analyze_tool_results_with_llm(
                user_message, used_tools, tool_results, streaming_callback
            )
            if analyzed:
                return {
                    "response": analyzed,
                    "reasoning": "자동 툴 라우팅",
                    "used_tools": used_tools,
                }
            # 분석 실패 시 원시 결과 포맷팅
            formatted = self._format_tool_results(used_tools, tool_results)
            return {
                "response": formatted,
                "reasoning": "자동 툴 라우팅 (포맷팅)",
                "used_tools": used_tools,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("자동 툴 라우팅 오류: %s", exc)
            return None

    def _has_tool_error(self, tool_result: Any) -> bool:
        """도구 결과에 오류가 있는지 확인합니다."""
        try:
            # JSON 문자열인 경우 파싱
            if isinstance(tool_result, str):

                try:
                    result_dict = json.loads(tool_result)
                except json.JSONDecodeError:
                    # JSON이 아닌 경우 오류로 간주하지 않음
                    return False
            elif isinstance(tool_result, dict):
                result_dict = tool_result
            else:
                # 다른 타입인 경우 오류로 간주하지 않음
                return False

            # 'error' 키가 있으면 오류로 판단
            return "error" in result_dict and result_dict["error"]
        except Exception:
            # 파싱 실패 시 오류로 간주하지 않음
            return False

    def _extract_error_message(self, tool_result: Any) -> str:
        """도구 결과에서 오류 메시지를 추출합니다."""
        try:
            # JSON 문자열인 경우 파싱
            if isinstance(tool_result, str):

                try:
                    result_dict = json.loads(tool_result)
                except json.JSONDecodeError:
                    return f"도구 실행 중 오류 발생: {tool_result}"
            elif isinstance(tool_result, dict):
                result_dict = tool_result
            else:
                return f"도구 실행 중 알 수 없는 오류 발생: {str(tool_result)}"

            # 오류 메시지 추출
            if "error" in result_dict:
                error_msg = result_dict["error"]
                if isinstance(error_msg, str):
                    return error_msg
                else:
                    return f"도구 실행 중 오류 발생: {str(error_msg)}"
            else:
                return "도구 실행 중 알 수 없는 오류 발생"
        except Exception as exc:
            return f"도구 결과 처리 중 오류 발생: {str(exc)}"
