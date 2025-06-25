"""
Langchain 기반 LLM 에이전트 - create_react_agent 사용 (OpenAI Compatible)
"""

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

# langgraph import를 try-catch로 처리
try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.prebuilt import create_react_agent

    LANGGRAPH_AVAILABLE = True
    CreateReactAgentFunc: Optional[Any] = create_react_agent
    MemorySaverClass: Optional[Any] = MemorySaver
except ImportError:
    LANGGRAPH_AVAILABLE = False
    CreateReactAgentFunc = None
    MemorySaverClass = None

from application.llm.interfaces.llm_interface import LLMInterface
from application.llm.models.llm_config import LLMConfig
from application.llm.processors.base_processor import ToolResultProcessorRegistry
from application.llm.processors.search_processor import SearchToolResultProcessor
from application.llm.services.conversation_service import ConversationService
from application.llm.services.llm_service import LLMService
from application.llm.workflow.workflow_utils import get_workflow
from application.util.logger import setup_logger

logger = setup_logger("llm_agent") or logging.getLogger("llm_agent")

if not LANGGRAPH_AVAILABLE:
    logger.warning("langgraph를 사용할 수 없습니다. ReAct 모드가 비활성화됩니다.")


class LLMAgent(LLMInterface):
    def __init__(self, config_manager: Any, mcp_tool_manager: Optional[Any] = None) -> None:
        self.config_manager = config_manager
        self.mcp_tool_manager = mcp_tool_manager

        # 설정 로드
        self._load_config()

        # 서비스 초기화
        self.llm_service = LLMService(self.llm_config)
        self.conversation_service = ConversationService()

        # 프로세서 레지스트리 초기화
        self.processor_registry: Optional[ToolResultProcessorRegistry] = None

        # ReAct 에이전트 관련 (langgraph가 사용 가능한 경우만)
        self.react_agent: Optional[Any] = None
        self.checkpointer: Optional[Any] = None
        if LANGGRAPH_AVAILABLE and MemorySaverClass is not None:
            self.checkpointer = MemorySaverClass()

        self.thread_id = str(uuid.uuid4())

        # 히스토리 (하위 호환성)
        self.history: List[Dict[str, str]] = []

        logger.info("LLM 에이전트 초기화 완료")

    def _load_config(self) -> None:
        """설정 로드"""
        try:
            # 프로필 기반 설정 로드 (mode와 workflow 포함)
            llm_config_dict = self.config_manager.get_llm_config()

            self.llm_config = LLMConfig.from_dict(llm_config_dict)
            logger.debug(
                f"LLM 설정 로드 완료: {self.llm_config.model}, 모드: {self.llm_config.mode}"
            )

        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            # 기본 설정으로 폴백 - 모든 필수 필드 포함
            self.llm_config = LLMConfig(
                api_key="",
                base_url=None,
                model="gpt-4o-mini",
                max_tokens=1000,
                temperature=0.7,
                streaming=True,
                mode="basic",
                workflow=None,
            )

    async def generate_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        try:
            logger.info(f"LLM 응답 생성 시작: {user_message[:50]}...")

            # 사용자 메시지 추가
            self.add_user_message(user_message)

            # 모드에 따른 처리
            mode = self._get_llm_mode()
            logger.info(f"🎯 현재 LLM 모드: {mode}")
            logger.info(f"🔧 MCP 도구 관리자 존재: {self.mcp_tool_manager is not None}")
            logger.info(f"🚀 LANGGRAPH 사용 가능: {LANGGRAPH_AVAILABLE}")

            if mode == "workflow":
                logger.info("📋 워크플로우 모드로 처리")
                return await self._handle_workflow_mode(user_message, streaming_callback)
            elif mode == "mcp_tools" and self.mcp_tool_manager and LANGGRAPH_AVAILABLE:
                logger.info("🤖 ReAct 에이전트 모드로 처리")
                return await self._handle_react_agent_mode(user_message, streaming_callback)
            else:
                logger.info("⚡ 기본 모드로 처리")
                return await self._handle_basic_mode(user_message, streaming_callback)
        except Exception as e:
            logger.error(f"응답 생성 중 오류: {e}")
            import traceback

            logger.error(f"응답 생성 상세 오류: {traceback.format_exc()}")
            return self._create_error_response("응답 생성 중 오류가 발생했습니다", str(e))

    async def generate_response_streaming(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """스트리밍 응답 생성 (하위 호환성)"""
        return await self.generate_response(user_message, streaming_callback)

    async def _handle_basic_mode(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """기본 모드 처리"""
        try:
            logger.debug("기본 모드로 응답 생성 중...")
            response = await self._generate_basic_response(user_message, streaming_callback)
            logger.debug(f"기본 응답 생성 완료: {len(response)} 문자")
            return self._create_response_data(response)
        except Exception as e:
            logger.error(f"기본 모드 처리 중 오류: {e}")
            return self._create_error_response("기본 모드 처리 중 오류가 발생했습니다", str(e))

    async def _handle_workflow_mode(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """워크플로우 모드 처리"""
        try:
            workflow_name = self.llm_config.workflow or "basic_chat"
            workflow_class = get_workflow(workflow_name)
            workflow = workflow_class()

            result = await workflow.run(self, user_message, streaming_callback)

            return {
                "response": result,
                "workflow": workflow_name,
                "reasoning": "",
                "used_tools": [],
            }

        except Exception as e:
            logger.error(f"워크플로우 모드 처리 중 오류: {e}")
            return {
                "response": "워크플로우 처리 중 문제가 발생했습니다.",
                "workflow": self.llm_config.workflow or "basic_chat",
                "reasoning": str(e),
                "used_tools": [],
            }

    async def _handle_react_agent_mode(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """ReAct 에이전트 모드 처리"""
        try:
            logger.info("🤖 ReAct 에이전트 모드로 응답 생성 중...")

            if not LANGGRAPH_AVAILABLE:
                logger.error("❌ langgraph가 사용할 수 없음")
                logger.info("🔄 기본 모드로 폴백")
                return await self._handle_basic_mode(user_message, streaming_callback)

            if not self.mcp_tool_manager:
                logger.error("❌ MCP 도구 관리자가 없음")
                logger.info("🔄 기본 모드로 폴백")
                return await self._handle_basic_mode(user_message, streaming_callback)

            # ReAct 에이전트 초기화 (필요한 경우)
            if not self.react_agent:
                logger.info("🔄 ReAct 에이전트 초기화 시작...")
                init_success = await self._initialize_react_agent()
                if not init_success:
                    logger.error("❌ ReAct 에이전트 초기화 실패")
                    logger.info("🔄 기본 모드로 폴백")
                    return await self._handle_basic_mode(user_message, streaming_callback)
                else:
                    logger.info("✅ ReAct 에이전트 초기화 성공")
            else:
                logger.info("✅ ReAct 에이전트 이미 초기화됨")

            # ReAct 에이전트를 사용한 응답 생성
            logger.info("🚀 ReAct 에이전트 실행 시작...")
            result = await self._run_react_agent(user_message, streaming_callback)

            logger.info(f"✅ ReAct 에이전트 응답 완료: {len(result.get('response', ''))} 문자")

            return {
                "response": result.get("response", ""),
                "reasoning": "ReAct 에이전트를 사용한 응답",
                "used_tools": result.get("used_tools", []),
            }

        except Exception as e:
            logger.error(f"ReAct 에이전트 모드 처리 중 오류: {e}")
            import traceback

            logger.error(f"ReAct 에이전트 모드 상세 오류: {traceback.format_exc()}")
            logger.info("🔄 기본 모드로 폴백")
            return await self._handle_basic_mode(user_message, streaming_callback)

    async def _initialize_react_agent(self) -> bool:
        """ReAct 에이전트 초기화"""
        try:
            if not LANGGRAPH_AVAILABLE:
                logger.error("langgraph를 사용할 수 없습니다")
                return False

            if not self.mcp_tool_manager:
                logger.error("MCP 도구 관리자가 없습니다")
                return False

            # MCP 도구 가져오기
            tools = await self.mcp_tool_manager.get_langchain_tools()
            if not tools:
                logger.warning("사용 가능한 MCP 도구가 없습니다")
                return False

            # LLM 모델 초기화
            llm = await self._create_llm_model()
            if not llm:
                logger.error("LLM 모델 생성에 실패했습니다")
                return False

            # 시스템 프롬프트 설정
            system_prompt = self._get_system_prompt()

            # ReAct 에이전트 생성
            if CreateReactAgentFunc is not None and self.checkpointer:
                self.react_agent = CreateReactAgentFunc(
                    llm, tools, checkpointer=self.checkpointer, prompt=system_prompt
                )

                logger.info(f"ReAct 에이전트 초기화 완료: {len(tools)}개 도구")
                return True
            else:
                logger.error("create_react_agent 또는 checkpointer를 사용할 수 없습니다")
                return False

        except Exception as e:
            logger.error(f"ReAct 에이전트 초기화 실패: {e}")
            import traceback

            logger.error(f"ReAct 에이전트 초기화 실패 상세: {traceback.format_exc()}")
            return False

    async def _create_llm_model(self) -> Optional[ChatOpenAI]:
        """OpenAI Compatible LLM 모델 생성"""
        try:
            model_name = str(self.llm_config.model)

            # ChatOpenAI 초기화 - 명시적 파라미터 전달
            openai_params = {
                "model": model_name,
                "temperature": float(self.llm_config.temperature),
            }

            # API 키 설정
            if self.llm_config.api_key:
                openai_params["api_key"] = str(self.llm_config.api_key)

            # base_url이 있으면 추가
            if self.llm_config.base_url:
                openai_params["base_url"] = str(self.llm_config.base_url)

            # streaming 설정
            if hasattr(self.llm_config, "streaming") and self.llm_config.streaming is not None:
                openai_params["streaming"] = bool(self.llm_config.streaming)

            logger.debug(
                f"ChatOpenAI 초기화 파라미터: model={model_name}, base_url={openai_params.get('base_url', 'None')}"
            )

            # 명시적 생성자 호출 - 안정성을 위한 추가 파라미터
            return ChatOpenAI(
                model=str(openai_params["model"]),
                temperature=float(openai_params["temperature"]),
                api_key=str(openai_params["api_key"]) if openai_params.get("api_key") else None,
                base_url=str(openai_params["base_url"]) if openai_params.get("base_url") else None,
                streaming=bool(openai_params.get("streaming", True)),
                max_tokens=None,  # 최대 토큰 제한 없음
                timeout=60,  # 60초 타임아웃
                max_retries=3,  # 최대 3회 재시도
            )

        except Exception as e:
            logger.error(f"LLM 모델 생성 실패: {e}")
            import traceback

            logger.error(f"LLM 모델 생성 실패 상세: {traceback.format_exc()}")
            return None

    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return """당신은 다양한 도구를 활용하여 정보를 수집하고 분석하는 지능형 AI 어시스턴트입니다.

**핵심 역할:**
- 사용자의 요청을 정확히 이해하고 적절한 도구를 선택하여 정보를 수집
- 수집된 정보를 분석하여 사용자에게 맞춤화된 유용한 답변 제공
- 단순한 나열이 아닌 깊이 있는 분석과 인사이트 제공

**작업 절차:**

1. **요청 분석**: 사용자가 원하는 것을 정확히 파악하고 필요한 도구 결정

2. **도구 활용**: 적절한 도구를 사용하여 관련 정보 수집

3. **정보 분석 및 가공** (매우 중요):
   - 도구로부터 받은 원시 데이터를 철저히 분석
   - 핵심 정보와 패턴을 추출하고 의미있는 인사이트 도출
   - 여러 소스의 정보를 연결하고 비교 분석
   - 사용자의 원래 질문에 맞게 정보를 재구성

4. **맞춤형 응답 생성**:
   - 수집된 정보를 기반으로 상세하고 유용한 답변 작성
   - 관련 세부사항, 인용구, 통계 등을 포함
   - 명확하고 논리적으로 정보 구성
   - 출처 명시 및 맥락 제공

**중요 원칙:**
- **도구 결과 우선**: 도구로 수집한 데이터를 주요 근거로 사용
- **분석적 접근**: 단순 요약이 아닌 해석과 맥락 제공
- **한국어 응답**: 모든 응답은 자연스러운 한국어로 작성
- **전문적이고 도움이 되는 톤**: 명확하고 유익한 정보 전달
- **풍부한 콘텐츠**: 도구가 제공하는 상세 정보를 최대한 활용

**특별 지침:**
도구를 사용한 후에는 반드시 결과를 분석하여 사용자 요청에 맞는 유용한 답변을 생성해야 합니다.
원시 데이터를 그대로 나열하지 말고, 사용자가 이해하기 쉽고 실용적인 형태로 가공하여 제공하세요."""

    async def _run_react_agent(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """ReAct 에이전트 실행"""
        try:
            logger.info(f"🔥 ReAct 에이전트 실행 메서드 진입: {user_message[:50]}...")

            if not self.react_agent:
                logger.error("❌ ReAct 에이전트가 초기화되지 않음")
                return {"response": "ReAct 에이전트가 초기화되지 않았습니다.", "used_tools": []}

            logger.info("✅ ReAct 에이전트 확인 완료")

            # 설정 생성 (configurable 사용)
            config = RunnableConfig(recursion_limit=100, configurable={"thread_id": self.thread_id})
            logger.info(f"✅ 설정 생성 완료: thread_id={self.thread_id}")

            # 메시지 생성
            messages = [HumanMessage(content=user_message)]
            inputs = {"messages": messages}
            logger.info(f"✅ 입력 메시지 생성 완료: {len(messages)}개 메시지")

            # 스트리밍이 활성화된 경우
            if streaming_callback is not None:
                logger.info("🎬 스트리밍 모드로 실행")
                accumulated_response = ""
                used_tools: List[str] = []
                tool_results: Dict[str, str] = {}

                try:
                    # astream_graph 활용하여 스트리밍 처리
                    from application.llm.workflow.workflow_utils import astream_graph

                    logger.info("✅ astream_graph import 성공")

                    def streaming_wrapper(chunk: Dict[str, Any]) -> None:
                        nonlocal accumulated_response, used_tools, tool_results

                        logger.info(
                            f"📦 스트리밍 청크 수신: {type(chunk)}, keys={list(chunk.keys()) if isinstance(chunk, dict) else 'N/A'}"
                        )

                        # langgraph ReAct 에이전트의 실제 응답 구조 처리
                        if isinstance(chunk, dict):
                            # 직접 messages 키가 있는 경우
                            if "messages" in chunk:
                                logger.info(
                                    f"📬 직접 메시지 청크 처리: {len(chunk['messages'])}개 메시지"
                                )
                                for i, message in enumerate(chunk["messages"]):
                                    logger.info(
                                        f"📨 직접 메시지 {i}: type={type(message)}, hasattr(content)={hasattr(message, 'content')}"
                                    )
                                    # AIMessage만 사용자에게 전달 (도구 결과는 제외)
                                    if (
                                        hasattr(message, "content")
                                        and message.content
                                        and str(type(message)).find("AIMessage") != -1
                                    ):
                                        content = str(message.content)
                                        accumulated_response += content
                                        logger.info(
                                            f"📝 직접 AI 컨텐츠 추가: {len(content)}자, 누적={len(accumulated_response)}자"
                                        )
                                        try:
                                            if streaming_callback is not None:
                                                streaming_callback(content)
                                                logger.info(f"✅ 직접 AI 스트리밍 콜백 실행 성공")
                                        except Exception as e:
                                            logger.error(f"❌ 직접 AI 스트리밍 콜백 실행 오류: {e}")

                                    # 도구 사용 추적 (로깅용)
                                    if hasattr(message, "tool_calls") and message.tool_calls:
                                        for tool_call in message.tool_calls:
                                            tool_name = (
                                                tool_call.get("name", "unknown_tool")
                                                if isinstance(tool_call, dict)
                                                else getattr(tool_call, "name", "unknown_tool")
                                            )
                                            used_tools.append(tool_name)
                                            logger.info(f"🔧 직접 도구 사용: {tool_name}")

                                            # --- 사용자에게 진행 상황 알림 ---
                                            try:
                                                if streaming_callback is not None:
                                                    streaming_callback(f"\n⏳ '{tool_name}' 도구 실행 중...<br/>")
                                            except Exception as cb_err:
                                                logger.error(f"진행 상황 콜백 오류: {cb_err}")

                            # agent 키 안에 messages가 있는 경우 (ReAct 에이전트 구조)
                            elif (
                                "agent" in chunk
                                and isinstance(chunk["agent"], dict)
                                and "messages" in chunk["agent"]
                            ):
                                logger.info(
                                    f"📬 에이전트 메시지 청크 처리: {len(chunk['agent']['messages'])}개 메시지"
                                )
                                for i, message in enumerate(chunk["agent"]["messages"]):
                                    logger.info(
                                        f"📨 에이전트 메시지 {i}: type={type(message)}, hasattr(content)={hasattr(message, 'content')}"
                                    )
                                    # AIMessage만 사용자에게 전달 (도구 결과는 제외)
                                    if (
                                        hasattr(message, "content")
                                        and message.content
                                        and str(type(message)).find("AIMessage") != -1
                                    ):
                                        content = str(message.content)
                                        accumulated_response += content
                                        logger.info(
                                            f"📝 에이전트 AI 컨텐츠 추가: {len(content)}자, 누적={len(accumulated_response)}자"
                                        )
                                        try:
                                            if streaming_callback is not None:
                                                streaming_callback(content)
                                                logger.info(
                                                    f"✅ 에이전트 AI 스트리밍 콜백 실행 성공"
                                                )
                                        except Exception as e:
                                            logger.error(
                                                f"❌ 에이전트 AI 스트리밍 콜백 실행 오류: {e}"
                                            )

                                    # 도구 사용 추적 (로깅용)
                                    if hasattr(message, "tool_calls") and message.tool_calls:
                                        for tool_call in message.tool_calls:
                                            tool_name = (
                                                tool_call.get("name", "unknown_tool")
                                                if isinstance(tool_call, dict)
                                                else getattr(tool_call, "name", "unknown_tool")
                                            )
                                            used_tools.append(tool_name)
                                            logger.info(f"🔧 에이전트 도구 사용: {tool_name}")

                                            # --- 사용자에게 진행 상황 알림 ---
                                            try:
                                                if streaming_callback is not None:
                                                    streaming_callback(f"\n⏳ '{tool_name}' 도구 실행 중...<br/>")
                                            except Exception as cb_err:
                                                logger.error(f"진행 상황 콜백 오류: {cb_err}")

                            # tools 키 안에 messages가 있는 경우 (도구 결과 - 사용자에게 직접 전달하지 않음)
                            elif (
                                "tools" in chunk
                                and isinstance(chunk["tools"], dict)
                                and "messages" in chunk["tools"]
                            ):
                                logger.info(
                                    f"🔧 도구 결과 청크 처리: {len(chunk['tools']['messages'])}개 메시지 (사용자에게 직접 전달하지 않음)"
                                )
                                # 도구 결과는 로깅만 하고 사용자에게 직접 전달하지 않음
                                for i, message in enumerate(chunk["tools"]["messages"]):
                                    logger.info(
                                        f"🔧 도구 결과 {i}: type={type(message)}, content={getattr(message, 'content', 'No content')[:100]}..."
                                    )

                                    # 도구 사용 추적
                                    if hasattr(message, "name") and message.name:
                                        tool_name = str(message.name)
                                        if tool_name not in used_tools:
                                            used_tools.append(tool_name)
                                            logger.info(f"🔧 도구 사용 기록: {tool_name}")
                                        # 메시지 content 저장 (JSON 문자열일 수 있음)
                                        if hasattr(message, "content") and message.content:
                                            tool_results[tool_name] = str(message.content)

                                            # --- 사용자에게 결과 수신 알림 ---
                                            try:
                                                if streaming_callback is not None:
                                                    streaming_callback(f"\n✅ '{tool_name}' 결과 수신 완료<br/>")
                                            except Exception as cb_err:
                                                logger.error(f"결과 수신 콜백 오류: {cb_err}")

                            # 다른 구조의 청크들
                            else:
                                logger.info(
                                    f"📦 다른 구조의 청크: {list(chunk.keys()) if isinstance(chunk, dict) else str(chunk)[:100]}"
                                )
                                # 에러 청크는 건너뛰기
                                if isinstance(chunk, dict) and "error" in chunk and "type" in chunk:
                                    logger.warning(
                                        f"⚠️ 에러 청크 건너뛰기: {str(chunk.get('error', ''))[:100]}..."
                                    )
                                    return

                                # 혹시 다른 구조로 AIMessage가 있는지 체크
                                if isinstance(chunk, dict):
                                    for key, value in chunk.items():
                                        if isinstance(value, dict) and "messages" in value:
                                            logger.info(
                                                f"📬 {key} 안에서 메시지 발견: {len(value['messages'])}개"
                                            )
                                            for i, message in enumerate(value["messages"]):
                                                # AIMessage만 처리
                                                if (
                                                    hasattr(message, "content")
                                                    and message.content
                                                    and str(type(message)).find("AIMessage") != -1
                                                ):
                                                    content = str(message.content)
                                                    accumulated_response += content
                                                    logger.info(
                                                        f"📝 {key} AI 컨텐츠 추가: {len(content)}자, 누적={len(accumulated_response)}자"
                                                    )
                                                    try:
                                                        if streaming_callback is not None:
                                                            streaming_callback(content)
                                                            logger.info(
                                                                f"✅ {key} AI 스트리밍 콜백 실행 성공"
                                                            )
                                                    except Exception as e:
                                                        logger.error(
                                                            f"❌ {key} AI 스트리밍 콜백 실행 오류: {e}"
                                                        )
                        else:
                            logger.info(
                                f"📦 dict가 아닌 청크: {type(chunk)} - {str(chunk)[:100]}..."
                            )

                    # astream_graph를 사용하여 스트리밍 실행
                    logger.info("🚀 astream_graph 실행 시작...")
                    chunk_count = 0
                    final_response_found = False

                    async for chunk_result in astream_graph(
                        self.react_agent, inputs, callback=streaming_wrapper, config=config
                    ):
                        chunk_count += 1
                        logger.info(f"📦 청크 {chunk_count} 완료: {type(chunk_result)}")

                        # 청크에서 최종 AI 응답 확인
                        if isinstance(chunk_result, dict):
                            # agent 키에서 AIMessage 확인
                            if (
                                "agent" in chunk_result
                                and isinstance(chunk_result["agent"], dict)
                                and "messages" in chunk_result["agent"]
                            ):
                                for message in chunk_result["agent"]["messages"]:
                                    if (
                                        hasattr(message, "content")
                                        and message.content
                                        and str(type(message)).find("AIMessage") != -1
                                    ):
                                        final_response_found = True
                                        logger.info(
                                            f"✅ 최종 AI 응답 발견: {len(str(message.content))}자"
                                        )
                                        break

                    logger.info(
                        f"✅ astream_graph 완료: {chunk_count}개 청크 처리, 최종응답={final_response_found}"
                    )

                    # 최종 응답이 없고 도구를 사용했다면 비스트리밍 모드로 재시도
                    if not final_response_found and len(used_tools) > 0:
                        logger.warning(
                            "⚠️ 도구 사용 후 최종 AI 응답이 없음 - 비스트리밍 모드로 재시도"
                        )
                        try:
                            # 새로운 thread_id로 비스트리밍 실행
                            fallback_thread_id = str(uuid.uuid4())
                            fallback_config = RunnableConfig(
                                recursion_limit=100, configurable={"thread_id": fallback_thread_id}
                            )

                            logger.info("🔄 비스트리밍 폴백 실행...")
                            result = await self.react_agent.ainvoke(inputs, config=fallback_config)

                            if "messages" in result:
                                for message in result["messages"]:
                                    if (
                                        hasattr(message, "content")
                                        and message.content
                                        and str(type(message)).find("AIMessage") != -1
                                    ):
                                        content = str(message.content)
                                        if content.strip() and content not in accumulated_response:
                                            accumulated_response += content
                                            logger.info(f"📝 폴백 AI 응답 추가: {len(content)}자")
                                            if streaming_callback is not None:
                                                streaming_callback(content)
                                            break
                        except Exception as e:
                            logger.error(f"❌ 비스트리밍 폴백 실행 실패: {e}")

                            # 도구 사용 후 AI 응답이 없으면 LLM으로 분석 시도
                            if len(used_tools) > 0 and not accumulated_response.strip():
                                logger.info("🔧 스트리밍: LLM 분석으로 폴백...")
                                try:
                                    analyzed_response = await self._analyze_tool_results_with_llm(
                                        user_message, used_tools, tool_results, streaming_callback
                                    )
                                    if analyzed_response and analyzed_response.strip():
                                        accumulated_response = analyzed_response
                                        logger.info(f"✅ 스트리밍 LLM 분석 완료: {len(analyzed_response)}자")
                                    else:
                                        # LLM 분석도 실패하면 포맷팅된 결과 사용
                                        formatted_response = self._format_tool_results(used_tools, tool_results)
                                        accumulated_response = formatted_response
                                        if streaming_callback is not None:
                                            streaming_callback(formatted_response)
                                        logger.info(f"✅ 스트리밍 포맷팅 폴백 완료: {len(formatted_response)}자")
                                except Exception as analysis_error:
                                    logger.error(f"❌ LLM 분석 실패: {analysis_error}")
                                    # 최종 폴백: 포맷팅된 결과 사용
                                    formatted_response = self._format_tool_results(used_tools, tool_results)
                                    accumulated_response = formatted_response
                                    if streaming_callback is not None:
                                        streaming_callback(formatted_response)
                                    logger.info(f"✅ 스트리밍 최종 폴백 완료: {len(formatted_response)}자")

                    # 도구를 사용하지 않았더라도 특정 키워드가 포함된 질문에서 응답이 없다면 폴백
                    elif not final_response_found and not accumulated_response.strip():
                        # 도구 결과가 있으면 포맷팅해서 사용
                        if tool_results:
                            logger.info("🔧 스트리밍: 일반 폴백에서 도구 결과 포맷팅")
                            accumulated_response = self._format_tool_results(used_tools, tool_results)
                            if streaming_callback is not None:
                                streaming_callback(accumulated_response)
                        else:
                            accumulated_response = "죄송합니다. 요청을 처리하는 중 문제가 발생했습니다."
                            if streaming_callback is not None:
                                streaming_callback(accumulated_response)
                except Exception as e:
                    logger.error(f"❌ 스트리밍 처리 중 오류: {e}")
                    import traceback

                    logger.error(f"❌ 스트리밍 처리 상세 오류: {traceback.format_exc()}")
                    return {
                        "response": f"ReAct 스트리밍 실행 중 오류: {str(e)}",
                        "used_tools": used_tools,
                    }

                logger.info(
                    f"✅ 스트리밍 완료: {len(accumulated_response)} 문자, {len(used_tools)}개 도구 사용"
                )

                return {"response": accumulated_response, "used_tools": used_tools}
            else:
                # 비스트리밍 모드
                logger.info("📞 비스트리밍 모드로 실행")
                try:
                    logger.info("🚀 ReAct ainvoke 시작...")
                    result = await self.react_agent.ainvoke(inputs, config=config)
                    logger.info(
                        f"✅ ReAct ainvoke 완료: type={type(result)}, keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}"
                    )
                except Exception as e:
                    logger.error(f"❌ ReAct ainvoke 실행 중 오류: {e}")
                    import traceback

                    logger.error(f"❌ ReAct ainvoke 오류 상세: {traceback.format_exc()}")
                    return {"response": f"ReAct ainvoke 실행 중 오류: {str(e)}", "used_tools": []}

                response_text = ""
                used_tools: List[str] = []
                tool_results: Dict[str, str] = {}

                if "messages" in result:
                    logger.info(f"📬 결과 메시지 수: {len(result['messages'])}")
                    ai_messages = []
                    tool_messages = []

                    # 메시지 분류
                    for i, message in enumerate(result["messages"]):
                        logger.info(
                            f"📨 결과 메시지 {i}: type={type(message)}, hasattr(content)={hasattr(message, 'content')}"
                        )

                        if str(type(message)).find("AIMessage") != -1:
                            ai_messages.append(message)
                            logger.info(
                                f"🤖 AI 메시지 발견: {len(str(getattr(message, 'content', '')))}자"
                            )
                        elif str(type(message)).find("ToolMessage") != -1:
                            tool_messages.append(message)
                            logger.info(
                                f"🔧 도구 메시지 발견: {getattr(message, 'name', 'unknown')}"
                            )
                            if (
                                hasattr(message, "name")
                                and message.name
                                and hasattr(message, "content")
                                and message.content
                            ):
                                tool_results[str(message.name)] = str(message.content)

                    # 도구 사용 추적
                    for tool_msg in tool_messages:
                        if hasattr(tool_msg, "name") and tool_msg.name:
                            tool_name = str(tool_msg.name)
                            if tool_name not in used_tools:
                                used_tools.append(tool_name)
                                logger.info(f"🔧 도구 사용 기록: {tool_name}")

                    # AI 메시지에서 최종 응답 추출 (마지막 AI 메시지 우선)
                    if ai_messages:
                        # 마지막 AI 메시지가 최종 응답일 가능성이 높음
                        for message in reversed(ai_messages):
                            if hasattr(message, "content") and message.content:
                                content = str(message.content).strip()
                                if content:
                                    response_text = content
                                    logger.info(f"📝 최종 AI 응답 선택: {len(content)}자")
                                    break

                    # 응답이 없고 도구를 사용했다면 재시도
                    if not response_text and used_tools:
                        logger.warning("⚠️ 도구 사용 후 AI 응답이 없음 - 새 세션으로 재시도")
                        try:
                            # 새로운 thread_id로 재시도
                            retry_thread_id = str(uuid.uuid4())
                            retry_config = RunnableConfig(
                                recursion_limit=100, configurable={"thread_id": retry_thread_id}
                            )

                            logger.info("🔄 새 세션으로 재시도...")
                            retry_result = await self.react_agent.ainvoke(
                                inputs, config=retry_config
                            )

                            if "messages" in retry_result:
                                for message in reversed(retry_result["messages"]):
                                    if (
                                        hasattr(message, "content")
                                        and message.content
                                        and str(type(message)).find("AIMessage") != -1
                                    ):
                                        content = str(message.content).strip()
                                        if content:
                                            response_text = content
                                            logger.info(f"📝 재시도 성공: {len(content)}자")
                                            break
                        except Exception as e:
                            logger.error(f"❌ 재시도 실패: {e}")

                    # 도구 사용 후 AI 응답이 없으면 LLM으로 분석 시도
                    if not response_text.strip() and len(used_tools) > 0:
                        logger.info("🔧 LLM 분석으로 폴백...")
                        try:
                            analyzed_response = await self._analyze_tool_results_with_llm(
                                user_message, used_tools, tool_results
                            )
                            if analyzed_response and analyzed_response.strip():
                                response_text = analyzed_response
                                logger.info(f"✅ LLM 분석 완료: {len(response_text)}자")
                            else:
                                # LLM 분석도 실패하면 포맷팅된 결과 사용
                                response_text = self._format_tool_results(used_tools, tool_results)
                                logger.info(f"✅ 포맷팅 폴백 완료: {len(response_text)}자")
                        except Exception as analysis_error:
                            logger.error(f"❌ LLM 분석 실패: {analysis_error}")
                            # 최종 폴백: 포맷팅된 결과 사용
                            response_text = self._format_tool_results(used_tools, tool_results)
                            logger.info(f"✅ 최종 폴백 완료: {len(response_text)}자")

                else:
                    logger.warning("❌ 결과에 'messages' 키가 없음")

                # -------------  새 후처리: 플레이스홀더 치환 -------------
                if response_text and tool_results:
                    processed = self._substitute_tool_placeholders(response_text, tool_results)
                    if processed != response_text:
                        logger.info("🔧 플레이스홀더 치환 완료")
                        response_text = processed

                logger.info(
                    f"✅ 비스트리밍 완료: {len(response_text)} 문자, {len(used_tools)}개 도구 사용"
                )

                return {"response": response_text, "used_tools": used_tools}

        except Exception as e:
            logger.error(f"❌ ReAct 에이전트 실행 최상위 오류: {e}")
            import traceback

            logger.error(f"❌ ReAct 에이전트 실행 최상위 상세 오류: {traceback.format_exc()}")
            return {
                "response": f"ReAct 에이전트 실행 중 최상위 오류가 발생했습니다: {str(e)}",
                "used_tools": [],
            }

    async def _generate_basic_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """기본 응답 생성"""
        try:
            logger.debug("기본 LLM 서비스를 통한 응답 생성 시작")
            messages = self.conversation_service.get_messages()
            response = await self.llm_service.generate_response(messages, streaming_callback)
            logger.debug(f"기본 응답 생성 완료: {len(response.response)} 문자")
            return response.response
        except Exception as e:
            logger.error(f"기본 응답 생성 중 오류: {e}")
            import traceback

            logger.error(f"기본 응답 생성 상세 오류: {traceback.format_exc()}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"

    def _get_llm_mode(self) -> str:
        """LLM 모드 반환"""
        mode = getattr(self.llm_config, "mode", "basic")
        if mode and isinstance(mode, str):
            return mode.lower()
        return "basic"

    def _create_response_data(
        self, response: str, reasoning: str = "", used_tools: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """응답 데이터 생성"""
        if used_tools is None:
            used_tools = []

        # 어시스턴트 메시지 추가
        self.add_assistant_message(response)

        return {"response": response, "reasoning": reasoning, "used_tools": used_tools}

    def _create_error_response(self, error_msg: str, detail: str = "") -> Dict[str, Any]:
        """에러 응답 생성"""
        response = f"죄송합니다. {error_msg}"
        self.add_assistant_message(response)

        return {"response": response, "reasoning": detail, "used_tools": []}

    def add_user_message(self, message: str) -> None:
        """사용자 메시지를 대화 히스토리에 추가"""
        self.conversation_service.add_user_message(message)
        # 하위 호환성
        self.history.append({"role": "user", "content": message})

    def add_assistant_message(self, message: str) -> None:
        """어시스턴트 메시지를 대화 히스토리에 추가"""
        self.conversation_service.add_assistant_message(message)
        # 하위 호환성
        self.history.append({"role": "assistant", "content": message})

    def clear_conversation(self) -> None:
        """대화 히스토리 초기화"""
        self.conversation_service.clear_conversation()
        # 하위 호환성
        self.history.clear()
        # 새 thread_id 생성
        self.thread_id = str(uuid.uuid4())
        logger.info("대화 히스토리 초기화")

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """대화 히스토리 반환"""
        messages = self.conversation_service.get_messages_as_dict()
        # 타입 변환 보장
        result: List[Dict[str, str]] = []
        for msg in messages:
            if isinstance(msg, dict):
                result.append(
                    {"role": str(msg.get("role", "")), "content": str(msg.get("content", ""))}
                )
        return result

    async def cleanup(self) -> None:
        """리소스 정리"""
        await self.llm_service.cleanup()
        if self.react_agent:
            self.react_agent = None
        logger.info("LLM 에이전트 정리 완료")

    def reinitialize_client(self) -> None:
        """클라이언트 재초기화 - 프로필 변경 시 사용"""
        try:
            logger.info("LLM 에이전트 클라이언트 재초기화 시작")

            # 설정 다시 로드
            self._load_config()

            # LLM 서비스 재초기화
            self.llm_service = LLMService(self.llm_config)

            # ReAct 에이전트 재초기화 필요
            self.react_agent = None

            # 대화 서비스 재초기화 (히스토리는 유지)
            # self.conversation_service는 그대로 유지하여 대화 맥락 보존

            logger.info(
                f"LLM 에이전트 재초기화 완료: 모델={self.llm_config.model}, 모드={self.llm_config.mode}"
            )

        except Exception as e:
            logger.error(f"LLM 에이전트 재초기화 실패: {e}")

    # 컨텍스트 매니저 지원
    async def __aenter__(self) -> "LLMAgent":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.cleanup()

    def _format_tool_results(self, used_tools: List[str], tool_results: Dict[str, str]) -> str:
        """도구 결과를 LLM이 분석할 수 있는 형태로 포맷팅 (범용적)"""
        try:
            # 프로세서 레지스트리를 사용하여 처리
            return self._get_processor_registry().process_tool_results(used_tools, tool_results)
        except Exception as e:
            logger.error(f"도구 결과 포맷팅 오류: {e}")
            return "도구 결과를 처리하는 중 오류가 발생했습니다."

    async def _analyze_tool_results_with_llm(
        self,
        user_message: str,
        used_tools: List[str],
        tool_results: Dict[str, str],
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """도구 결과를 LLM이 분석하여 사용자 요청에 맞는 응답 생성"""
        try:
            logger.info(f"🧠 LLM 분석 시작: {len(used_tools)}개 도구, {user_message[:50]}...")

            # 도구 결과를 분석용 프롬프트에 포함
            formatted_results = self._format_tool_results(used_tools, tool_results)
            
            analysis_prompt = f"""사용자 요청: {user_message}

다음 도구를 사용하여 정보를 수집했습니다:
{formatted_results}

위 정보를 바탕으로 사용자의 요청에 대해 종합적이고 유용한 답변을 제공해주세요:

1. **핵심 내용 정리**: 수집된 정보의 주요 포인트
2. **분석 및 해석**: 데이터에서 발견한 인사이트나 패턴
3. **맥락과 배경**: 필요시 추가 설명이나 연관성 제공
4. **출처 및 신뢰성**: 중요한 정보의 출처 명시

사용자가 이해하기 쉽고 실용적인 한국어 답변을 제공해주세요."""

            # 새로운 대화 컨텍스트로 LLM 호출
            from application.llm.models.conversation_message import ConversationMessage
            
            temp_messages = [
                ConversationMessage(role="user", content=analysis_prompt)
            ]
            
            logger.info(f"🔄 LLM 분석 요청: {len(analysis_prompt)}자 프롬프트")
            
            response = await self.llm_service.generate_response(temp_messages, streaming_callback)
            analysis_result = response.response.strip()
            
            if analysis_result:
                logger.info(f"✅ LLM 분석 성공: {len(analysis_result)}자")
                return analysis_result
            else:
                logger.warning("⚠️ LLM 분석 결과가 비어있음")
                return self._format_tool_results(used_tools, tool_results)
                
        except Exception as e:
            logger.error(f"❌ LLM 분석 중 오류: {e}")
            import traceback
            logger.error(f"❌ LLM 분석 상세 오류: {traceback.format_exc()}")
            # 오류 시 기본 포맷팅 반환
            return self._format_tool_results(used_tools, tool_results)

    def _substitute_tool_placeholders(self, text: str, tool_results: Dict[str, str]) -> str:
        """AI 응답 안의 `default_api.xxx()` 식 플레이스홀더를 실제 도구 결과로 치환"""
        import json
        import re

        out = str(text)
        for tool_name, raw in tool_results.items():
            try:
                data = json.loads(raw)
                result_str = data.get("result", raw)
            except Exception:
                result_str = raw

            # 백틱 포함 패턴 및 함수호출 패턴 치환
            patterns = [
                rf"`[^`]*{tool_name}\([^`]*`",  # `default_api.get_current_weather(...)`
                rf"{tool_name}\([^)]*\)",  # get_current_weather(...)
            ]
            for pat in patterns:
                out = re.sub(pat, result_str, out)

        return out

    def _get_processor_registry(self) -> ToolResultProcessorRegistry:
        """프로세서 레지스트리를 가져오거나 생성합니다 (지연 초기화)"""
        if self.processor_registry is None:
            self.processor_registry = ToolResultProcessorRegistry()
            # 검색 프로세서 등록
            self.processor_registry.register(SearchToolResultProcessor())
            logger.debug("도구 결과 프로세서 레지스트리 초기화 완료")
        return self.processor_registry
