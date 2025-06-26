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
        """ReAct Agent 응답 생성 - 적응형 워크플로우 우선 시도"""
        try:
            # 사용자 메시지 추가
            self.add_user_message(user_message)

            logger.info("ReactAgent: 적응형 워크플로우 우선 시도")
            
            # 1. 먼저 적응형 워크플로우 시도
            try:
                from application.llm.workflow.adaptive_workflow import AdaptiveWorkflow
                adaptive_workflow = AdaptiveWorkflow()
                
                # 적응형 워크플로우 실행
                workflow_response = await adaptive_workflow.run(self, user_message, streaming_callback)
                
                if workflow_response and len(workflow_response.strip()) > 10:  # 의미있는 응답인지 확인
                    logger.info("적응형 워크플로우로 성공적으로 처리됨")
                    return self._create_response_data(
                        workflow_response, 
                        reasoning="적응형 워크플로우 실행", 
                        used_tools=["adaptive_workflow"]
                    )
                else:
                    logger.warning("적응형 워크플로우 응답이 불충분함")
                    
            except Exception as workflow_exc:
                logger.warning("적응형 워크플로우 실행 실패: %s", workflow_exc)
            
            # 2. 적응형 워크플로우 실패 시 기존 ReAct 에이전트 시도
            logger.info("기존 ReAct 에이전트로 폴백")
            react_result = await self._run_react_agent(user_message, streaming_callback)
            
            if react_result and react_result.get("response"):
                return self._create_response_data(
                    react_result["response"],
                    reasoning="ReAct 에이전트 실행",
                    used_tools=react_result.get("used_tools", [])
                )
            
            # 3. ReAct 에이전트도 실패 시 자동 도구 플로우 시도
            logger.info("자동 도구 플로우로 최종 시도")
            auto_result = await self._auto_tool_flow(user_message, streaming_callback)
            
            if auto_result:
                return auto_result
            
            # 4. 모든 방법 실패 시 기본 응답
            logger.warning("모든 처리 방법 실패, 기본 응답 생성")
            basic_response = await self._generate_basic_response(user_message, streaming_callback)
            return self._create_response_data(basic_response, reasoning="기본 LLM 응답")
            
        except Exception as e:
            logger.error("ReactAgent 전체 처리 실패: %s", e)
            return self._handle_exceptions(e)

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
            "당신은 범용 MCP 도구를 활용하는 지능형 AI 어시스턴트입니다.\n\n"
            "**핵심 역할:**\n"
            "- 사용자의 요청을 정확히 이해하고 적절한 도구를 선택하여 정보를 수집\n"
            "- 사용자 요청의 성격에 따라 간결하거나 자세한 답변을 제공\n"
            "- 범용 MCP 도구 시스템의 확장성과 호환성을 고려한 응답 생성\n\n"
            "**응답 스타일 가이드라인:**\n\n"
            "1. **단순 정보 요청**:\n"
            "   - 핵심 정보만 간결하게 제공\n"
            "   - 불필요한 분석이나 부가 설명 생략\n"
            "   - 직접적이고 명확한 답변\n\n"
            "2. **복잡한 분석 요청**:\n"
            "   - 상세한 분석과 인사이트 제공\n"
            "   - 다각도 검토 및 맥락 정보 포함\n"
            "   - 구조화된 형태의 포괄적 답변\n\n"
            "3. **일반적인 질문**:\n"
            "   - 질문 범위에 맞는 적절한 수준의 답변\n"
            "   - 필요에 따라 간결하거나 상세하게 조절\n\n"
            "**작업 절차:**\n"
            "1. **요청 분석**: 사용자 질문의 복잡도와 기대 응답 수준 파악\n"
            "2. **도구 활용**: 필요한 정보 수집\n"
            "3. **적절한 응답 생성**: 요청 성격에 맞는 답변 길이와 상세도 조절\n\n"
            "**🚨 중요 원칙 - 반드시 준수:**\n"
            "- **시간/날짜 정보**: 현재 시간, 오늘 날짜, 몇 시, 몇 일 등 모든 시간 관련 질문에는 반드시 해당 도구를 사용하세요. 절대 추측하지 마세요.\n"
            "- **도구 결과 우선**: 도구로 수집한 데이터를 주요 근거로 사용\n"
            "- **한국어 응답**: 모든 응답은 자연스러운 한국어로 작성\n"
            "- **범용성 고려**: 다양한 MCP 도구와 호환되는 일관된 접근 방식\n"
            "- **요청 맞춤형 응답**: 사용자가 원하는 수준의 정보만 제공\n\n"
            "**특별 지침:**\n"
            "- 시간, 날짜, 현재 정보 관련 질문에는 반드시 적절한 도구를 사용하세요\n"
            "- 사용자의 질문이 간단하면 간단하게, 복잡하면 상세하게 답변하세요\n"
            "- 도구 사용 후 결과를 사용자 요청 수준에 맞게 적절히 가공하여 제공하세요\n"
            "- 추측하지 말고 항상 최신 정보를 위해 도구를 활용하세요\n"
            "- '오늘 몇 일?', '지금 날짜?', '현재 시간?' 같은 질문에는 100% 도구를 사용하세요"
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
            
            # 메시지 내용 검증 및 정리
            clean_message = user_message.strip()
            if not clean_message:
                logger.warning("빈 메시지 내용")
                return {"response": "메시지를 입력해 주세요.", "used_tools": []}
            
            # Gemini 모델의 경우 더 엄격한 메시지 검증
            model_name = str(self.llm_config.model).lower()
            if "gemini" in model_name:
                # Gemini는 특정 문자나 형식에 민감하므로 추가 정리
                clean_message = clean_message.replace('\x00', '').replace('\n\n\n', '\n\n')
                if len(clean_message) > 8000:  # Gemini 토큰 제한 고려
                    clean_message = clean_message[:8000] + "..."
                logger.debug("Gemini 모델용 메시지 정리 완료")
            
            messages = [HumanMessage(content=clean_message)]
            inputs = {"messages": messages}

            logger.debug(
                "ReactAgent 실행 설정: thread_id=%s, message_length=%d, model=%s",
                thread_id,
                len(clean_message),
                model_name,
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
            logger.debug("비스트리밍 모드로 ReactAgent 실행")
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
            
            # 400 에러 등 특정 에러의 경우 자동 툴 라우팅으로 폴백
            error_str = str(exc).lower()
            if any(keyword in error_str for keyword in ["400", "null", "invalid_argument", "expected string"]):
                logger.info("ReAct 결과가 비어있거나 오류임 → 자동 툴 라우팅 시도")
                fallback_result = await self._auto_tool_flow(user_message, streaming_callback)
                if fallback_result:
                    return fallback_result
            
            return {"response": f"ReAct 처리 중 오류 발생: {str(exc)}", "used_tools": []}

    # ------------------------------------------------------------------
    # 범용 자동 툴 라우팅 ---------------------------------------------------
    # ------------------------------------------------------------------
    async def _auto_tool_flow(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Optional[Dict[str, Any]]:
        """ReAct 실패 시 LLM이 직접 도구를 선택하게 하는 범용적 접근 방식."""
        try:
            if self.mcp_tool_manager is None:
                return None

            logger.info("범용 자동 라우팅: LLM이 적절한 도구를 직접 선택하도록 처리")
            
            # 사용 가능한 모든 도구 목록 가져오기
            langchain_tools = await self.mcp_tool_manager.get_langchain_tools()
            if not langchain_tools:
                logger.warning("사용 가능한 도구가 없습니다")
                return None

            # LLM이 직접 도구를 선택하고 실행하도록 위임
            # 기본 LLM 모델을 사용해서 도구 선택 및 실행
            llm = self._create_llm_model()
            if llm is None:
                return None

            # 도구 설명 포함한 프롬프트 생성
            tools_desc = "\n".join([f"- {tool.name}: {tool.description}" for tool in langchain_tools])
            
            prompt = f"""사용자 요청: {user_message}

사용 가능한 도구들:
{tools_desc}

위 요청을 처리하기 위해 필요한 도구를 선택하고 매개변수를 결정하세요.

**중요 지침:**
1. 단일 도구가 충분한 경우: {{"tool_name": "도구명", "arguments": {{"param": "value"}}}}
2. 여러 도구가 필요한 경우: [{{"tool_name": "도구1", "arguments": {{}}}}, {{"tool_name": "도구2", "arguments": {{}}}}]
3. 시간/날짜 질문: get_current_time 또는 get_current_date 사용
4. 날씨 질문: get_current_weather 또는 get_detailed_weather 사용
5. 검색이 필요한 경우: search_web 사용
6. "시간과 날씨"처럼 두 가지 정보가 필요하면 배열 형식으로 두 도구 모두 포함

반드시 JSON 형식으로만 응답하세요."""

            try:
                response = await llm.ainvoke(prompt)
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # 마크다운 코드 블록 제거하고 JSON 추출
                import json
                import re

                # 마크다운 코드 블록을 찾아서 JSON 추출
                # ```json {...} ``` 또는 ``` {...} ``` 패턴 모두 지원
                json_patterns = [
                    r'```(?:json)?\s*(\[[^\]]*\])\s*```',  # 마크다운 블록 내 JSON 배열
                    r'```(?:json)?\s*(\{[^`]*\})\s*```',   # 마크다운 블록 내 JSON 객체
                    r'(\[[^\]]*"tool_name"[^\]]*\])',      # tool_name을 포함한 JSON 배열
                    r'(\{[^{}]*"tool_name"[^{}]*\})',      # tool_name을 포함한 JSON 객체
                    r'(\{.*?\})',                          # 일반 JSON 객체
                    r'(\[.*?\])'                           # 일반 JSON 배열
                ]
                
                json_text = None
                for pattern in json_patterns:
                    match = re.search(pattern, response_text, re.DOTALL)
                    if match:
                        json_text = match.group(1).strip()
                        break
                
                if not json_text:
                    # 패턴 매칭 실패 시 전체 텍스트 사용
                    json_text = response_text.strip()
                
                logger.debug("추출된 JSON 텍스트: %s", json_text)
                tool_selection = json.loads(json_text)
                
                # 배열 형식인 경우 여러 도구 순차 실행 지원
                tools_to_execute = []
                if isinstance(tool_selection, list):
                    if tool_selection:
                        logger.info("배열 형식 도구 선택 감지: %d개 도구를 순차 실행합니다", len(tool_selection))
                        tools_to_execute = tool_selection
                    else:
                        logger.warning("빈 배열이 반환되었습니다")
                        return None
                else:
                    # 단일 도구 객체
                    tools_to_execute = [tool_selection]
                
                # 여러 도구 실행
                tool_results = {}
                used_tools = []
                
                for i, tool_spec in enumerate(tools_to_execute):
                    selected_tool = tool_spec.get("tool_name")
                    arguments = tool_spec.get("arguments", {})
                    
                    if not selected_tool:
                        logger.warning("도구 %d: tool_name이 없습니다", i+1)
                        continue
                    
                    logger.info("도구 %d/%d 실행: %s, 매개변수: %s", i+1, len(tools_to_execute), selected_tool, arguments)
                    
                    try:
                        # 도구 실행
                        tool_result_raw = await self.mcp_tool_manager.call_mcp_tool(selected_tool, arguments)
                        tool_results[selected_tool] = tool_result_raw
                        used_tools.append(selected_tool)
                        
                        # 스트리밍 피드백 (선택사항)
                        if streaming_callback and len(tools_to_execute) > 1:
                            streaming_callback(f"🔧 {selected_tool} 완료 ({i+1}/{len(tools_to_execute)})\n")
                            
                    except Exception as tool_exc:
                        logger.error("도구 %s 실행 실패: %s", selected_tool, tool_exc)
                        tool_results[selected_tool] = json.dumps({"error": f"도구 실행 실패: {str(tool_exc)}"})
                        used_tools.append(selected_tool)
                
                if not used_tools:
                    logger.warning("실행할 수 있는 도구가 없습니다")
                    return None

                # 결과 분석
                analyzed = await self._analyze_tool_results_with_llm(
                    user_message, used_tools, tool_results, streaming_callback
                )
                if analyzed:
                    return {
                        "response": analyzed,
                        "reasoning": "범용 자동 툴 라우팅",
                        "used_tools": used_tools,
                    }
                
                # 분석 실패 시 포맷팅된 결과 반환
                formatted = self._format_tool_results(used_tools, tool_results)
                return {
                    "response": formatted,
                    "reasoning": "범용 자동 툴 라우팅 (포맷팅)",
                    "used_tools": used_tools,
                }
                
            except json.JSONDecodeError:
                logger.error("LLM 응답의 JSON 파싱 실패: %s", response_text)
                return None
            except Exception as inner_exc:
                logger.error("도구 선택/실행 중 오류: %s", inner_exc)
                return None
                
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("범용 자동 툴 라우팅 오류: %s", exc)
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
