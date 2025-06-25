import logging
from typing import Any, Callable, Dict, List, Optional

from langchain_openai import ChatOpenAI

from application.llm.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class BasicAgent(BaseAgent):
    """기본 모드 Agent - 단순한 LLM 응답만 제공"""

    async def generate_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """기본 모드로 응답 생성"""
        try:
            logger.info("BasicAgent: 기본 모드로 응답 생성 중...")
            
            # 사용자 메시지 추가
            self.add_user_message(user_message)
            
            # 기본 응답 생성
            response = await self._generate_basic_response(user_message, streaming_callback)
            
            return self._create_response_data(response)
        except Exception as e:
            logger.error(f"BasicAgent 응답 생성 중 오류: {e}")
            return self._create_error_response("기본 모드 처리 중 오류가 발생했습니다", str(e))
    
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
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"

    @staticmethod
    async def test_connection(api_key: str, base_url: Optional[str], model: str) -> Dict[str, Any]:
        """API 연결 테스트"""
        try:
            # ChatOpenAI 인스턴스 생성
            llm_kwargs = {
                "api_key": api_key,
                "model": model,
                "temperature": 0.1,
                "max_tokens": 10,
            }
            if base_url:
                llm_kwargs["base_url"] = base_url

            llm = ChatOpenAI(**llm_kwargs)

            # 간단한 테스트 메시지 전송
            from langchain_core.messages import HumanMessage
            response = await llm.ainvoke([HumanMessage(content="Hi")])

            return {
                "success": True,
                "message": "연결 성공",
                "response": response.content[:50] if response.content else "",
            }
        except Exception as e:
            return {"success": False, "message": f"연결 실패: {str(e)}", "response": ""}

    @staticmethod
    async def get_available_models(api_key: str, base_url: Optional[str]) -> List[str]:
        """사용 가능한 모델 목록 조회"""
        try:
            # 기본 모델 목록 반환 (OpenAI 호환)
            default_models = [
                "gpt-4o-mini",
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
            ]
            
            # 특정 base_url에 따른 추가 모델들
            if base_url and "ollama" in base_url.lower():
                # Ollama 모델들 추가
                ollama_models = [
                    "llama2",
                    "llama2:13b", 
                    "codellama",
                    "mistral",
                    "mixtral",
                ]
                return ollama_models + default_models
            elif base_url and "anthropic" in base_url.lower():
                # Claude 모델들
                claude_models = [
                    "claude-3-5-sonnet-20241022",
                    "claude-3-opus-20240229",
                    "claude-3-haiku-20240307",
                ]
                return claude_models + default_models
            else:
                return default_models
        except Exception as e:
            logger.error(f"모델 목록 조회 실패: {e}")
            return ["gpt-4o-mini", "gpt-3.5-turbo"]  # 최소한의 기본 모델 