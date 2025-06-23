"""
Langchain 기반 LLM 에이전트
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from application.llm.interfaces.llm_interface import LLMInterface
from application.llm.models.llm_config import LLMConfig
from application.llm.services.conversation_service import ConversationService
from application.llm.services.llm_service import LLMService
from application.llm.workflow.workflow_utils import get_workflow
from application.util.logger import setup_logger

logger = setup_logger("llm_agent") or logging.getLogger("llm_agent")


class LLMAgent(LLMInterface):
    """Langchain 기반 LLM 에이전트"""

    def __init__(self, config_manager, mcp_tool_manager=None):
        """
        LLM 에이전트 초기화
        
        Args:
            config_manager: 설정 관리자
            mcp_tool_manager: MCP 도구 관리자 (선택사항)
        """
        self.config_manager = config_manager
        self.mcp_tool_manager = mcp_tool_manager
        
        # 설정 로드
        self._load_config()
        
        # 서비스 초기화
        self.llm_service = LLMService(self.llm_config)
        self.conversation_service = ConversationService()
        
        # 히스토리 (하위 호환성)
        self.history = []
        
        logger.info("LLM 에이전트 초기화 완료")

    def _load_config(self) -> None:
        """설정 로드"""
        try:
            # 프로필 기반 설정 로드 (mode와 workflow 포함)
            llm_config_dict = self.config_manager.get_llm_config()
            
            self.llm_config = LLMConfig.from_dict(llm_config_dict)
            logger.debug(f"LLM 설정 로드 완료: {self.llm_config.model}, 모드: {self.llm_config.mode}")
            
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            # 기본 설정으로 폴백
            self.llm_config = LLMConfig(
                api_key="",
                model="gpt-3.5-turbo",
                mode="basic"
            )

    async def generate_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        사용자 메시지에 대한 응답 생성
        
        Args:
            user_message: 사용자 입력 메시지
            streaming_callback: 스트리밍 콜백 함수
            
        Returns:
            Dict[str, Any]: 응답 데이터
        """
        try:
            logger.info(f"LLM 응답 생성 시작: {user_message[:50]}...")
            
            # 사용자 메시지 추가
            self.add_user_message(user_message)
            
            # 모드에 따른 처리
            mode = self._get_llm_mode()
            
            if mode == "workflow":
                return await self._handle_workflow_mode(user_message, streaming_callback)
            elif mode == "mcp_tools" and self.mcp_tool_manager:
                return await self._handle_mcp_tools_mode(user_message, streaming_callback)
            else:
                return await self._handle_basic_mode(user_message, streaming_callback)
                
        except Exception as e:
            logger.error(f"응답 생성 중 오류: {e}")
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
            response = await self._generate_basic_response(user_message, streaming_callback)
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
                "used_tools": []
            }
            
        except Exception as e:
            logger.error(f"워크플로우 모드 처리 중 오류: {e}")
            return {
                "response": "워크플로우 처리 중 문제가 발생했습니다.",
                "workflow": self.llm_config.workflow or "basic_chat",
                "reasoning": str(e),
                "used_tools": []
            }

    async def _handle_mcp_tools_mode(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """MCP 도구 모드 처리 - Langchain Agent 패턴 사용"""
        try:
            if not self.mcp_tool_manager:
                return self._create_error_response("MCP 도구 관리자가 설정되지 않았습니다")
            
            # Langchain Agent를 사용한 도구 기반 응답 생성
            result = await self._run_langchain_agent_with_tools(user_message, streaming_callback)
            
            return {
                "response": result.get("response", ""),
                "reasoning": result.get("reasoning", ""),
                "used_tools": result.get("used_tools", [])
            }
            
        except Exception as e:
            logger.error(f"MCP 도구 모드 처리 중 오류: {e}")
            return self._create_error_response("MCP 도구 모드 처리 중 오류가 발생했습니다", str(e))

    async def _run_langchain_agent_with_tools(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """진정한 Langchain MCP Agent를 사용한 도구 기반 응답 생성"""
        # JSON 스키마 이슈로 인해 일시적으로 간단한 방식 사용
        logger.info("🔧 Langchain Agent JSON 스키마 이슈로 인해 간단한 MCP 방식 사용")
        return await self._fallback_to_simple_mcp_approach(user_message, streaming_callback)

    async def _fallback_to_simple_mcp_approach(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """간단한 MCP 접근법으로 폴백"""
        try:
            # 사용자 메시지에서 필요한 도구 파악 및 실행
            tool_results = await self._execute_relevant_tools(user_message)
            
            # 도구 결과를 포함한 프롬프트로 LLM에게 최종 답변 요청
            if tool_results["used_tools"]:
                enhanced_prompt = self._create_enhanced_prompt_with_tools(user_message, tool_results)
                final_response = await self._generate_basic_response(enhanced_prompt, streaming_callback)
                
                return {
                    "response": final_response,
                    "reasoning": "Simple MCP approach with tool results",
                    "used_tools": tool_results["used_tools"]
                }
            else:
                return await self._fallback_to_basic_response(user_message, streaming_callback)
            
        except Exception as e:
            logger.error(f"Simple MCP approach 실패: {e}")
            return await self._fallback_to_basic_response(user_message, streaming_callback)

    async def _execute_relevant_tools(self, user_message: str) -> Dict[str, Any]:
        """사용자 메시지에서 관련 도구 실행"""
        try:
            # Langchain 도구 가져오기
            langchain_tools = await self.mcp_tool_manager.get_langchain_tools()
            
            if not langchain_tools:
                logger.warning("사용 가능한 MCP 도구가 없습니다")
                return {"response": "", "reasoning": "사용 가능한 도구 없음", "used_tools": []}
            
            logger.info(f"🔍 도구 실행 분석: '{user_message}' -> {len(langchain_tools)}개 도구 사용 가능")
            
            # 간단한 키워드 기반 도구 실행
            message_lower = user_message.lower()
            used_tools = []
            responses = []
            
            # 시간 관련 요청
            time_keywords = ["시간", "time", "현재", "지금"]
            time_match = any(keyword in message_lower for keyword in time_keywords)
            logger.info(f"🕐 시간 키워드 매칭: {time_match} (키워드: {time_keywords})")
            
            if time_match:
                logger.info("🕐 시간 관련 도구 검색 중...")
                for tool in langchain_tools:
                    logger.debug(f"  - 도구 확인: {tool.name}")
                    if "time" in tool.name.lower() and "current" in tool.name.lower():
                        try:
                            logger.info(f"🔧 시간 도구 실행: {tool.name}")
                            result = await tool.ainvoke({})
                            logger.info(f"✅ 시간 도구 결과: {result}")
                            responses.append(str(result))
                            used_tools.append(tool.name)
                            break
                        except Exception as e:
                            logger.error(f"❌ 도구 {tool.name} 실행 실패: {e}")
            
            # 날씨 관련 요청
            weather_keywords = ["날씨", "weather", "기온", "온도"]
            weather_match = any(keyword in message_lower for keyword in weather_keywords)
            logger.info(f"🌤️ 날씨 키워드 매칭: {weather_match} (키워드: {weather_keywords})")
            
            if weather_match:
                city = "Seoul"  # 기본값
                # 도시명 추출 (간단한 방식)
                for word in user_message.split():
                    if word in ["서울", "Seoul", "부산", "Busan", "도쿄", "Tokyo"]:
                        city = word
                        break
                
                logger.info(f"🌤️ 날씨 관련 도구 검색 중... (도시: {city})")
                for tool in langchain_tools:
                    logger.debug(f"  - 도구 확인: {tool.name}")
                    if "weather" in tool.name.lower() and "current" in tool.name.lower():
                        try:
                            logger.info(f"🔧 날씨 도구 실행: {tool.name} (city={city})")
                            result = await tool.ainvoke({"city": city})
                            logger.info(f"✅ 날씨 도구 결과: {result}")
                            responses.append(str(result))
                            used_tools.append(tool.name)
                            break
                        except Exception as e:
                            logger.error(f"❌ 도구 {tool.name} 실행 실패: {e}")
            
            if responses:
                logger.info(f"✅ 도구 실행 완료: {len(used_tools)}개 도구 사용")
                return {
                    "response": "\n\n".join(responses),
                    "reasoning": f"도구 {len(used_tools)}개 실행",
                    "used_tools": used_tools
                }
            else:
                logger.warning("⚠️ 실행된 도구가 없습니다")
                return {
                    "response": "",
                    "reasoning": "실행할 도구 없음",
                    "used_tools": []
                }
                
        except Exception as e:
            logger.error(f"❌ 관련 도구 실행 실패: {e}")
            return {"response": "", "reasoning": str(e), "used_tools": []}

    def _create_enhanced_prompt_with_tools(self, user_message: str, tool_results: Dict[str, Any]) -> str:
        """도구 결과를 포함한 향상된 프롬프트 생성"""
        tool_info = ""
        if tool_results.get("used_tools"):
            tool_info = f"\n\n도구 실행 결과:\n{tool_results.get('response', '')}\n"
        
        enhanced_prompt = f"""사용자 질문: {user_message}
{tool_info}
위의 도구 실행 결과를 바탕으로 사용자의 질문에 대해 정확하고 유용한 답변을 제공해주세요.

특별 요청사항:
- 시간 관련 질문의 경우: 시간 계산, 포맷팅, 추가적인 정보 제공
- 날씨 관련 질문의 경우: 표 형태나 구조화된 형태로 정보 정리
- 복합 질문의 경우: 여러 정보를 종합하여 완전한 답변 제공

항상 한국어로 친절하고 자세하게 답변해주세요."""

        return enhanced_prompt

    async def _fallback_to_basic_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """도구가 없을 때 기본 응답으로 폴백"""
        try:
            response = await self._generate_basic_response(user_message, streaming_callback)
            return {
                "response": response,
                "reasoning": "도구 없이 기본 응답 생성",
                "used_tools": []
            }
        except Exception as e:
            logger.error(f"기본 응답 폴백 실패: {e}")
            return {
                "response": "죄송합니다. 응답 생성 중 문제가 발생했습니다.",
                "reasoning": str(e),
                "used_tools": []
            }

    async def _fallback_to_mcp_tools(self, user_message: str) -> Dict[str, Any]:
        """Langchain Agent 실패 시 기본 MCP 도구 사용으로 폴백"""
        try:
            result = await self.mcp_tool_manager.run_agent_with_tools(user_message)
            return {
                "response": result.get("response", ""),
                "reasoning": "Langchain Agent 실패로 기본 MCP 도구 사용",
                "used_tools": result.get("used_tools", [])
            }
        except Exception as e:
            logger.error(f"MCP 도구 폴백도 실패: {e}")
            return {
                "response": "죄송합니다. 도구 사용 중 문제가 발생했습니다.",
                "reasoning": str(e),
                "used_tools": []
            }

    async def _generate_basic_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """기본 응답 생성"""
        try:
            messages = self.conversation_service.get_messages()
            response = await self.llm_service.generate_response(messages, streaming_callback)
            return response.response
        except Exception as e:
            logger.error(f"기본 응답 생성 중 오류: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"

    def _get_llm_mode(self) -> str:
        """LLM 모드 반환"""
        mode = self.llm_config.mode
        if mode and isinstance(mode, str):
            return mode.lower()
        return "basic"

    def _create_response_data(
        self,
        response: str,
        reasoning: str = "",
        used_tools: List[str] = None
    ) -> Dict[str, Any]:
        """응답 데이터 생성"""
        if used_tools is None:
            used_tools = []
            
        # 어시스턴트 메시지 추가
        self.add_assistant_message(response)
        
        return {
            "response": response,
            "reasoning": reasoning,
            "used_tools": used_tools
        }

    def _create_error_response(self, error_msg: str, detail: str = "") -> Dict[str, Any]:
        """에러 응답 생성"""
        response = f"죄송합니다. {error_msg}"
        self.add_assistant_message(response)
        
        return {
            "response": response,
            "reasoning": detail,
            "used_tools": []
        }

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
        logger.info("대화 히스토리 초기화")

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """대화 히스토리 반환"""
        return self.conversation_service.get_messages_as_dict()

    async def cleanup(self) -> None:
        """리소스 정리"""
        await self.llm_service.cleanup()
        logger.info("LLM 에이전트 정리 완료")

    def reinitialize_client(self) -> None:
        """클라이언트 재초기화 - 프로필 변경 시 사용"""
        try:
            logger.info("LLM 에이전트 클라이언트 재초기화 시작")
            
            # 설정 다시 로드
            self._load_config()
            
            # LLM 서비스 재초기화
            self.llm_service = LLMService(self.llm_config)
            
            # 대화 서비스 재초기화 (히스토리는 유지)
            # self.conversation_service는 그대로 유지하여 대화 맥락 보존
            
            logger.info(f"LLM 에이전트 재초기화 완료: 모델={self.llm_config.model}, 모드={self.llm_config.mode}")
            
        except Exception as e:
            logger.error(f"LLM 에이전트 재초기화 실패: {e}")

    # 컨텍스트 매니저 지원
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup() 