"""
기본 채팅 워크플로우
"""

import logging
from typing import Any, Callable, Optional

from application.llm.workflow.base_workflow import BaseWorkflow
from application.util.logger import setup_logger

logger = setup_logger("basic_chat_workflow") or logging.getLogger("basic_chat_workflow")


class BasicChatWorkflow(BaseWorkflow):
    """기본 채팅 워크플로우"""
    
    async def run(
        self,
        agent: Any,
        message: str,
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        기본 채팅 워크플로우 실행
        
        Args:
            agent: LLM 에이전트
            message: 입력 메시지
            streaming_callback: 스트리밍 콜백
            
        Returns:
            str: 처리 결과
        """
        try:
            logger.info(f"기본 채팅 워크플로우 실행: {message[:50]}...")
            
            # 에이전트의 기본 응답 생성 메서드 호출
            if hasattr(agent, '_generate_basic_response'):
                result = await agent._generate_basic_response(message, streaming_callback)
                logger.info("기본 채팅 워크플로우 완료")
                return result
            else:
                logger.error("에이전트에 _generate_basic_response 메서드가 없습니다")
                return "에이전트 설정에 문제가 있습니다."
                
        except Exception as e:
            logger.error(f"기본 채팅 워크플로우 실행 중 오류: {e}")
            return f"워크플로우 실행 중 오류가 발생했습니다: {str(e)}" 