"""
연구/조사 전용 워크플로우
정보 수집 → 분석 → 종합 결론 도출 과정
"""

import logging
from typing import Any, Callable, Optional

from application.llm.workflow.base_workflow import BaseWorkflow
from application.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class ResearchWorkflow(BaseWorkflow):
    """연구/조사 워크플로우"""

    def __init__(self):
        self.steps = [
            "정보_수집",
            "데이터_분석",
            "종합_정리",
            "결론_도출",
        ]

    async def run(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        연구 워크플로우 실행

        Args:
            agent: LLM 에이전트
            message: 연구 주제
            streaming_callback: 스트리밍 콜백

        Returns:
            str: 연구 결과
        """
        try:
            logger.info(f"연구 워크플로우 시작: {message[:50]}...")

            # 1단계: 연구 계획 수립
            research_plan = await self._create_research_plan(agent, message, streaming_callback)
            
            # 2단계: 정보 수집
            collected_info = await self._collect_information(agent, research_plan, streaming_callback)
            
            # 3단계: 데이터 분석
            analysis_result = await self._analyze_data(agent, collected_info, streaming_callback)
            
            # 4단계: 최종 종합 보고서 작성
            final_report = await self._generate_final_report(
                agent, message, analysis_result, streaming_callback
            )

            logger.info("연구 워크플로우 완료")
            return final_report

        except Exception as e:
            logger.error(f"연구 워크플로우 실행 중 오류: {e}")
            return f"연구 워크플로우 실행 중 오류가 발생했습니다: {str(e)}"

    async def _create_research_plan(
        self, agent: Any, topic: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """연구 계획 수립"""
        planning_prompt = f"""
        다음 주제에 대한 체계적인 연구 계획을 수립해주세요:

        주제: {topic}

        다음 사항들을 포함해주세요:
        1. 연구 목적과 범위
        2. 핵심 질문들 (3-5개)
        3. 필요한 정보 유형
        4. 조사 방법론
        5. 예상 결과물

        간결하고 구체적인 계획을 작성해주세요.
        """

        if streaming_callback:
            streaming_callback("🔍 연구 계획 수립 중...\n\n")

        # 기본 응답 생성 메서드 사용
        if hasattr(agent, "_generate_basic_response"):
            plan = await agent._generate_basic_response(planning_prompt, streaming_callback)
        else:
            plan = "연구 계획 수립 기능을 사용할 수 없습니다."

        logger.debug("연구 계획 수립 완료")
        return plan

    async def _collect_information(
        self, agent: Any, research_plan: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """정보 수집 단계"""
        collection_prompt = f"""
        다음 연구 계획에 따라 정보 수집을 진행해주세요:

        {research_plan}

        사용 가능한 도구들을 활용하여 다양한 관점에서 정보를 수집하고,
        각 정보의 출처와 신뢰성을 명시해주세요.

        특히 다음 사항에 중점을 두세요:
        - 최신 정보와 동향
        - 다양한 관점과 의견
        - 구체적인 데이터와 사례
        - 전문가 견해나 연구 결과
        """

        if streaming_callback:
            streaming_callback("📚 정보 수집 중...\n\n")

        # MCP 도구가 있는 경우 활용
        if hasattr(agent, "mcp_tool_manager") and agent.mcp_tool_manager:
            # ReactAgent의 generate_response 사용하여 도구 활용
            if hasattr(agent, "generate_response"):
                result = await agent.generate_response(collection_prompt, streaming_callback)
                return result.get("response", "정보 수집에 실패했습니다.")

        # 기본 응답 생성
        if hasattr(agent, "_generate_basic_response"):
            info = await agent._generate_basic_response(collection_prompt, streaming_callback)
        else:
            info = "정보 수집 기능을 사용할 수 없습니다."

        logger.debug("정보 수집 완료")
        return info

    async def _analyze_data(
        self, agent: Any, collected_info: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """데이터 분석 단계"""
        analysis_prompt = f"""
        수집된 다음 정보를 분석해주세요:

        {collected_info}

        분석 시 다음 관점들을 고려해주세요:
        1. 핵심 패턴과 트렌드 식별
        2. 상충되는 정보나 의견 분석
        3. 데이터의 신뢰성과 한계점 평가
        4. 숨겨진 인사이트나 시사점 도출
        5. 추가 조사가 필요한 영역 식별

        객관적이고 논리적인 분석을 제공해주세요.
        """

        if streaming_callback:
            streaming_callback("🔬 데이터 분석 중...\n\n")

        if hasattr(agent, "_generate_basic_response"):
            analysis = await agent._generate_basic_response(analysis_prompt, streaming_callback)
        else:
            analysis = "데이터 분석 기능을 사용할 수 없습니다."

        logger.debug("데이터 분석 완료")
        return analysis

    async def _generate_final_report(
        self,
        agent: Any,
        original_topic: str,
        analysis_result: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """최종 종합 보고서 작성"""
        report_prompt = f"""
        원래 주제: {original_topic}

        분석 결과: {analysis_result}

        위 내용을 바탕으로 다음 구조의 종합 보고서를 작성해주세요:

        # 연구 보고서: {original_topic}

        ## 1. 요약 (Executive Summary)
        - 핵심 발견사항 3-5줄로 요약

        ## 2. 주요 발견사항 (Key Findings)
        - 가장 중요한 발견사항들을 우선순위 순으로

        ## 3. 상세 분석 (Detailed Analysis)
        - 수집된 데이터의 심층 분석
        - 패턴, 트렌드, 인사이트

        ## 4. 시사점 (Implications)
        - 실무적/전략적 시사점
        - 향후 전망

        ## 5. 제한사항 (Limitations)
        - 연구의 한계점
        - 추가 조사 필요 영역

        ## 6. 결론 및 권장사항 (Conclusions & Recommendations)
        - 명확한 결론
        - 구체적인 권장사항

        전문적이고 구조화된 보고서를 작성해주세요.
        """

        if streaming_callback:
            streaming_callback("📝 최종 보고서 작성 중...\n\n")

        if hasattr(agent, "_generate_basic_response"):
            report = await agent._generate_basic_response(report_prompt, streaming_callback)
        else:
            report = "최종 보고서 작성 기능을 사용할 수 없습니다."

        logger.debug("최종 보고서 작성 완료")
        return report 