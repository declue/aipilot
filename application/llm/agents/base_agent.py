import logging
import uuid
from typing import Any, Callable, Dict, List, Optional

from langchain_openai import ChatOpenAI

from application.llm.interfaces.llm_interface import LLMInterface
from application.llm.models.conversation_message import ConversationMessage
from application.llm.models.llm_config import LLMConfig
from application.llm.processors.base_processor import ToolResultProcessorRegistry
from application.llm.processors.search_processor import SearchToolResultProcessor
from application.llm.services.conversation_service import ConversationService
from application.llm.services.llm_service import LLMService
from application.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class BaseAgent(LLMInterface):
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
                from application.llm.validators.config_validator import LLMConfigValidator
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
                    {"role": str(msg.get("role", "")), "content": str(msg.get("content", ""))}
                )
        return history

    async def cleanup(self) -> None:  # noqa: D401
        await self.llm_service.cleanup()
        logger.info("Agent 리소스 정리 완료")

    # ---------------------------------------------------------------------
    # 공통 헬퍼
    # ---------------------------------------------------------------------
    def _get_llm_mode(self) -> str:
        mode = getattr(self.llm_config, "mode", "basic")
        return mode.lower() if isinstance(mode, str) else "basic"

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
            logger.info("LLM 분석 시작 (%d개 도구)", len(used_tools))

            # 도구 결과에 error 가 있는지 먼저 확인 --------------------------------
            errors: List[str] = []
            import json

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

            formatted_results = self._format_tool_results(used_tools, tool_results)

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
            temp_messages = [ConversationMessage(role="user", content=analysis_prompt)]
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
        import json
        import re

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
    # 필수 추상 메서드 -----------------------------------------------------
    # ------------------------------------------------------------------
    async def generate_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError()  # pragma: no cover

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
