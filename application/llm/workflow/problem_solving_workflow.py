"""
문제 해결 전용 워크플로우
"""

import logging
from typing import Any, Callable, Optional

from application.llm.workflow.base_workflow import BaseWorkflow
from application.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class ProblemSolvingWorkflow(BaseWorkflow):
    """문제 해결 전용 워크플로우"""

    async def run(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        문제 해결 워크플로우 실행
        
        1. 문제 정의
        2. 원인 분석
        3. 해결책 도출
        4. 실행 계획 수립
        """
        try:
            logger.info(f"문제 해결 워크플로우 시작: {message[:50]}...")

            # 1단계: 문제 정의
            problem_definition = await self._define_problem(agent, message, streaming_callback)
            
            # 2단계: 원인 분석
            root_cause = await self._analyze_root_cause(agent, problem_definition, streaming_callback)
            
            # 3단계: 해결책 도출
            solutions = await self._generate_solutions(agent, root_cause, streaming_callback)
            
            # 4단계: 실행 계획 수립
            action_plan = await self._create_action_plan(agent, solutions, streaming_callback)

            logger.info("문제 해결 워크플로우 완료")
            return action_plan

        except Exception as e:
            logger.error(f"문제 해결 워크플로우 실행 중 오류: {e}")
            return f"문제 해결 워크플로우 실행 중 오류가 발생했습니다: {str(e)}"

    async def _define_problem(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """문제 명확히 정의"""
        prompt = f"""
        다음 상황에서 핵심 문제를 명확히 정의해주세요:

        상황: {message}

        다음 관점에서 문제를 분석해주세요:
        1. 현재 상태 vs 원하는 상태
        2. 문제의 범위와 경계
        3. 영향받는 주체들
        4. 시급성과 중요도
        5. 측정 가능한 문제 지표

        명확하고 구체적인 문제 정의를 제공해주세요.
        """

        if streaming_callback:
            streaming_callback("🎯 문제 정의 중...\n\n")

        return await self._execute_step(agent, prompt, streaming_callback)

    async def _analyze_root_cause(
        self, agent: Any, problem_definition: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """근본 원인 분석"""
        prompt = f"""
        다음 문제의 근본 원인을 분석해주세요:

        문제 정의: {problem_definition}

        5 Why 기법을 사용하여 근본 원인을 찾아주세요:
        1. 왜 이 문제가 발생했는가?
        2. 왜 그런 상황이 발생했는가?
        3. 왜 그런 조건이 만들어졌는가?
        4. 왜 그런 시스템이 있는가?
        5. 왜 그런 구조가 형성되었는가?

        또한 다음 관점도 고려해주세요:
        - 시스템적 원인
        - 프로세스적 원인  
        - 인적 원인
        - 환경적 원인

        체계적인 근본 원인 분석을 제공해주세요.
        """

        if streaming_callback:
            streaming_callback("🔍 근본 원인 분석 중...\n\n")

        return await self._execute_step(agent, prompt, streaming_callback)

    async def _generate_solutions(
        self, agent: Any, root_cause: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """해결책 도출"""
        prompt = f"""
        다음 근본 원인에 대한 해결책을 도출해주세요:

        근본 원인 분석: {root_cause}

        다양한 해결책을 다음 관점에서 도출해주세요:
        1. 단기 해결책 (즉시 실행 가능)
        2. 중기 해결책 (3-6개월 내)
        3. 장기 해결책 (시스템 개선)

        각 해결책에 대해 다음을 포함해주세요:
        - 구체적인 실행 방법
        - 예상 효과
        - 필요한 자원
        - 리스크와 제약사항
        - 실행 난이도

        창의적이고 실용적인 해결책들을 제공해주세요.
        """

        if streaming_callback:
            streaming_callback("💡 해결책 도출 중...\n\n")

        return await self._execute_step(agent, prompt, streaming_callback)

    async def _create_action_plan(
        self, agent: Any, solutions: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """실행 계획 수립"""
        prompt = f"""
        다음 해결책들을 바탕으로 구체적인 실행 계획을 수립해주세요:

        해결책들: {solutions}

        다음 구조의 실행 계획을 작성해주세요:

        # 실행 계획

        ## 1. 우선순위별 실행 로드맵
        - 1단계 (즉시 실행): 
        - 2단계 (1-3개월):
        - 3단계 (3-6개월):

        ## 2. 세부 실행 단계
        각 단계별로:
        - 구체적인 액션 아이템
        - 담당자/역할
        - 타임라인
        - 성공 지표
        - 체크포인트

        ## 3. 리스크 관리
        - 예상 리스크
        - 대응 방안
        - 모니터링 방법

        ## 4. 자원 계획
        - 필요한 자원
        - 예산 계획
        - 인력 계획

        실행 가능하고 구체적인 계획을 제공해주세요.
        """

        if streaming_callback:
            streaming_callback("📋 실행 계획 수립 중...\n\n")

        return await self._execute_step(agent, prompt, streaming_callback)

    async def _execute_step(
        self, agent: Any, prompt: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """단계 실행"""
        if hasattr(agent, "_generate_basic_response"):
            return await agent._generate_basic_response(prompt, streaming_callback)
        else:
            return "단계 실행 기능을 사용할 수 없습니다" 