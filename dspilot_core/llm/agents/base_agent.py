"""
BaseAgent 모듈
==============

`BaseAgent` 는 모든 DSPilot LLM 에이전트의 **공통 기능을 캡슐화**하는 추상
베이스 클래스입니다. 주요 책임은 다음과 같습니다.

1. **LLM 설정 로딩 & 검증**  
   `ConfigManager` 로부터 `LLMConfig` 딕셔너리를 받아 pydantic 모델로 마샬링
   후 `LLMConfigValidator` 로 체크.
2. **Service 초기화**  
   - `LLMService` : LangChain Chat API 호출 래퍼  
   - `ConversationService` : 사용자·시스템·assistant 메시지 스토리지
3. **Tool Result Processing**  
   `ToolProcessorMixin` 과 `ToolResultProcessorRegistry` 로 MCP 실행 결과를
   후처리 및 요약.
4. **Mode Dispatch**  
   `generate_response()` 에서 모드(basic / mcp_tools / workflow)에 따라
   별도 핸들러로 분기.
5. **ReAct Agent 지원**  
   LangGraph 기반 React agent를 초기화하여 *자율 도구 사용* 모드를 지원.

확장 가이드
-----------
• 커스텀 Agent 를 만들려면 본 클래스를 상속 후 `_handle_*_mode` 또는
  `generate_response` 를 오버라이드하세요.
• 믹스인 설계로 특정 기능(설정, 대화, 결과 처리)을 재정의하기 용이합니다.

Mermaid 흐름
------------
```mermaid
stateDiagram-v2
    [*] --> LoadConfig
    LoadConfig --> InitServices
    InitServices --> WaitQuery
    WaitQuery -->|generate_response| DispatchMode
    DispatchMode --> BasicFlow
    DispatchMode --> ToolFlow
    DispatchMode --> WorkflowFlow
    BasicFlow --> ReturnAnswer
    ToolFlow --> ReturnAnswer
    WorkflowFlow --> ReturnAnswer
    ReturnAnswer --> WaitQuery
```
"""

import json
import logging
import re
import uuid
from typing import Any, Callable, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from dspilot_core.llm.agents.mixins.config_mixin import ConfigMixin
from dspilot_core.llm.agents.mixins.conversation_mixin import ConversationMixin
from dspilot_core.llm.agents.mixins.tool_processor_mixin import ToolProcessorMixin
from dspilot_core.llm.interfaces.llm_interface import LLMInterface
from dspilot_core.llm.models.conversation_message import ConversationMessage
from dspilot_core.llm.models.llm_config import LLMConfig
from dspilot_core.llm.processors.base_processor import ToolResultProcessorRegistry
from dspilot_core.llm.processors.search_processor import SearchToolResultProcessor
from dspilot_core.llm.services.conversation_service import ConversationService
from dspilot_core.llm.services.llm_service import LLMService
from dspilot_core.llm.validators.config_validator import LLMConfigValidator
from dspilot_core.llm.workflow.workflow_utils import astream_graph
from dspilot_core.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class BaseAgent(ConfigMixin, ConversationMixin, ToolProcessorMixin, LLMInterface):
    """LLMAgent 의 공통 기능을 담당하는 베이스 클래스"""

    def __init__(self, config_manager: Any, mcp_tool_manager: Optional[Any] = None) -> None:
        self.config_manager = config_manager
        self.mcp_tool_manager = mcp_tool_manager

        # 설정 로드
        self._load_config()

        # 서비스 초기화
        self.llm_service = LLMService(self.llm_config)
        self.conversation_service = ConversationService()

        # 프로세서 레지스트리 (지연 초기화)
        self._processor_registry: Optional[ToolResultProcessorRegistry] = None

        # 히스토리 (하위 호환성 유지)
        self.history: List[Dict[str, str]] = []

        # 고유 스레드 ID
        self.thread_id = str(uuid.uuid4())

        # 하위 호환: 외부에서 직접 접근 가능한 _client 속성
        # 실제 ChatOpenAI 인스턴스는 llm_service 내부에 존재하지만, 일부 테스트에서
        # 이 속성의 존재 여부만을 확인하므로 기본값을 None 으로 둡니다.
        self._client = None  # pylint: disable=attribute-defined-outside-init

        # ReAct Agent 관련 속성 추가
        self.react_agent: Optional[Any] = None
        self.checkpointer: Optional[Any] = MemorySaver()

        logger.debug("BaseAgent 초기화 완료")

    # ---------------------------------------------------------------------
    # 설정 및 서비스 로드
    # ---------------------------------------------------------------------
    def _load_config(self) -> None:
        """config_manager 로부터 LLM 설정 로드"""
        try:
            cfg_dict = self.config_manager.get_llm_config()
            self.llm_config = LLMConfig.from_dict(cfg_dict)

            # 설정 검증 적용
            try:

                LLMConfigValidator.validate_config(self.llm_config)
                logger.debug(
                    "LLM 설정 로드 및 검증 완료: model=%s, mode=%s",
                    self.llm_config.model, self.llm_config.mode
                )
            except Exception as validation_exc:
                logger.warning("LLM 설정 검증 실패: %s", validation_exc)
                # 검증 실패해도 설정은 로드된 상태로 진행

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("LLM 설정 로드 실패: %s", exc)
            # 안전한 기본값
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

    # ---------------------------------------------------------------------
    # 외부 API (conversation)
    # ---------------------------------------------------------------------
    def add_user_message(self, message: str) -> None:
        self.conversation_service.add_user_message(message)
        self.history.append({"role": "user", "content": message})

    def add_assistant_message(self, message: str) -> None:
        self.conversation_service.add_assistant_message(message)
        self.history.append({"role": "assistant", "content": message})

    def clear_conversation(self) -> None:
        self.conversation_service.clear_conversation()
        self.history.clear()
        self.thread_id = str(uuid.uuid4())
        logger.info("대화 히스토리 초기화")

    def get_conversation_history(self) -> List[Dict[str, str]]:
        messages = self.conversation_service.get_messages_as_dict()
        history: List[Dict[str, str]] = []
        for msg in messages:
            if isinstance(msg, dict):
                history.append(
                    {"role": str(msg.get("role", "")),
                     "content": str(msg.get("content", ""))}
                )
        return history

    async def cleanup(self) -> None:  # noqa: D401
        await self.llm_service.cleanup()
        logger.debug("Agent 리소스 정리 완료")

    # ---------------------------------------------------------------------
    # 공통 헬퍼
    # ---------------------------------------------------------------------
    def _get_llm_mode(self) -> str:
        """LLM 동작 모드(basic/workflow/mcp_tools 등)를 반환.

        • `self.llm_config` 가 dataclass 또는 dict 모두 지원
        • config_manager.get_config_value("LLM","mode") 값이 존재하면 우선
        """

        # 1) config_manager 에 명시된 모드 우선
        try:
            if hasattr(self, "config_manager") and hasattr(self.config_manager, "get_config_value"):
                cfg_mode = self.config_manager.get_config_value(
                    "LLM", "mode", None)
                if cfg_mode:
                    return str(cfg_mode).lower()
        except Exception:  # pragma: no cover
            pass

        # 2) dataclass 객체
        if hasattr(self.llm_config, "mode"):
            cfg_mode = getattr(self.llm_config, "mode")
            if cfg_mode:
                return str(cfg_mode).lower()

        # 3) dict 형태
        if isinstance(self.llm_config, dict):
            cfg_mode = self.llm_config.get("mode")
            if cfg_mode:
                return str(cfg_mode).lower()

        return "basic"

    def _create_response_data(
        self,
        response: str,
        reasoning: str = "",
        used_tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if used_tools is None:
            used_tools = []
        self.add_assistant_message(response)
        return {"response": response, "reasoning": reasoning, "used_tools": used_tools}

    def _create_error_response(self, error_msg: str, detail: str = "") -> Dict[str, Any]:
        response = f"죄송합니다. {error_msg}"
        self.add_assistant_message(response)
        return {"response": response, "reasoning": detail, "used_tools": []}

    async def _generate_basic_response(
        self,
        message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """기본 LLM 응답 생성 (워크플로우에서 사용)"""
        try:
            # 메시지를 ConversationMessage로 변환
            messages = [
                ConversationMessage(role="user", content=message)
            ]

            # LLM 서비스를 통해 응답 생성
            response = await self.llm_service.generate_response(
                messages=messages,
                streaming_callback=streaming_callback
            )

            return response.response

        except Exception as e:
            logger.error(f"기본 응답 생성 실패: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"

    # ------------------------------------------------------------------
    # 도구 결과 처리 및 LLM 분석 (SearchTool 포함)
    # ------------------------------------------------------------------
    def _get_processor_registry(self) -> ToolResultProcessorRegistry:
        if self._processor_registry is None:
            self._processor_registry = ToolResultProcessorRegistry()
            self._processor_registry.register(SearchToolResultProcessor())
            logger.debug("도구 결과 프로세서 레지스트리 초기화 완료")
        return self._processor_registry

    def _format_tool_results(self, used_tools: List[str], tool_results: Dict[str, str]) -> str:
        try:
            return self._get_processor_registry().process_tool_results(used_tools, tool_results)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("도구 결과 포맷팅 오류: %s", exc)
            return "도구 결과를 처리하는 중 오류가 발생했습니다."

    async def _analyze_tool_results_with_llm(
        self,
        user_message: str,
        used_tools: List[str],
        tool_results: Dict[str, str],
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        try:
            logger.debug("LLM 분석 시작 (%d개 도구)", len(used_tools))

            # 도구 결과에 error 가 있는지 먼저 확인 --------------------------------
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
                # 여러 에러 메시지를 묶어 사용자에게 직접 전달
                msg = "\n".join(f"- {e}" for e in errors)
                logger.info("도구 결과에 error 발견 → 그대로 반환")
                return f"요청을 처리할 수 없습니다.\n도구 오류:\n{msg}"

            formatted_results = self._format_tool_results(
                used_tools, tool_results)

            # 다중 도구 결과 종합을 위한 개선된 프롬프트
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

            # 빈 프롬프트 방지
            if not analysis_prompt or not analysis_prompt.strip():
                logger.warning("분석 프롬프트가 비어있음")
                return formatted_results

            # ConversationMessage 객체 사용 (llm_service와 호환)
            temp_messages = [ConversationMessage(
                role="user", content=analysis_prompt)]
            response = await self.llm_service.generate_response(temp_messages, streaming_callback)

            # 응답 검증
            if not response or not hasattr(response, 'response'):
                logger.warning("LLM 응답 객체가 유효하지 않음")
                return formatted_results

            result = response.response.strip() if response.response else ""
            return result or formatted_results
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("LLM 분석 오류: %s", exc)
            return self._format_tool_results(used_tools, tool_results)

    def _substitute_tool_placeholders(self, text: str, tool_results: Dict[str, str]) -> str:

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

    # ------------------------------------------------------------------
    # LLM 모델 생성 (ReactAgent 등에서 사용)
    # ------------------------------------------------------------------
    def _create_llm_model(self) -> Optional[ChatOpenAI]:
        try:
            model_name = str(self.llm_config.model)
            openai_params: Dict[str, Any] = {
                "model": model_name,
                "temperature": float(self.llm_config.temperature),
            }
            if self.llm_config.api_key:
                openai_params["api_key"] = str(self.llm_config.api_key)
            if self.llm_config.base_url:
                openai_params["base_url"] = str(self.llm_config.base_url)
            if getattr(self.llm_config, "streaming", None) is not None:
                openai_params["streaming"] = bool(self.llm_config.streaming)

            # Gemini 모델에 대한 특별 처리
            if "gemini" in model_name.lower():
                # Gemini는 함수 호출 처리가 까다로우므로 더 안전한 설정 사용
                # OpenAI 호환 형식이므로 표준 파라미터만 사용
                openai_params["max_tokens"] = 2048
                openai_params["timeout"] = 120
                # 스트리밍 비활성화로 더 안정적인 처리
                openai_params["streaming"] = False
                logger.debug("Gemini 모델 특별 설정 적용 (함수 호출 안정화)")

            logger.debug(
                "ChatOpenAI 초기화 파라미터: %s",
                {k: v for k, v in openai_params.items() if k != "api_key"},
            )
            return ChatOpenAI(
                model=openai_params["model"],
                temperature=openai_params["temperature"],
                api_key=openai_params.get("api_key"),
                base_url=openai_params.get("base_url"),
                streaming=openai_params.get("streaming", True),
                timeout=openai_params.get("timeout", 60),
                max_retries=3,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("LLM 모델 생성 실패: %s", exc)
            return None

    # ------------------------------------------------------------------
    # ReAct Agent 기능 추가 ---------------------------------------------
    # ------------------------------------------------------------------
    async def _initialize_react_agent(self) -> bool:
        """langgraph의 create_react_agent를 사용해 에이전트 객체 생성"""
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

            prompt = self._get_react_system_prompt()
            self.react_agent = create_react_agent(
                llm, tools, checkpointer=self.checkpointer, prompt=prompt
            )
            logger.info("ReactAgent 초기화 완료 (도구 %d개)", len(tools))
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("ReactAgent 초기화 실패: %s", exc)
            return False

    def _get_react_system_prompt(self) -> str:
        """ReAct Agent용 시스템 프롬프트 반환"""
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

    async def run_react_agent(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """ReAct agent의 ainvoke/astream_graph 실행"""
        if self.react_agent is None:
            # 초기화 시도
            if not await self._initialize_react_agent():
                return {"response": "ReAct 에이전트를 초기화할 수 없습니다.", "used_tools": []}

        # 입력 검증
        if not user_message or not user_message.strip():
            logger.warning("빈 사용자 메시지")
            return {"response": "메시지를 입력해 주세요.", "used_tools": []}

        # thread_id 검증 및 기본값 설정
        thread_id = getattr(self, "thread_id", None) or "default-thread"
        if not isinstance(thread_id, str):
            thread_id = str(thread_id)

        try:
            config = RunnableConfig(recursion_limit=100, configurable={
                                    "thread_id": thread_id})

            # 메시지 내용 검증 및 정리
            clean_message = user_message.strip()
            if not clean_message:
                logger.warning("빈 메시지 내용")
                return {"response": "메시지를 입력해 주세요.", "used_tools": []}

            # Gemini 모델의 경우 더 엄격한 메시지 검증
            model_name = str(self.llm_config.model).lower()
            if "gemini" in model_name:
                # Gemini는 특정 문자나 형식에 민감하므로 추가 정리
                clean_message = clean_message.replace(
                    '\x00', '').replace('\n\n\n', '\n\n')
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
                            "그래프 스트리밍 오류 청크: %s", chunk.get(
                                "error", "Unknown error")
                        )
                        continue

                    # 간단 처리: AIMessage content만 뽑아 누적
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
                    "스트리밍 완료: accumulated=%d자, tools=%d개", len(
                        accumulated), len(used_tools)
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
                response_text = self._substitute_tool_placeholders(
                    response_text, tool_results)

            logger.debug(
                "비스트리밍 완료: response=%d자, tools=%d개", len(
                    response_text), len(used_tools)
            )
            # workflow_name 정의 (누락된 부분)
            workflow_name = "react_agent"
            result = self._create_response_data(response_text)
            result["workflow"] = str(workflow_name)
            return result
        except Exception as exc:
            logger.error("ReactAgent 비스트리밍 실행 중 오류: %s", exc)
            return {"response": f"ReAct 처리 중 오류 발생: {str(exc)}", "used_tools": []}

    # ------------------------------------------------------------------
    # 범용 자동 툴 라우팅 ---------------------------------------------------
    # ------------------------------------------------------------------
    async def auto_tool_flow(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Optional[Dict[str, Any]]:
        """LLM이 직접 도구를 선택하게 하는 범용적 접근 방식"""
        try:
            if self.mcp_tool_manager is None:
                return None

            logger.debug("범용 자동 라우팅: LLM이 적절한 도구를 직접 선택하도록 처리")

            # 사용 가능한 모든 도구 목록 가져오기
            langchain_tools = await self.mcp_tool_manager.get_langchain_tools()
            if not langchain_tools:
                logger.warning("사용 가능한 도구가 없습니다")
                return None

            # LLM이 직접 도구를 선택하고 실행하도록 위임
            llm = self._create_llm_model()
            if llm is None:
                return None

            # 도구 설명 포함한 프롬프트 생성
            tools_desc = "\n".join(
                [f"- {tool.name}: {tool.description}" for tool in langchain_tools])

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
                response_text = response.content if hasattr(
                    response, 'content') else str(response)

                # 마크다운 코드 블록 제거하고 JSON 추출

                # 마크다운 코드 블록을 찾아서 JSON 추출
                json_patterns = [
                    r'```(?:json)?\s*(\[[^\]]*\])\s*```',  # 마크다운 블록 내 JSON 배열
                    r'```(?:json)?\s*(\{[^`]*\})\s*```',   # 마크다운 블록 내 JSON 객체
                    # tool_name을 포함한 JSON 배열
                    r'(\[[^\]]*"tool_name"[^\]]*\])',
                    # tool_name을 포함한 JSON 객체
                    r'(\{[^{}]*"tool_name"[^{}]*\})',
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
                    json_text = response_text.strip()

                logger.debug("추출된 JSON 텍스트: %s", json_text)
                tool_selection = json.loads(json_text)

                # 배열 형식인 경우 여러 도구 순차 실행 지원
                tools_to_execute = []
                if isinstance(tool_selection, list):
                    if tool_selection:
                        logger.debug(
                            "배열 형식 도구 선택 감지: %d개 도구를 순차 실행합니다", len(tool_selection))
                        tools_to_execute = tool_selection
                    else:
                        logger.warning("빈 배열이 반환되었습니다")
                        return None
                else:
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

                    logger.debug("도구 %d/%d 실행: %s, 매개변수: %s", i+1,
                                 len(tools_to_execute), selected_tool, arguments)

                    try:
                        tool_result_raw = await self.mcp_tool_manager.call_mcp_tool(selected_tool, arguments)
                        tool_results[selected_tool] = tool_result_raw
                        used_tools.append(selected_tool)

                        if streaming_callback and len(tools_to_execute) > 1:
                            streaming_callback(
                                f"🔧 {selected_tool} 완료 ({i+1}/{len(tools_to_execute)})\n")

                    except Exception as tool_exc:
                        logger.error("도구 %s 실행 실패: %s",
                                     selected_tool, tool_exc)
                        tool_results[selected_tool] = json.dumps(
                            {"error": f"도구 실행 실패: {str(tool_exc)}"})
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
                # JSON 형식이 아닌 응답은 "도구 실행이 필요 없는 직접 답변" 으로 간주
                logger.debug("도구 선택 JSON 미검출 – 직접 응답 처리: %s", response_text[:100].replace("\n", " "))
                return {  # 기본 응답 데이터 구조와 맞추어 직접 반환
                    "response": response_text.strip(),
                    "reasoning": "도구 실행 불필요",
                    "used_tools": []
                }
            except Exception as inner_exc:
                logger.error("도구 선택/실행 중 오류: %s", inner_exc)
                return None

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("범용 자동 툴 라우팅 오류: %s", exc)
            return None

    # ------------------------------------------------------------------
    # 필수 추상 메서드 -----------------------------------------------------
    # ------------------------------------------------------------------
    async def generate_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        # 공용 진입점 – 모드에 따라 분기 처리

        # 1) 사용자 메시지 기록
        self.add_user_message(user_message)

        mode = self._get_llm_mode()

        try:
            if mode == "basic":
                result = await self._handle_basic_mode(user_message, streaming_callback)
            elif mode == "workflow":
                result = await self._handle_workflow_mode(user_message, streaming_callback)
            elif mode == "mcp_tools":
                result = await self._handle_mcp_tools_mode(user_message, streaming_callback)
            else:
                # 알 수 없는 모드 – basic 처리
                result = await self._handle_basic_mode(user_message, streaming_callback)

            # 결과가 None 이면 오류 처리
            if not result:
                return self._create_error_response("현재 응답을 생성할 수 없습니다.")

            return result

        except Exception as exc:  # pylint: disable=broad-except
            # 예외 발생 시 오류 응답 반환
            logger.error("generate_response 실패: %s", exc)
            return self._create_error_response("응답 생성 중 문제가 발생했습니다", str(exc))

    # 컨텍스트 매니저 지원 --------------------------------------------------
    async def __aenter__(self):  # noqa: D401
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):  # noqa: D401
        await self.cleanup()

    def reinitialize_client(self) -> None:
        """LLM 설정 변경 시 서비스 재초기화"""
        try:
            logger.info("BaseAgent 재초기화 시작")
            self._load_config()
            self.llm_service = LLMService(self.llm_config)
            logger.info(
                "BaseAgent 재초기화 완료: model=%s, mode=%s",
                self.llm_config.model,
                self.llm_config.mode,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("BaseAgent 재초기화 실패: %s", exc)

    # ------------------------------------------------------------------
    # 레거시 테스트 호환용 경량 래퍼 메서드들 ------------------------------
    # ------------------------------------------------------------------

    async def _handle_basic_mode(
        self,
        message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:  # noqa: D401
        """기본 모드 처리 – 기존 테스트 호환용."""

        response_text = await self._generate_basic_response(message, streaming_callback)
        return self._create_response_data(response_text)

    async def _handle_mcp_tools_mode(
        self,
        message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:  # noqa: D401
        """MCP 도구 모드 처리 – 최소 로직 (테스트 스텁)."""

        if not self.mcp_tool_manager:
            return self._create_error_response("MCP 도구 관리자가 설정되지 않았습니다")

        try:
            result = await self.mcp_tool_manager.run_agent_with_tools(message)
            # run_agent_with_tools 는 dict 반환 보장
            return {
                "response": result.get("response", ""),
                "reasoning": result.get("reasoning", ""),
                "used_tools": result.get("used_tools", []),
            }
        except Exception as exc:  # pragma: no cover
            return self._create_error_response("도구 실행 실패", str(exc))

    async def _handle_workflow_mode(
        self,
        message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:  # noqa: D401
        """워크플로우 모드 처리 – 기본 워크플로우 실행."""

        try:
            from dspilot_core.llm.workflow.workflow_utils import get_workflow

            workflow_name = getattr(
                self.llm_config, "workflow", None) or "basic"
            try:
                workflow_cls = get_workflow(workflow_name)
            except Exception:
                workflow_cls = get_workflow("basic")

            workflow = workflow_cls()
            response_text = await workflow.run(self, message, streaming_callback)
            result = self._create_response_data(response_text)
            result["workflow"] = str(workflow_name)
            return result

        except Exception as exc:  # pragma: no cover
            return self._create_error_response("워크플로우 처리 중 문제가 발생했습니다", str(exc))
