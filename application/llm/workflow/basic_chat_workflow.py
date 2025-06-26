"""
기본 질의응답 워크플로우 (Cursor/Cline Ask 모드)
단순하고 직접적인 AI 어시스턴트 대화
"""

import logging
from typing import Any, Callable, Optional

from application.llm.workflow.base_workflow import BaseWorkflow
from application.util.logger import setup_logger

logger = setup_logger("basic_chat_workflow") or logging.getLogger("basic_chat_workflow")


class BasicChatWorkflow(BaseWorkflow):
    """
    기본 질의응답 워크플로우
    
    Cursor/Cline의 Ask 모드와 유사한 단순하고 직접적인 AI 대화
    - 복잡한 도구 사용 없이 순수 LLM 기반 응답
    - 빠르고 간결한 질의응답
    - 일반적인 정보 제공 및 간단한 도움말
    """

    async def run(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        기본 질의응답 워크플로우 실행

        Args:
            agent: LLM 에이전트
            message: 사용자 질문
            streaming_callback: 스트리밍 콜백

        Returns:
            str: AI 응답
        """
        try:
            logger.info(f"기본 질의응답 시작: {message[:50]}...")

            if streaming_callback:
                streaming_callback("💬 ")

            # 질문 유형에 따른 최적화된 프롬프트 생성
            optimized_prompt = self._optimize_prompt(message)

            # 순수 LLM 기반 응답 생성 (도구 사용 없음)
            if hasattr(agent, "_generate_basic_response"):
                result = await agent._generate_basic_response(optimized_prompt, streaming_callback)
                logger.info("기본 질의응답 완료")
                return result
            else:
                logger.error("에이전트에 기본 응답 생성 기능이 없습니다")
                return "죄송합니다. 현재 응답을 생성할 수 없습니다."

        except Exception as e:
            logger.error(f"기본 질의응답 실행 중 오류: {e}")
            return f"응답 생성 중 문제가 발생했습니다: {str(e)}"

    def _optimize_prompt(self, user_message: str) -> str:
        """사용자 질문을 분석하여 최적화된 프롬프트 생성"""
        
        # 질문 유형 감지
        question_type = self._detect_question_type(user_message)
        
        # 유형별 최적화된 프롬프트
        if question_type == "code_help":
            return f"""다음 프로그래밍 관련 질문에 대해 명확하고 실용적인 답변을 제공해주세요:

질문: {user_message}

답변 시 다음을 포함해주세요:
- 핵심 해결 방법
- 간단한 코드 예시 (필요시)
- 주의사항이나 팁

간결하고 실용적인 답변을 제공해주세요."""

        elif question_type == "explanation":
            return f"""다음 질문에 대해 이해하기 쉽게 설명해주세요:

질문: {user_message}

답변 시:
- 핵심 개념을 명확히 설명
- 구체적인 예시 포함
- 단계별로 정리하여 설명

명확하고 이해하기 쉬운 설명을 제공해주세요."""

        elif question_type == "comparison":
            return f"""다음 비교 요청에 대해 객관적이고 구조화된 답변을 제공해주세요:

질문: {user_message}

답변 시:
- 주요 차이점과 공통점
- 각각의 장단점
- 사용 상황별 권장사항

균형 잡힌 비교 분석을 제공해주세요."""

        elif question_type == "troubleshooting":
            return f"""다음 문제 해결 요청에 대해 단계별 해결 방법을 제공해주세요:

문제: {user_message}

답변 시:
- 가능한 원인들
- 단계별 해결 방법
- 예방 방법

실용적이고 따라하기 쉬운 해결책을 제공해주세요."""

        else:  # 일반 질문
            return f"""다음 질문에 대해 도움이 되는 답변을 제공해주세요:

질문: {user_message}

정확하고 유용한 정보를 바탕으로 친근하고 이해하기 쉬운 답변을 제공해주세요."""

    def _detect_question_type(self, message: str) -> str:
        """질문 유형 감지"""
        message_lower = message.lower()
        
        # 코딩/프로그래밍 관련
        code_keywords = ['코드', 'code', '프로그래밍', 'programming', '함수', 'function', 
                        '에러', 'error', '버그', 'bug', '구현', 'implement', 'python', 
                        'javascript', 'java', 'c++', 'sql', 'html', 'css']
        if any(keyword in message_lower for keyword in code_keywords):
            return "code_help"
        
        # 설명 요청
        explain_keywords = ['설명', '뭐야', '무엇', 'what', 'explain', '차이', 'difference',
                           '어떻게', 'how', '왜', 'why', '의미']
        if any(keyword in message_lower for keyword in explain_keywords):
            return "explanation"
        
        # 비교 요청
        compare_keywords = ['비교', 'compare', 'vs', '대', '차이점', '장단점', '어느게']
        if any(keyword in message_lower for keyword in compare_keywords):
            return "comparison"
        
        # 문제 해결
        trouble_keywords = ['문제', 'problem', '안돼', '안되', '오류', '에러', 'error',
                           '해결', 'solve', '고치', 'fix', '작동', '실행']
        if any(keyword in message_lower for keyword in trouble_keywords):
            return "troubleshooting"
        
        return "general"
