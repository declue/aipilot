"""
Perplexity 스타일 전문 리서치 워크플로우
실시간 웹검색을 통한 심층적이고 전문적인 조사 및 분석
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from dspilot_core.llm.workflow.base_workflow import BaseWorkflow
from dspilot_core.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class ResearchWorkflow(BaseWorkflow):
    """Perplexity 스타일 전문 리서치 워크플로우"""

    def __init__(self):
        self.search_queries = []
        self.collected_sources = []
        self.research_depth = "comprehensive"  # basic, standard, comprehensive

    async def run(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        전문 리서치 워크플로우 실행

        Args:
            agent: LLM 에이전트 (MCP 도구 필요)
            message: 리서치 질문/주제
            streaming_callback: 스트리밍 콜백

        Returns:
            str: 종합 리서치 보고서
        """
        try:
            logger.info(f"전문 리서치 워크플로우 시작: {message[:50]}...")

            # MCP 도구 사용 가능한지 확인
            if not hasattr(agent, "mcp_tool_manager") or not agent.mcp_tool_manager:
                return await self._fallback_research(agent, message, streaming_callback)

            if streaming_callback:
                streaming_callback("🔍 **전문 리서치 시작**\n\n")

            # 1단계: 다각도 검색 쿼리 생성
            search_queries = await self._generate_search_queries(agent, message, streaming_callback)
            
            # 2단계: 웹검색 실행 및 정보 수집
            raw_data = await self._execute_web_searches(agent, search_queries, streaming_callback)
            
            # 3단계: 추가 심화 검색 (필요시)
            enhanced_data = await self._deep_dive_search(agent, message, raw_data, streaming_callback)
            
            # 4단계: 정보 검증 및 신뢰성 평가
            verified_data = await self._verify_and_validate(agent, enhanced_data, streaming_callback)
            
            # 5단계: 종합 분석 및 보고서 생성
            final_report = await self._generate_comprehensive_report(
                agent, message, verified_data, streaming_callback
            )

            logger.info("전문 리서치 워크플로우 완료")
            return final_report

        except Exception as e:
            logger.error(f"전문 리서치 워크플로우 실행 중 오류: {e}")
            return f"리서치 워크플로우 실행 중 오류가 발생했습니다: {str(e)}"

    async def _generate_search_queries(
        self, agent: Any, topic: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> List[str]:
        """다각도 검색 쿼리 생성"""
        query_prompt = f"""
        다음 주제에 대한 전문적이고 포괄적인 리서치를 위한 검색 쿼리들을 생성해주세요:

        주제: {topic}

        다음 관점에서 5-7개의 다양한 검색 쿼리를 만들어주세요:
        1. 기본 개념 및 정의
        2. 최신 동향 및 뉴스
        3. 전문가 의견 및 분석
        4. 통계 및 데이터
        5. 관련 케이스 스터디
        6. 비교 분석 (경쟁사, 대안 등)
        7. 미래 전망 및 예측

        각 쿼리는:
        - 구체적이고 검색 최적화된 키워드 사용
        - 중복 없이 서로 다른 관점 포함
        - 영어와 한국어 혼용 가능

        JSON 형식으로 응답:
        {
            "queries": [
                "검색쿼리1",
                "검색쿼리2",
                ...
            ]
        }
        """

        if streaming_callback:
            streaming_callback("📝 검색 쿼리 생성 중...\n\n")

        response = await agent._generate_basic_response(query_prompt, None)
        
        # JSON 파싱
        try:
            import json
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                query_data = json.loads(json_str)
                queries = query_data.get("queries", [])
            else:
                queries = [topic, f"{topic} latest news", f"{topic} analysis"]
        except Exception as e:
            logger.warning(f"검색 쿼리 파싱 실패: {e}")
            queries = [topic, f"{topic} 최신 동향", f"{topic} 분석", f"{topic} 전문가 의견"]

        self.search_queries = queries
        logger.debug(f"검색 쿼리 생성 완료: {len(queries)}개")
        return queries

    async def _execute_web_searches(
        self, agent: Any, queries: List[str], streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, str]:
        """웹검색 실행 및 정보 수집"""
        search_results = {}
        
        for i, query in enumerate(queries, 1):
            if streaming_callback:
                streaming_callback(f"🌐 검색 {i}/{len(queries)}: {query[:50]}...\n")

            try:
                # MCP 웹검색 도구 사용
                search_prompt = f"웹에서 다음에 대해 최신 정보를 검색해주세요: {query}"
                
                if hasattr(agent, "generate_response"):
                    result = await agent.generate_response(search_prompt, None)
                    search_content = result.get("response", "검색 결과 없음")
                else:
                    search_content = await agent._generate_basic_response(search_prompt, None)
                
                search_results[f"query_{i}_{query[:30]}"] = search_content
                
            except Exception as e:
                logger.warning(f"검색 실패 - {query}: {e}")
                search_results[f"query_{i}_{query[:30]}"] = f"검색 실패: {str(e)}"

        if streaming_callback:
            streaming_callback(f"✅ 총 {len(search_results)}개 검색 완료\n\n")

        return search_results

    async def _deep_dive_search(
        self, agent: Any, original_topic: str, initial_data: Dict[str, str], 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, str]:
        """심화 검색 실행"""
        analysis_prompt = f"""
        원래 주제: {original_topic}
        
        초기 검색 결과들을 분석하여 다음을 식별해주세요:
        {self._format_search_data(initial_data)}

        다음 중 추가 조사가 필요한 영역이 있다면 2-3개의 추가 검색 쿼리를 제안해주세요:
        1. 데이터 부족 영역
        2. 상충되는 정보가 있는 부분
        3. 더 깊이 파야 할 전문 분야
        4. 최신 업데이트가 필요한 부분

        JSON 형식으로 응답:
        {
            "need_additional_search": true/false,
            "additional_queries": ["쿼리1", "쿼리2", "쿼리3"],
            "reason": "추가 검색이 필요한 이유"
        }
        """

        if streaming_callback:
            streaming_callback("🔬 심화 분석 중...\n")

        response = await agent._generate_basic_response(analysis_prompt, None)
        
        try:
            import json
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                analysis = json.loads(json_str)
                
                if analysis.get("need_additional_search", False):
                    additional_queries = analysis.get("additional_queries", [])
                    if streaming_callback:
                        streaming_callback(f"🎯 추가 심화 검색 실행: {len(additional_queries)}개\n")
                    
                    additional_results = await self._execute_web_searches(
                        agent, additional_queries, streaming_callback
                    )
                    
                    # 기존 데이터와 병합
                    enhanced_data = {**initial_data, **additional_results}
                    return enhanced_data
                    
        except Exception as e:
            logger.warning(f"심화 검색 분석 실패: {e}")

        return initial_data

    async def _verify_and_validate(
        self, agent: Any, data: Dict[str, str], streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """정보 검증 및 신뢰성 평가"""
        validation_prompt = f"""
        다음 검색 결과들의 신뢰성을 평가하고 검증해주세요:

        {self._format_search_data(data)}

        각 정보에 대해 다음을 평가해주세요:
        1. 정보의 신뢰성 (1-10점)
        2. 정보의 최신성 (1-10점) 
        3. 출처의 권위성 (1-10점)
        4. 정보 간 일관성 확인
        5. 사실 확인이 필요한 주장들

        또한 다음을 식별해주세요:
        - 가장 신뢰할 수 있는 정보들
        - 추가 확인이 필요한 정보들
        - 상충되는 정보가 있는 경우 해당 내용

        검증된 핵심 사실들과 주의사항을 정리해주세요.
        """

        if streaming_callback:
            streaming_callback("🔍 정보 검증 및 신뢰성 평가 중...\n")

        validation_result = await agent._generate_basic_response(validation_prompt, None)
        
        return {
            "raw_data": data,
            "validation_analysis": validation_result,
            "verified_facts": self._extract_verified_facts(validation_result)
        }

    async def _generate_comprehensive_report(
        self, agent: Any, original_question: str, verified_data: Dict[str, Any], 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """종합 리서치 보고서 생성"""
        report_prompt = f"""
        원래 질문: {original_question}

        검증된 데이터:
        {verified_data.get('validation_analysis', '')}

        위 정보를 바탕으로 Perplexity 스타일의 전문적인 리서치 보고서를 작성해주세요:

        # {original_question}

        ## 🔍 핵심 요약
        - 3-4줄로 핵심 내용 요약
        - 가장 중요한 발견사항

        ## 📊 주요 발견사항
        1. **첫 번째 핵심 발견**
           - 구체적인 데이터나 사실
           - 신뢰할 수 있는 출처 정보

        2. **두 번째 핵심 발견**
           - 구체적인 데이터나 사실
           - 신뢰할 수 있는 출처 정보

        3. **세 번째 핵심 발견**
           - 구체적인 데이터나 사실
           - 신뢰할 수 있는 출처 정보

        ## 🧭 심층 분석
        - 데이터 간 연관성 분석
        - 패턴과 트렌드 식별
        - 전문가 관점 종합

        ## 🔮 시사점 및 전망
        - 현재 상황의 의미
        - 미래 전망
        - 주의할 점

        ## ⚠️ 제한사항
        - 정보의 한계점
        - 추가 조사 필요 영역
        - 불확실한 부분

        ## 📚 참고 정보
        - 주요 출처들
        - 관련 리소스

        ---
        *이 보고서는 실시간 웹검색을 통해 수집된 정보를 바탕으로 작성되었습니다.*

        전문적이고 객관적인 보고서를 작성해주세요.
        """

        if streaming_callback:
            streaming_callback("📝 종합 보고서 작성 중...\n")

        final_report = await agent._generate_basic_response(report_prompt, streaming_callback)
        
        return final_report

    async def _fallback_research(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """MCP 도구 없을 때 기본 리서치"""
        if streaming_callback:
            streaming_callback("⚠️ 웹검색 도구가 없어 기본 지식 기반 분석을 제공합니다.\n\n")

        fallback_prompt = f"""
        다음 주제에 대해 기존 지식을 바탕으로 분석해주세요:

        주제: {message}

        다음 구조로 분석해주세요:
        1. 기본 개념 설명
        2. 주요 특징 및 현황
        3. 관련 동향 (일반적인)
        4. 고려사항
        5. 추천 리소스 (검색 키워드)

        실시간 웹검색은 불가하지만 최대한 도움이 될 수 있는 분석을 제공해주세요.
        """

        return await agent._generate_basic_response(fallback_prompt, streaming_callback)

    def _format_search_data(self, data: Dict[str, str]) -> str:
        """검색 데이터 포맷팅"""
        formatted = []
        for key, content in data.items():
            formatted.append(f"**{key}:**\n{content[:500]}...\n")
        return "\n".join(formatted)

    def _extract_verified_facts(self, validation_text: str) -> List[str]:
        """검증된 사실들 추출"""
        # 간단한 키워드 기반 추출
        facts = []
        lines = validation_text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['확인됨', '검증됨', '사실', '신뢰']):
                facts.append(line.strip())
        return facts[:5]  # 최대 5개 