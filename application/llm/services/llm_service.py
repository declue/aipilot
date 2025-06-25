"""
Langchain 기반 LLM 서비스
"""

import logging
from typing import Callable, List, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from application.llm.models.conversation_message import ConversationMessage
from application.llm.models.llm_config import LLMConfig
from application.llm.models.llm_response import LLMResponse
from application.util.logger import setup_logger

logger = setup_logger("llm_service") or logging.getLogger("llm_service")


class StreamingCallbackHandler(BaseCallbackHandler):
    """스트리밍 콜백 핸들러"""

    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self.callback = callback

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """새 토큰이 생성될 때 호출"""
        if self.callback:
            self.callback(token)


class LLMService:
    """Langchain 기반 LLM 서비스"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._llm: Optional[ChatOpenAI] = None
        self._initialize_llm()

    def _initialize_llm(self) -> None:
        """LLM 초기화"""
        try:
            self._llm = ChatOpenAI(
                model=self.config.model,
                openai_api_key=self.config.api_key,
                openai_api_base=self.config.base_url,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                streaming=self.config.streaming,
            )
            logger.info(f"LLM 초기화 완료: {self.config.model}")
        except Exception as e:
            logger.error(f"LLM 초기화 실패: {e}")
            raise

    async def generate_response(
        self,
        messages: List[ConversationMessage],
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse:
        """
        메시지 리스트로부터 응답 생성

        Args:
            messages: 대화 메시지 리스트
            streaming_callback: 스트리밍 콜백 함수

        Returns:
            LLMResponse: 생성된 응답
        """
        try:
            if not self._llm:
                raise ValueError("LLM이 초기화되지 않았습니다")

            # ConversationMessage를 Langchain 메시지로 변환
            langchain_messages = self._convert_to_langchain_messages(messages)

            if self.config.streaming and streaming_callback:
                # 스트리밍 모드
                response_content = ""
                callback_handler = StreamingCallbackHandler(streaming_callback)

                async for chunk in self._llm.astream(
                    langchain_messages, config={"callbacks": [callback_handler]}
                ):
                    if hasattr(chunk, "content"):
                        response_content += chunk.content

                return LLMResponse(response=response_content, reasoning="", used_tools=[])
            else:
                # 일반 모드
                result = await self._llm.ainvoke(langchain_messages)
                return LLMResponse(response=result.content, reasoning="", used_tools=[])

        except Exception as e:
            logger.error(f"응답 생성 중 오류: {e}")
            return LLMResponse(
                response=f"응답 생성 중 오류가 발생했습니다: {str(e)}",
                reasoning=str(e),
                used_tools=[],
            )

    def _convert_to_langchain_messages(self, messages: List[ConversationMessage]) -> List:
        """ConversationMessage를 Langchain 메시지로 변환"""
        langchain_messages = []

        for msg in messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))

        return langchain_messages

    def update_config(self, config: LLMConfig) -> None:
        """설정 업데이트"""
        self.config = config
        self._initialize_llm()

    async def cleanup(self) -> None:
        """리소스 정리"""
        self._llm = None
        logger.info("LLM 서비스 정리 완료")
