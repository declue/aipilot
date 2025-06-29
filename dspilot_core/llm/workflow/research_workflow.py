"""
전문 리서치 워크플로우 (ResearchWorkflow)
========================================

Perplexity 스타일의 심층적이고 전문적인 조사 및 분석을 수행하는 워크플로우입니다.
실시간 웹검색을 통해 다각도로 정보를 수집하고, 검증을 거쳐 종합적인 리서치 보고서를 생성합니다.

단순한 검색을 넘어서 전문적인 조사 방법론을 적용하여, 신뢰성 있고 
포괄적인 정보를 제공하는 것이 특징입니다.

주요 특징
=========

1. **다각도 검색 전략**
   - 주제를 여러 관점에서 분석하여 검색 쿼리 생성
   - 기본 개념, 최신 동향, 전문가 의견, 통계 데이터 등 포괄적 수집
   - 중복 없이 서로 다른 관점의 정보 확보

2. **심층 분석 프로세스**
   - 초기 검색 결과 분석 후 추가 조사 영역 식별
   - 데이터 부족 영역이나 상충 정보에 대한 추가 검색
   - 정보의 신뢰성 및 최신성 평가

3. **전문적 보고서 생성**
   - Perplexity 스타일의 구조화된 리서치 보고서
   - 핵심 요약, 주요 발견사항, 심층 분석, 시사점 등 포함
   - 출처 정보 및 제한사항 명시

4. **정보 검증 시스템**
   - 수집된 정보의 신뢰성 평가 (1-10점 척도)
   - 정보 간 일관성 확인 및 상충 내용 식별
   - 사실 확인이 필요한 주장들 별도 표시

처리 과정 다이어그램
==================

```mermaid
flowchart TD
    A[리서치 주제] --> B[다각도 검색 쿼리 생성]
    B --> C[웹검색 실행 및 정보 수집]
    C --> D[초기 결과 분석]
    D --> E{추가 조사 필요?}
    E -->|Yes| F[심화 검색 실행]
    E -->|No| G[정보 검증 및 신뢰성 평가]
    F --> G
    G --> H[종합 리서치 보고서 생성]
    H --> I[최종 보고서 반환]
```

리서치 단계별 세부 과정
=====================

### 1단계: 다각도 검색 쿼리 생성
**목적**: 주제를 포괄적으로 조사하기 위한 다양한 검색 쿼리 생성

**생성 관점**:
- 기본 개념 및 정의
- 최신 동향 및 뉴스  
- 전문가 의견 및 분석
- 통계 및 데이터
- 관련 케이스 스터디
- 비교 분석 (경쟁사, 대안 등)
- 미래 전망 및 예측

**예시**: "인공지능 윤리" 주제의 경우
- "AI ethics definition principles"
- "인공지능 윤리 최신 동향 2024"
- "AI ethics expert opinion analysis"
- "artificial intelligence ethics statistics data"
- "AI ethics case study examples"

### 2단계: 웹검색 실행 및 정보 수집
**프로세스**:
- 각 검색 쿼리별로 MCP 웹검색 도구 사용
- 검색 결과 수집 및 임시 저장
- 실패한 검색에 대한 오류 로깅
- 스트리밍 콜백을 통한 진행 상황 실시간 피드백

### 3단계: 추가 심화 검색
**판단 기준**:
- 데이터 부족 영역 식별
- 상충되는 정보 발견 시
- 더 깊이 파야 할 전문 분야 존재
- 최신 업데이트가 필요한 부분

**실행 방식**:
- LLM이 초기 결과를 분석하여 추가 검색 필요성 판단
- 필요시 2-3개의 추가 검색 쿼리 생성 및 실행

### 4단계: 정보 검증 및 신뢰성 평가
**평가 기준**:
- 정보의 신뢰성 (1-10점): 출처의 권위성, 정보의 정확성
- 정보의 최신성 (1-10점): 발행일, 업데이트 빈도
- 출처의 권위성 (1-10점): 기관의 신뢰도, 전문성
- 정보 간 일관성: 여러 소스 간 내용 일치도

### 5단계: 종합 리서치 보고서 생성
**보고서 구조**:
```
# 주제명

## 🔍 핵심 요약
- 3-4줄 핵심 내용 요약
- 가장 중요한 발견사항

## 📊 주요 발견사항  
1. 첫 번째 핵심 발견 (구체적 데이터 + 출처)
2. 두 번째 핵심 발견 (구체적 데이터 + 출처)
3. 세 번째 핵심 발견 (구체적 데이터 + 출처)

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
```

사용 권장 상황
=============

### 적합한 사용 사례:
- **학술 연구**: 논문 작성, 문헌 조사, 현황 분석
- **비즈니스 분석**: 시장 조사, 경쟁사 분석, 트렌드 분석
- **정책 연구**: 사회 이슈 분석, 정책 효과 조사
- **기술 조사**: 신기술 동향, 기술 비교 분석
- **투자 분석**: 산업 전망, 기업 분석, 리스크 평가

### 부적합한 사용 사례:
- **단순 정보 조회**: 날씨, 시간 등 간단한 정보
- **개인적 질문**: 개인 상담, 간단한 도움말
- **즉시 답변 필요**: 긴급한 의사결정, 실시간 대응
- **도구 없는 환경**: 웹검색 도구가 없는 경우

사용법 및 예시
=============

### 1. 기본 사용법

```python
from dspilot_core.llm.workflow import ResearchWorkflow

# 워크플로우 초기화
workflow = ResearchWorkflow()

# 리서치 실행
result = await workflow.run(
    agent=agent,
    message="인공지능이 교육에 미치는 영향에 대해 조사해주세요",
    streaming_callback=progress_callback
)
```

### 2. 에이전트에서 사용

```python
class ProblemAgent(BaseAgent):
    def _get_workflow_name(self, mode: str) -> str:
        if mode == "research":
            return "research"  # ResearchWorkflow 사용
        # ... 다른 모드들
```

### 3. 진행 상황 모니터링

```python
def research_progress(content: str):
    if "검색" in content:
        print(f"🔍 {content}")
    elif "분석" in content:
        print(f"🧠 {content}")
    elif "보고서" in content:
        print(f"📝 {content}")

result = await workflow.run(agent, research_topic, research_progress)
```

성능 및 품질 특성
================

### 장점
- **포괄성**: 다각도 검색으로 빠뜨리는 정보 최소화
- **신뢰성**: 정보 검증 및 출처 평가 시스템
- **전문성**: 체계적인 조사 방법론 적용
- **구조화**: 읽기 쉽고 활용하기 좋은 보고서 형식

### 제한사항
- **시간 소요**: 다단계 검색으로 인한 처리 시간 증가
- **도구 의존**: 웹검색 도구 없이는 기본 지식 기반으로만 동작
- **비용**: 여러 번의 LLM 호출로 인한 API 비용 증가
- **언어 제한**: 주로 한국어/영어 소스에 의존

최적화 팁
=========

### 효과적인 리서치 주제 설정
1. **구체적 주제**: "AI 기술"보다는 "의료 분야 AI 활용 현황"
2. **명확한 범위**: "글로벌 동향" vs "국내 현황" 등 범위 명시
3. **시간 범위**: "최근 3년간", "2024년 현재" 등 시점 명시

### 품질 향상 방법
- 신뢰할 만한 출처가 많은 주제 선택
- 너무 새로운 주제보다는 어느 정도 정보가 축적된 주제
- 객관적 데이터가 존재하는 주제 우선

문제 해결
=========

### MCP 도구 없는 경우
- 자동으로 기본 지식 기반 분석으로 폴백
- 제한적이지만 기본적인 분석 정보 제공
- 추천 검색 키워드 제공

### 검색 결과 부족
- 다양한 키워드로 재검색 시도
- 관련 주제로 범위 확장
- 부족한 부분을 명시적으로 보고서에 기재

### 상충 정보 발견
- 여러 출처의 정보를 균형있게 제시
- 상충 내용을 명확히 표시
- 추가 확인이 필요한 부분 안내

확장 가능성
===========

### 향후 개선 방향
- **다국어 지원**: 더 많은 언어의 소스 활용
- **전문 데이터베이스**: 학술 DB, 정부 통계 등 연동
- **시각화**: 차트, 그래프 등 데이터 시각화 기능
- **협업 기능**: 여러 에이전트 간 리서치 결과 공유
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from dspilot_core.llm.workflow.base_workflow import BaseWorkflow
from dspilot_core.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class ResearchWorkflow(BaseWorkflow):
    """
    전문 리서치 워크플로우
    
    Perplexity 스타일의 심층적이고 전문적인 조사 및 분석을 수행합니다.
    실시간 웹검색을 통해 다각도로 정보를 수집하고, 검증을 거쳐 
    종합적인 리서치 보고서를 생성합니다.
    
    주요 특징:
    - 다각도 검색 전략으로 포괄적 정보 수집
    - 정보 검증 및 신뢰성 평가 시스템
    - 전문적이고 구조화된 리서치 보고서 생성
    - 심층 분석 및 추가 조사 기능
    
    Attributes:
        search_queries: 생성된 검색 쿼리 목록
        collected_sources: 수집된 정보 소스 목록  
        research_depth: 리서치 깊이 설정 ("basic", "standard", "comprehensive")
    """

    def __init__(self):
        """ResearchWorkflow 초기화"""
        self.search_queries = []
        self.collected_sources = []
        self.research_depth = "comprehensive"  # 기본값: 포괄적 조사

    async def run(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        전문 리서치 워크플로우 실행

        주어진 주제에 대해 다단계 리서치 프로세스를 수행하여
        전문적이고 포괄적인 조사 보고서를 생성합니다.

        Args:
            agent: LLM 에이전트 (MCP 웹검색 도구 필요)
            message: 리서치 질문/주제
            streaming_callback: 실시간 진행 상황 콜백

        Returns:
            str: 종합 리서치 보고서 또는 기본 분석 결과

        Raises:
            Exception: 리서치 프로세스 중 복구 불가능한 오류 발생 시
        """
        try:
            logger.info(f"전문 리서치 워크플로우 시작: {message[:50]}...")

            # MCP 도구 사용 가능한지 확인
            if not hasattr(agent, "mcp_tool_manager") or not agent.mcp_tool_manager:
                logger.warning("MCP 도구가 없어 기본 지식 기반 분석으로 폴백")
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
        """
        다각도 검색 쿼리 생성
        
        주제를 여러 관점에서 분석하여 포괄적인 정보 수집을 위한
        다양한 검색 쿼리를 생성합니다.
        
        Args:
            agent: LLM 에이전트
            topic: 리서치 주제
            streaming_callback: 진행 상황 콜백
            
        Returns:
            List[str]: 생성된 검색 쿼리 목록
        """
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
        
        # JSON 파싱 및 쿼리 추출
        try:
            import json
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                query_data = json.loads(json_str)
                queries = query_data.get("queries", [])
            else:
                # JSON 파싱 실패시 기본 쿼리 생성
                queries = [topic, f"{topic} latest news", f"{topic} analysis"]
        except Exception as e:
            logger.warning(f"검색 쿼리 파싱 실패: {e}")
            # 폴백: 기본 쿼리 생성
            queries = [topic, f"{topic} 최신 동향", f"{topic} 분석", f"{topic} 전문가 의견"]

        self.search_queries = queries
        logger.debug(f"검색 쿼리 생성 완료: {len(queries)}개")
        return queries

    async def _execute_web_searches(
        self, agent: Any, queries: List[str], streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, str]:
        """
        웹검색 실행 및 정보 수집
        
        생성된 검색 쿼리들을 순차적으로 실행하여 정보를 수집합니다.
        실패한 검색도 로깅하여 나중에 분석할 수 있도록 합니다.
        
        Args:
            agent: LLM 에이전트
            queries: 검색 쿼리 목록
            streaming_callback: 진행 상황 콜백
            
        Returns:
            Dict[str, str]: 쿼리별 검색 결과
        """
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
                logger.debug(f"검색 완료: {query[:30]}...")
                
            except Exception as e:
                logger.warning(f"검색 실패 - {query}: {e}")
                search_results[f"query_{i}_{query[:30]}"] = f"검색 실패: {str(e)}"

        if streaming_callback:
            successful_searches = len([r for r in search_results.values() if not r.startswith("검색 실패")])
            streaming_callback(f"✅ 총 {successful_searches}/{len(search_results)}개 검색 완료\n\n")

        return search_results

    async def _deep_dive_search(
        self, agent: Any, original_topic: str, initial_data: Dict[str, str], 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, str]:
        """
        심화 검색 실행
        
        초기 검색 결과를 분석하여 추가 조사가 필요한 영역을 식별하고
        필요시 추가 검색을 수행합니다.
        
        Args:
            agent: LLM 에이전트
            original_topic: 원래 리서치 주제
            initial_data: 초기 검색 결과
            streaming_callback: 진행 상황 콜백
            
        Returns:
            Dict[str, str]: 초기 데이터 + 추가 검색 결과
        """
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
                    reason = analysis.get("reason", "")
                    
                    if streaming_callback:
                        streaming_callback(f"🎯 추가 심화 검색 실행: {len(additional_queries)}개\n")
                        streaming_callback(f"사유: {reason}\n\n")
                    
                    logger.info(f"추가 검색 실행: {reason}")
                    additional_results = await self._execute_web_searches(
                        agent, additional_queries, streaming_callback
                    )
                    
                    # 기존 데이터와 병합
                    enhanced_data = {**initial_data, **additional_results}
                    return enhanced_data
                else:
                    if streaming_callback:
                        streaming_callback("✅ 초기 검색 결과가 충분하여 추가 검색 생략\n\n")
                    
        except Exception as e:
            logger.warning(f"심화 검색 분석 실패: {e}")

        return initial_data

    async def _verify_and_validate(
        self, agent: Any, data: Dict[str, str], streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        정보 검증 및 신뢰성 평가
        
        수집된 정보의 신뢰성, 최신성, 권위성을 평가하고
        정보 간 일관성을 확인합니다.
        
        Args:
            agent: LLM 에이전트
            data: 수집된 검색 데이터
            streaming_callback: 진행 상황 콜백
            
        Returns:
            Dict[str, Any]: 검증된 데이터와 분석 결과
        """
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
        """
        종합 리서치 보고서 생성
        
        검증된 데이터를 바탕으로 Perplexity 스타일의 전문적인
        리서치 보고서를 생성합니다.
        
        Args:
            agent: LLM 에이전트
            original_question: 원래 리서치 질문
            verified_data: 검증된 데이터
            streaming_callback: 진행 상황 콜백
            
        Returns:
            str: 완성된 리서치 보고서
        """
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
        """
        MCP 도구 없을 때 기본 리서치
        
        웹검색 도구가 없는 경우 기존 지식을 바탕으로
        기본적인 분석을 제공합니다.
        
        Args:
            agent: LLM 에이전트
            message: 리서치 주제
            streaming_callback: 진행 상황 콜백
            
        Returns:
            str: 기본 지식 기반 분석 결과
        """
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
        """
        검색 데이터 포맷팅
        
        검색 결과 데이터를 읽기 쉬운 형태로 포맷팅합니다.
        
        Args:
            data: 검색 결과 딕셔너리
            
        Returns:
            str: 포맷팅된 검색 데이터
        """
        formatted = []
        for key, content in data.items():
            # 내용이 너무 길면 500자로 제한
            truncated_content = content[:500] + "..." if len(content) > 500 else content
            formatted.append(f"**{key}:**\n{truncated_content}\n")
        return "\n".join(formatted)

    def _extract_verified_facts(self, validation_text: str) -> List[str]:
        """
        검증된 사실들 추출
        
        검증 분석 텍스트에서 확인된 사실들을 추출합니다.
        
        Args:
            validation_text: 검증 분석 결과 텍스트
            
        Returns:
            List[str]: 추출된 검증 사실 목록
        """
        facts = []
        lines = validation_text.split('\n')
        
        # 키워드 기반으로 검증된 사실 추출
        fact_keywords = ['확인됨', '검증됨', '사실', '신뢰', '입증', '증명']
        
        for line in lines:
            line = line.strip()
            if line and any(keyword in line.lower() for keyword in fact_keywords):
                # 불필요한 마크다운 문법 제거
                cleaned_line = line.replace('*', '').replace('#', '').strip()
                if len(cleaned_line) > 10:  # 너무 짧은 내용 제외
                    facts.append(cleaned_line)
        
        return facts[:5]  # 최대 5개까지만 반환 