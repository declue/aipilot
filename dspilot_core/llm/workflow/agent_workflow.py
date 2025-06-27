"""
Interactive Agent Workflow
Cursor와 같은 AI agent 도구들의 워크플로우를 모방한 단계별 interactive workflow
사용자 피드백을 받으면서 단계적으로 작업을 진행
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from dspilot_core.llm.models.conversation_message import ConversationMessage
from dspilot_core.llm.models.llm_response import LLMResponse
from dspilot_core.llm.workflow.base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class AgentWorkflow(BaseWorkflow):
    """
    Cursor/Cline 스타일의 간단한 Agent Workflow
    - 간단한 요청: 바로 MCP 도구 사용하여 처리
    - 복잡한 요청: 대화형 단계별 처리
    """

    def __init__(self, llm_service=None, mcp_tool_manager=None):
        # BaseWorkflow 초기화 호출하지 않음 (추상 클래스이므로)
        self.llm_service = llm_service
        self.mcp_tool_manager = mcp_tool_manager
        self.workflow_name = "agent"
        self.interaction_mode = "collaborative"  # 협업 모드
        self.max_iterations = 10  # 최대 반복 횟수
        self.context_window = 20  # 유지할 컨텍스트 메시지 수
        self.conversation_history: List[Dict[str, str]] = []

    async def run(
        self,
        agent: "BaseAgent",
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """대화형 협업 워크플로우 실행"""
        logger.info("=== AgentWorkflow: 대화형 협업 처리 시작 ===")
        
        try:
            # 사용 가능한 도구 목록 확인
            available_tools = []
            if self.mcp_tool_manager and hasattr(self.mcp_tool_manager, 'get_langchain_tools'):
                try:
                    available_tools = await self.mcp_tool_manager.get_langchain_tools()
                except Exception as e:
                    logger.warning(f"도구 목록 가져오기 실패: {e}")
            
            # 도구 사용 필요성 판단 (LLM에게 물어보기)
            should_use_tools = await self._should_use_tools(user_message, available_tools)
            logger.info(f"도구 사용 필요성 판단: {should_use_tools}")
            
            if should_use_tools and available_tools:
                # MCP 도구 실행
                logger.info("MCP 도구 실행 시작")
                result = await self._handle_execution(agent, user_message, streaming_callback)
                logger.info(f"MCP 도구 실행 완료: {len(str(result))}자")
                return result
            else:
                # 일반 LLM 응답
                logger.info("일반 LLM 응답 생성")
                result = await self._generate_llm_response(agent, user_message, streaming_callback)
                logger.info(f"일반 LLM 응답 완료: {len(str(result))}자")
                return result
                
        except Exception as e:
            logger.error(f"AgentWorkflow 처리 중 오류: {e}")
            return f"워크플로우 처리 중 오류가 발생했습니다: {str(e)}"

    async def process(self, message: str, context: List[ConversationMessage] = None) -> LLMResponse:
        """
        대화형 Agent 처리 - 사용자와 자연스러운 대화하며 필요시 도구 사용
        
        Args:
            message: 사용자 메시지
            context: 이전 대화 컨텍스트
            
        Returns:
            LLMResponse: 처리 결과
        """
        logger.info(f"=== AgentWorkflow.process: 처리 시작 - '{message}' ===")
        
        try:
            # 1. 컨텍스트 준비
            working_context = self._prepare_context(context)
            
            # 2. 사용자 메시지 추가
            user_message = ConversationMessage(role="user", content=message)
            working_context.append(user_message)
            
            # 3. 응답 생성 - 직접 처리
            logger.info("=== AgentWorkflow: 응답 생성 시작 ===")
            response = await self._generate_response(working_context)
            
            logger.info(f"=== AgentWorkflow.process: 처리 완료 ===")
            return response
            
        except Exception as e:
            logger.error(f"AgentWorkflow.process 처리 중 오류: {e}")
            return LLMResponse(
                response=f"처리 중 오류가 발생했습니다: {str(e)}",
                metadata={"error": str(e), "workflow": self.workflow_name}
            )

    def _prepare_context(self, context: List[ConversationMessage] = None) -> List[ConversationMessage]:
        """컨텍스트 준비 및 정리"""
        if not context:
            return []
        
        # 컨텍스트 윈도우 적용
        if len(context) > self.context_window:
            return context[-self.context_window:]
        
        return context.copy()

    async def _generate_response(self, context: List[ConversationMessage]) -> LLMResponse:
        """응답 생성 - 필요시 도구 사용"""
        try:
            # llm_service 유효성 검사
            if not self.llm_service:
                logger.error("llm_service가 초기화되지 않았습니다")
                return LLMResponse(
                    response="LLM 서비스가 초기화되지 않았습니다.",
                    metadata={"error": "llm_service_not_initialized", "workflow": self.workflow_name}
                )
            
            # 기본 LLM 응답 시도
            logger.info("=== AgentWorkflow: 기본 LLM 응답 생성 ===")
            response = await self.llm_service.generate_response(context)
            
            # MCP 도구가 사용 가능한 경우 도구 사용 가능성 확인
            if self.mcp_tool_manager and hasattr(self.mcp_tool_manager, 'get_langchain_tools'):
                logger.info("=== AgentWorkflow: MCP 도구 사용 가능성 확인 ===")
                
                try:
                    available_tools = await self.mcp_tool_manager.get_langchain_tools()
                    user_message = context[-1].content if context else ""
                    
                    # LLM에게 도구 사용 필요성 판단 요청
                    should_use_tools = await self._should_use_tools(user_message, available_tools)
                    
                    if should_use_tools and available_tools:
                        logger.info("=== AgentWorkflow: 도구 사용 필요 판단, BaseAgent의 ReAct 기능 호출 ===")
                        
                        # BaseAgent의 ReAct 기능 사용
                        if hasattr(self.llm_service, 'agent') and hasattr(self.llm_service.agent, 'run_react_agent'):
                            tool_response = await self.llm_service.agent.run_react_agent(user_message)
                            if tool_response and "response" in tool_response:
                                # 도구 사용 결과를 반영
                                return LLMResponse(
                                    response=tool_response["response"],
                                    metadata={
                                        "workflow": self.workflow_name,
                                        "used_tools": tool_response.get("used_tools", []),
                                        "tool_execution": True
                                    }
                                )
                except Exception as e:
                    logger.warning(f"도구 사용 가능성 확인 중 오류: {e}")
            
            return LLMResponse(
                response=response.response,
                metadata={
                    "workflow": self.workflow_name,
                    "tool_execution": False
                }
            )
            
        except Exception as e:
            logger.error(f"응답 생성 중 오류: {e}")
            return LLMResponse(
                response="죄송합니다. 응답 생성 중 오류가 발생했습니다.",
                metadata={"error": str(e), "workflow": self.workflow_name}
            )

    async def _should_use_tools(self, user_message: str, available_tools: List[Any] = None) -> bool:
        """LLM에게 도구 사용 필요성을 물어보는 범용적 접근"""
        
        # 사용 가능한 도구가 없으면 도구 사용 불가
        if not available_tools:
            return False
        
        # 도구 목록 생성
        tools_desc = "\n".join([
            f"- {tool.name}: {tool.description}" 
            for tool in available_tools
        ])
        
        # LLM에게 도구 사용 필요성 판단 요청
        analysis_prompt = f"""다음 사용자 요청을 분석하여 외부 도구 사용이 필요한지 판단해주세요.

사용자 요청: {user_message}

사용 가능한 도구들:
{tools_desc}

다음 기준으로 판단하세요:
1. 현재 시간/날짜, 날씨, 검색 등 실시간 정보가 필요한지
2. 파일 읽기/쓰기, 계산, 외부 API 호출이 필요한지
3. 단순한 대화나 일반적인 지식으로 답변 가능한지

**응답 형식 (JSON만):**
{{
    "need_tools": true/false,
    "reason": "판단 이유"
}}

반드시 JSON 형식으로만 응답하세요."""

        try:
            if self.llm_service:
                
                context = [ConversationMessage(role="user", content=analysis_prompt)]
                response = await self.llm_service.generate_response(context)
                
                # JSON 파싱
                import json
                response_text = response.response
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}") + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = response_text[start_idx:end_idx]
                    result = json.loads(json_str)
                    need_tools = result.get("need_tools", False)
                    reason = result.get("reason", "판단 실패")
                    logger.info(f"LLM 도구 사용 판단: {need_tools} - {reason}")
                    return need_tools
                    
        except Exception as e:
            logger.warning(f"LLM 도구 사용 판단 실패: {e}")
        
        # 폴백: 보수적 접근 (도구 사용 안함)
        return False

    async def _handle_execution(
        self,
        agent: "BaseAgent", 
        user_message: str, 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """MCP 도구를 사용한 실행 처리"""
        logger.info("=== MCP 도구 실행 시작 ===")
        
        try:
            # BaseAgent의 auto_tool_flow 사용
            if hasattr(agent, 'auto_tool_flow'):
                result = await agent.auto_tool_flow(user_message, streaming_callback)
                if result:
                    return result.get("response", "도구 실행 완료")
            
            # 폴백: 일반 LLM 응답
            return await self._generate_llm_response(agent, user_message, streaming_callback)
            
        except Exception as e:
            logger.error(f"MCP 도구 실행 중 오류: {e}")
            return f"도구 실행 중 오류가 발생했습니다: {str(e)}"

    async def _generate_llm_response(
        self,
        agent: "BaseAgent",
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """일반 LLM 응답 생성"""
        logger.info("=== 일반 LLM 응답 생성 ===")
        
        try:
            if self.llm_service:
                context = [ConversationMessage(role="user", content=user_message)]
                response = await self.llm_service.generate_response(context, streaming_callback)
                return response.response if hasattr(response, 'response') else str(response)
            elif hasattr(agent, '_generate_basic_response'):
                return await agent._generate_basic_response(user_message, streaming_callback)
            else:
                return "죄송합니다. 응답을 생성할 수 없습니다."
                
        except Exception as e:
            logger.error(f"LLM 응답 생성 중 오류: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"

    def get_workflow_info(self) -> Dict[str, Any]:
        """워크플로우 정보 반환"""
        return {
            "name": self.workflow_name,
            "description": "대화형 Agent 워크플로우 - 사용자와 AI 간의 자연스러운 대화 및 협업",
            "mode": self.interaction_mode,
            "max_iterations": self.max_iterations,
            "context_window": self.context_window,
            "supports_tools": True,
            "supports_streaming": True  # 스트리밍 지원 표시
        } 