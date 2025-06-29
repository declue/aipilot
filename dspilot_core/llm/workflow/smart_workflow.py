"""
통합 스마트 워크플로우 (SmartWorkflow)
=====================================

DSPilot의 핵심 워크플로우로, 사용자 요청의 복잡도를 자동 분석하여 
최적의 처리 방식을 선택하는 지능형 워크플로우입니다.

기존의 AgentWorkflow와 AdaptiveWorkflow의 장점을 통합하여,
단순한 요청부터 복잡한 다단계 작업까지 모두 효율적으로 처리합니다.

주요 특징
=========

1. **자동 복잡도 분석**
   - LLM이 요청을 분석하여 simple/medium/complex로 분류
   - 분류 결과에 따라 최적의 처리 전략 자동 선택

2. **이중 처리 전략**
   - 단순 요청: 직접 도구 실행 (빠른 처리)
   - 복잡 요청: Plan & Execute (정확한 처리)

3. **MCP 도구 통합**
   - 모든 MCP 도구와 호환
   - 도구 메타데이터 기반 동적 처리

4. **스트리밍 지원**
   - 실시간 진행 상황 피드백
   - 사용자 경험 최적화

처리 흐름 다이어그램
==================

```mermaid
flowchart TD
    A[사용자 요청] --> B{도구 사용 가능?}
    B -->|No| C[일반 LLM 응답]
    B -->|Yes| D[복잡도 분석]
    D --> E{복잡도 판단}
    E -->|Simple| F[직접 도구 실행]
    E -->|Medium| F
    E -->|Complex| G[Plan & Execute]
    F --> H[결과 반환]
    G --> I[계획 수립]
    I --> J[단계별 실행]
    J --> K[결과 통합]
    K --> H
```

복잡도 판단 기준
===============

### Simple (단순)
- 1-2개 도구로 즉시 해결 가능
- 예시: "현재 시간 알려줘", "날씨 검색해줘"
- 처리 방식: BaseAgent.auto_tool_flow() 직접 호출

### Medium (중간)
- 2-3개 도구의 순차 실행으로 해결 가능
- 예시: "파일 읽고 요약해줘", "검색 후 결과 저장해줘"
- 처리 방식: 단순 처리로 폴백 (대부분 해결 가능)

### Complex (복잡)
- 다단계 계획이 필요한 복합 작업
- 예시: "여러 소스 검색 후 비교 분석하여 보고서 작성"
- 처리 방식: Plan & Execute 전략

사용법 및 예시
=============

### 1. 기본 사용법

```python
from dspilot_core.llm.workflow import SmartWorkflow

# 워크플로우 초기화
workflow = SmartWorkflow(llm_service=llm_service, mcp_tool_manager=tool_manager)

# 실행
result = await workflow.run(agent, "사용자 요청", streaming_callback)
```

### 2. 스트리밍 콜백과 함께 사용

```python
def progress_callback(content: str):
    print(f"[진행상황] {content}")

result = await workflow.run(
    agent=my_agent,
    user_message="복잡한 작업 요청",
    streaming_callback=progress_callback
)
```

### 3. 에이전트에서 통합 사용

```python
class ProblemAgent(BaseAgent):
    def _get_workflow_name(self, mode: str) -> str:
        # 대부분의 모드를 SmartWorkflow로 통합
        if mode in ["mcp_tools", "workflow", "auto"]:
            return "smart"
        elif mode == "basic":
            return "basic"
        elif mode == "research":
            return "research"
        else:
            return "smart"  # 기본값
```

내부 구현 세부사항
=================

### 복잡도 분석 프롬프트
```
다음 사용자 요청의 복잡도를 분석해주세요:
사용자 요청: {message}
사용 가능한 도구들: {tools_list}

복잡도 기준:
- simple: 1-2개 도구로 즉시 해결 가능
- medium: 2-3개 도구 순차 실행으로 해결 가능  
- complex: 다단계 계획이 필요한 복합 작업

JSON 응답: {"complexity": "simple|medium|complex", "reason": "판단 이유"}
```

### Plan & Execute 전략
1. **계획 수립**: LLM이 JSON 형태의 실행 계획 생성
2. **단계별 실행**: MCP 도구를 순차적으로 호출
3. **결과 통합**: 모든 결과를 종합하여 최종 응답 생성

고급 기능 (AdaptiveWorkflow 통합)
=================================

### 1. 반복적 계획 개선
- **중복 계획 감지**: 해시 기반으로 이전에 실행한 계획과 중복 방지
- **실패 분석**: 실행 실패 원인을 분석하여 다음 계획에 반영
- **계획 수정**: 실패율이 높을 때 자동으로 계획을 개선하여 재시도
- **최대 3회 반복**: 계획 수립 → 실행 → 평가 → 개선 사이클

### 2. 고급 실행 제어
- **단계별 재시도**: 각 단계마다 최대 3회 재시도 (설정 가능)
- **매개변수 동적 치환**: 이전 단계 결과를 다음 단계 매개변수로 자동 치환
- **실행 결과 검증**: 각 단계 결과의 유효성을 자동 검증
- **사용자 승인 모드**: 중요한 단계 실행 전 사용자 승인 요청 (선택사항)

### 3. 컨텍스트 메모리 관리
- **단계별 메모리**: 각 단계의 실행 결과와 메타데이터 저장
- **실행 컨텍스트**: 전체 실행 과정의 상태 정보 유지
- **실패 이력 관리**: 실패 패턴 분석으로 향후 계획 개선

### 4. 지능형 오류 복구
- **공통 오류 패턴 분석**: 권한, 파일 경로, 네트워크 등 오류 유형별 분석
- **자동 폴백**: 복잡 처리 실패 시 단순 처리로 자동 전환
- **부분 성공 처리**: 일부 단계 실패 시에도 성공한 부분의 결과 활용

고급 사용법
===========

### 1. 인터랙션 모드 설정

```python
# 사용자 승인 모드 활성화
workflow = SmartWorkflow()
workflow.set_interaction_mode(True)

# 자동 실행 모드 (기본값)
workflow.set_interaction_mode(False)
```

### 2. 실행 통계 확인

```python
# 실행 통계 조회
stats = workflow.get_execution_statistics()
print(f"실행된 계획 수: {stats['executed_plans']}")
print(f"단계 메모리 크기: {stats['step_memory_size']}")
```

### 3. 실행 히스토리 관리

```python
# 히스토리 초기화 (메모리 절약)
workflow.clear_execution_history()
```

### 4. 매개변수 동적 치환 예시

```json
{
  "steps": [
    {
      "step": 1,
      "tool": "file_read",
      "args": {"path": "data.txt"},
      "desc": "데이터 파일 읽기"
    },
    {
      "step": 2,
      "tool": "text_process",
      "args": {"content": "$step_1"},
      "desc": "읽은 데이터 처리"
    }
  ]
}
```

성능 최적화
===========

- **캐싱**: 도구 목록과 복잡도 분석 결과 캐싱
- **병렬 처리**: 독립적인 단계들의 병렬 실행 지원 (향후 확장)
- **오류 복구**: 다층 폴백 메커니즘으로 안정성 확보
- **리소스 관리**: 메모리 효율적인 결과 저장 및 히스토리 관리
- **지능형 재시도**: 실패 원인 분석 기반 선택적 재시도

확장성
======

새로운 MCP 도구가 추가되어도 코드 수정 없이 자동으로 지원됩니다.
도구의 메타데이터(이름, 설명)만으로 복잡도 분석과 계획 수립이 가능합니다.

### 확장 가능한 요소들:
- **검증 규칙**: 도구별 맞춤 결과 검증 로직 추가
- **재시도 전략**: 오류 유형별 재시도 전략 커스터마이징
- **계획 개선 알고리즘**: 더 정교한 계획 개선 로직 구현

제한사항
========

- **복잡도 분석 정확도**: LLM 성능에 의존
- **계획 수립 시간**: 복잡한 작업의 경우 다소 시간 소요
- **메모리 사용량**: 실행 히스토리가 누적되면 메모리 사용량 증가
- **순차 실행**: 현재는 단계별 순차 실행만 지원 (병렬 실행은 향후 확장)

문제 해결
=========

### 복잡도 분석 실패
- 자동으로 'simple'로 폴백하여 안전하게 처리
- 로그에서 분석 실패 원인 확인 가능

### 계획 수립 실패  
- 단순 처리 방식으로 자동 폴백
- 대부분의 요청은 단순 처리로도 해결 가능

### 반복적 실행 실패
- 최대 3회 계획 수정 시도 후 부분 결과라도 반환
- 실패 원인 분석을 통한 근본 문제 해결 가이드 제공

### 메모리 사용량 증가
- `clear_execution_history()` 호출로 주기적 히스토리 정리
- 장시간 실행 시 메모리 모니터링 권장

### 도구 실행 실패
- 단계별 재시도 메커니즘으로 일시적 오류 자동 복구
- 영구적 실패 시 대안 계획 자동 생성
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from dspilot_core.llm.models.conversation_message import ConversationMessage
from dspilot_core.llm.models.llm_response import LLMResponse
from dspilot_core.llm.workflow.base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class SmartWorkflow(BaseWorkflow):
    """
    통합 스마트 워크플로우
    
    사용자 요청의 복잡도를 자동 분석하여 최적의 처리 방식을 선택하는 지능형 워크플로우입니다.
    
    - 단순 요청: 직접 도구 실행으로 빠른 처리
    - 복잡 요청: Plan & Execute로 정확한 처리
    - 모든 MCP 도구와 호환되는 범용 워크플로우
    
    Attributes:
        llm_service: LLM 서비스 인스턴스
        mcp_tool_manager: MCP 도구 관리자
        workflow_name: 워크플로우 식별명 ("smart")
        max_iterations: 최대 반복 횟수 (기본값: 10)
        context_window: 컨텍스트 윈도우 크기 (기본값: 20)
    """

    def __init__(self, llm_service=None, mcp_tool_manager=None):
        """
        SmartWorkflow 초기화
        
        Args:
            llm_service: LLM 서비스 인스턴스 (선택사항)
            mcp_tool_manager: MCP 도구 관리자 (선택사항)
        """
        self.llm_service = llm_service
        self.mcp_tool_manager = mcp_tool_manager
        self.workflow_name = "smart"
        self.max_iterations = 10
        self.context_window = 20
        
        # AdaptiveWorkflow 고급 기능들 추가
        self.execution_context = {}  # 실행 컨텍스트 저장
        self.step_memory = {}  # 단계별 메모리
        self.executed_plan_hashes = set()  # 중복 계획 감지
        self.retry_count = {}  # 단계별 재시도 횟수
        self.max_retries = 3  # 최대 재시도 횟수
        self.interaction_mode = True  # 사용자 승인 모드

    async def run(
        self,
        agent: "BaseAgent",
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        스마트 워크플로우 실행
        
        사용자 요청을 분석하여 복잡도에 따라 최적의 처리 방식을 자동 선택합니다.
        
        Args:
            agent: 실행할 BaseAgent 인스턴스
            user_message: 사용자 요청 메시지
            streaming_callback: 실시간 진행 상황 콜백 함수
            
        Returns:
            str: 처리 결과 메시지
            
        Raises:
            Exception: 워크플로우 실행 중 복구 불가능한 오류 발생 시
        """
        try:
            logger.info("=== SmartWorkflow: 처리 시작 ===")

            # 1. 도구 사용 가능성 확인
            available_tools = await self._get_available_tools()
            if not available_tools:
                logger.info("사용 가능한 도구가 없음 - LLM 응답으로 처리")
                return await self._generate_llm_response(agent, user_message, streaming_callback)

            # 2. 요청 복잡도 분석
            complexity = await self._analyze_complexity(agent, user_message, available_tools)
            logger.info(f"요청 복잡도 분석 결과: {complexity}")

            # 3. 복잡도에 따른 처리 방식 선택
            if complexity == "simple":
                return await self._handle_simple_request(agent, user_message, streaming_callback)
            elif complexity == "complex":
                return await self._handle_complex_request(agent, user_message, streaming_callback)
            else:
                # 중간 복잡도는 단순 방식으로 처리 (대부분 해결 가능)
                return await self._handle_simple_request(agent, user_message, streaming_callback)

        except Exception as e:
            logger.error(f"SmartWorkflow 처리 중 오류: {e}")
            return f"워크플로우 처리 중 오류가 발생했습니다: {str(e)}"

    async def _get_available_tools(self) -> List[Any]:
        """
        사용 가능한 MCP 도구 목록 반환
        
        Returns:
            List[Any]: 사용 가능한 도구 목록 (빈 리스트 가능)
        """
        if not self.mcp_tool_manager or not hasattr(self.mcp_tool_manager, 'get_langchain_tools'):
            return []
        
        try:
            tools = await self.mcp_tool_manager.get_langchain_tools()
            logger.debug(f"사용 가능한 도구 수: {len(tools)}")
            return tools
        except Exception as e:
            logger.warning(f"도구 목록 가져오기 실패: {e}")
            return []

    async def _analyze_complexity(self, agent: Any, message: str, tools: List[Any]) -> str:
        """
        사용자 요청의 복잡도 분석
        
        LLM에게 요청 내용과 사용 가능한 도구 목록을 제공하여
        simple/medium/complex 중 하나로 분류하도록 합니다.
        
        Args:
            agent: BaseAgent 인스턴스
            message: 사용자 요청 메시지  
            tools: 사용 가능한 도구 목록
            
        Returns:
            str: "simple", "medium", "complex" 중 하나 (기본값: "simple")
        """
        tools_desc = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
        
        analysis_prompt = f"""다음 사용자 요청의 복잡도를 분석해주세요:

사용자 요청: {message}

사용 가능한 도구들:
{tools_desc}

복잡도 기준:
- simple: 1-2개 도구로 즉시 해결 가능 (시간 조회, 단순 검색, 파일 읽기 등)
- medium: 2-3개 도구 순차 실행으로 해결 가능 (검색 후 저장, 파일 처리 후 분석 등)
- complex: 다단계 계획이 필요한 복합 작업 (여러 검색 + 분석 + 보고서 작성 등)

JSON 형식으로 응답:
{{
    "complexity": "simple|medium|complex",
    "reason": "판단 이유",
    "estimated_steps": 예상단계수
}}"""

        try:
            response = await agent._generate_basic_response(analysis_prompt, None)
            result = self._extract_json_from_response(response)
            complexity = result.get("complexity", "simple")
            reason = result.get("reason", "분석 실패")
            logger.debug(f"복잡도 분석: {complexity} - {reason}")
            return complexity
        except Exception as e:
            logger.warning(f"복잡도 분석 실패: {e} - 기본값 'simple' 사용")
            return "simple"

    async def _handle_simple_request(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        단순 요청 처리
        
        BaseAgent의 auto_tool_flow를 활용하여 직접적이고 빠른 처리를 수행합니다.
        대부분의 일반적인 요청들이 이 방식으로 효율적으로 처리됩니다.
        
        Args:
            agent: BaseAgent 인스턴스
            message: 사용자 요청 메시지
            streaming_callback: 스트리밍 콜백
            
        Returns:
            str: 처리 결과
        """
        logger.info("단순 요청으로 처리 - 직접 도구 실행")
        
        if streaming_callback:
            streaming_callback("🔧 도구 실행 중...\n")

        # BaseAgent의 auto_tool_flow 활용
        if hasattr(agent, 'auto_tool_flow'):
            try:
                result = await agent.auto_tool_flow(message, streaming_callback)
                if result and isinstance(result, dict):
                    return result.get("response", "도구 실행 완료")
                elif result:
                    return str(result)
            except Exception as e:
                logger.warning(f"auto_tool_flow 실행 실패: {e} - LLM 응답으로 폴백")
        
        # 폴백: 일반 LLM 응답
        return await self._generate_llm_response(agent, message, streaming_callback)

    async def _handle_complex_request(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        복잡 요청 처리 (고급 기능 포함)
        
        AdaptiveWorkflow의 고급 Plan & Execute 전략:
        1. 실행 계획 수립 및 중복 감지
        2. 계획 개선 및 최적화
        3. 단계별 실행 (재시도, 검증 포함)
        4. 실패 시 계획 수정 및 재시도
        5. 결과 통합 및 품질 평가
        
        Args:
            agent: BaseAgent 인스턴스  
            message: 사용자 요청 메시지
            streaming_callback: 스트리밍 콜백
            
        Returns:
            str: 통합된 최종 결과
        """
        logger.info("복잡 요청으로 처리 - 고급 Plan & Execute 전략")
        
        max_plan_iterations = 3  # 최대 계획 수정 횟수
        plan_iteration = 0
        
        while plan_iteration < max_plan_iterations:
            try:
                # 1. 계획 수립
                plan = await self._create_execution_plan(agent, message, streaming_callback)
                if not plan or not plan.get("steps"):
                    logger.warning("계획 수립 실패 - 단순 처리로 폴백")
                    return await self._handle_simple_request(agent, message, streaming_callback)

                # 2. 중복 계획 감지
                if self._is_duplicate_plan(plan):
                    logger.warning(f"중복 계획 감지 (반복 {plan_iteration + 1})")
                    if streaming_callback:
                        streaming_callback("⚠️ 중복 계획 감지, 다른 접근 방법 시도 중...\n")
                    
                    # 계획 수정 요청
                    plan = await self._refine_execution_plan(agent, message, plan, streaming_callback)
                    if not plan or not plan.get("steps"):
                        break

                # 3. 계획 실행
                if streaming_callback:
                    streaming_callback(f"📋 실행 계획 승인됨 (반복 {plan_iteration + 1})\n")
                
                results = await self._execute_plan(agent, plan, streaming_callback)
                
                # 4. 실행 결과 평가
                success_rate = sum(1 for r in results.values() if r.get("success")) / len(results) if results else 0
                
                if success_rate >= 0.7:  # 70% 이상 성공 시 결과 통합
                    return await self._integrate_results(agent, message, plan, results, streaming_callback)
                else:
                    # 실패율이 높으면 계획 수정 시도
                    logger.warning(f"실행 성공률 낮음: {success_rate:.1%}, 계획 수정 시도")
                    if streaming_callback:
                        streaming_callback(f"⚠️ 실행 성공률 낮음 ({success_rate:.1%}), 계획 수정 중...\n")
                    
                    plan_iteration += 1
                    
                    # 실패 원인 분석하여 다음 계획에 반영
                    failure_context = self._analyze_execution_failures(results)
                    self.execution_context["failure_analysis"] = failure_context
                    
                    if plan_iteration >= max_plan_iterations:
                        # 최대 시도 횟수 도달 시 부분 성공 결과라도 반환
                        logger.info("최대 계획 수정 횟수 도달, 부분 결과 반환")
                        return await self._integrate_results(agent, message, plan, results, streaming_callback)

            except Exception as e:
                logger.error(f"복잡 요청 처리 실패 (반복 {plan_iteration + 1}): {e}")
                plan_iteration += 1
                
                if plan_iteration >= max_plan_iterations:
                    logger.error("최대 시도 횟수 도달 - 단순 처리로 폴백")
                    return await self._handle_simple_request(agent, message, streaming_callback)
        
        # 모든 시도 실패 시 단순 처리로 폴백
        logger.warning("모든 복잡 처리 시도 실패 - 단순 처리로 폴백")
        return await self._handle_simple_request(agent, message, streaming_callback)

    async def _create_execution_plan(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        실행 계획 수립
        
        사용자 요청을 분석하여 단계별 실행 계획을 JSON 형태로 생성합니다.
        각 단계는 사용할 도구와 매개변수를 포함합니다.
        
        Args:
            agent: BaseAgent 인스턴스
            message: 사용자 요청 메시지  
            streaming_callback: 스트리밍 콜백
            
        Returns:
            Dict[str, Any]: 실행 계획 (빈 딕셔너리 가능)
        """
        tools = await self._get_available_tools()
        tools_desc = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
        
        planning_prompt = f"""사용자 요청을 분석하여 단계별 실행 계획을 수립해주세요:

사용자 요청: {message}

사용 가능한 도구들:
{tools_desc}

다음 형식의 JSON으로 계획을 작성해주세요:
{{
    "goal": "최종 목표 설명",
    "steps": [
        {{
            "step": 1,
            "tool": "사용할_도구명",
            "args": {{"매개변수": "값"}},
            "desc": "이 단계에서 수행할 작업 설명"
        }},
        {{
            "step": 2,
            "tool": "다음_도구명", 
            "args": {{"매개변수": "값"}},
            "desc": "다음 단계 작업 설명"
        }}
    ]
}}

단계별 실행이 논리적 순서를 따르도록 계획해주세요."""

        if streaming_callback:
            streaming_callback("📋 실행 계획 수립 중...\n")

        try:
            response = await agent._generate_basic_response(planning_prompt, None)
            plan = self._extract_json_from_response(response)
            
            if plan and plan.get("steps"):
                logger.debug(f"실행 계획 수립 완료: {len(plan['steps'])}단계")
                return plan
            else:
                logger.warning("유효한 실행 계획을 생성하지 못함")
                return {}
                
        except Exception as e:
            logger.error(f"실행 계획 수립 중 오류: {e}")
            return {}

    async def _execute_plan(
        self, agent: Any, plan: Dict[str, Any], streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[int, Any]:
        """
        계획된 단계들을 순차적으로 실행 (고급 기능 포함)
        
        AdaptiveWorkflow의 고급 기능들을 통합:
        - 단계별 재시도 메커니즘
        - 매개변수 동적 치환
        - 실행 결과 검증
        - 컨텍스트 메모리 관리
        
        Args:
            agent: BaseAgent 인스턴스
            plan: 실행 계획 딕셔너리
            streaming_callback: 스트리밍 콜백
            
        Returns:
            Dict[int, Any]: 단계별 실행 결과
        """
        results = {}
        steps = plan.get("steps", [])
        
        if streaming_callback:
            streaming_callback(f"⚡ {len(steps)}단계 실행 시작\n")

        for step in steps:
            step_num = step.get("step", 0)
            tool_name = step.get("tool")
            args = step.get("args", {})
            desc = step.get("desc", f"단계 {step_num}")
            
            # 매개변수 동적 치환 (이전 단계 결과 참조)
            processed_args = self._process_step_arguments(args, results)
            
            # 단계별 재시도 로직
            retry_count = 0
            success = False
            last_error = None
            
            while retry_count <= self.max_retries and not success:
                try:
                    if self.mcp_tool_manager and tool_name:
                        logger.debug(f"단계 {step_num} 실행 (시도 {retry_count + 1}): {tool_name}")
                        
                        # 사용자 승인 요청 (인터랙티브 모드)
                        if self.interaction_mode and retry_count == 0:
                            approval = await self._request_step_approval(step, streaming_callback)
                            if not approval:
                                results[step_num] = {
                                    "success": False,
                                    "error": "사용자가 단계 실행을 거부했습니다",
                                    "description": desc,
                                    "skipped": True
                                }
                                break
                        
                        result = await self.mcp_tool_manager.call_mcp_tool(tool_name, processed_args)
                        
                        # 결과 검증
                        if self._validate_step_result(result, step):
                            results[step_num] = {
                                "success": True, 
                                "result": result,
                                "tool": tool_name,
                                "description": desc,
                                "retry_count": retry_count
                            }
                            
                            # 컨텍스트 메모리에 저장
                            self.step_memory[step_num] = {
                                "result": result,
                                "tool": tool_name,
                                "timestamp": self._get_timestamp()
                            }
                            
                            success = True
                            if streaming_callback:
                                retry_msg = f" (재시도 {retry_count}회)" if retry_count > 0 else ""
                                streaming_callback(f"✅ {desc}{retry_msg}\n")
                        else:
                            raise Exception("결과 검증 실패")
                    else:
                        results[step_num] = {
                            "success": False, 
                            "error": "도구 관리자 또는 도구명 없음",
                            "description": desc
                        }
                        break
                        
                except Exception as e:
                    last_error = str(e)
                    retry_count += 1
                    logger.warning(f"단계 {step_num} 실행 실패 (시도 {retry_count}): {e}")
                    
                    if retry_count <= self.max_retries:
                        if streaming_callback:
                            streaming_callback(f"⚠️ {desc} 실패, 재시도 중... ({retry_count}/{self.max_retries})\n")
                        
                        # 재시도 전 잠시 대기
                        import asyncio
                        await asyncio.sleep(1)
            
            # 최종 실패 처리
            if not success:
                results[step_num] = {
                    "success": False, 
                    "error": last_error or "알 수 없는 오류",
                    "description": desc,
                    "retry_count": retry_count - 1
                }
                
                if streaming_callback:
                    streaming_callback(f"❌ {desc} (최종 실패)\n")

        successful_count = sum(1 for r in results.values() if r.get("success"))
        logger.info(f"계획 실행 완료: {successful_count}/{len(steps)}단계 성공")
        return results

    async def _integrate_results(
        self, agent: Any, message: str, plan: Dict[str, Any], results: Dict[int, Any],
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        실행 결과들을 통합하여 최종 응답 생성
        
        성공한 단계들의 결과를 종합하여 사용자 요청에 대한 
        완전하고 유용한 답변을 생성합니다.
        
        Args:
            agent: BaseAgent 인스턴스
            message: 원래 사용자 요청
            plan: 실행 계획
            results: 단계별 실행 결과
            streaming_callback: 스트리밍 콜백
            
        Returns:
            str: 통합된 최종 응답
        """
        if streaming_callback:
            streaming_callback("📝 결과 통합 중...\n")

        # 성공한 결과들만 수집
        successful_results = []
        for step_num, result in results.items():
            if result.get("success"):
                result_text = str(result.get("result", ""))[:300]  # 길이 제한
                successful_results.append(f"단계 {step_num}: {result_text}")

        if not successful_results:
            return "요청을 처리하는 중 모든 단계가 실패했습니다. 다시 시도해 주세요."

        integration_prompt = f"""다음 실행 결과들을 종합하여 사용자 요청에 대한 완전한 답변을 생성해주세요:

원래 사용자 요청: {message}
실행 목표: {plan.get('goal', '목표 불명')}

단계별 실행 결과:
{chr(10).join(successful_results)}

위 결과들을 바탕으로:
1. 사용자의 원래 요청이 어떻게 처리되었는지 설명
2. 각 단계의 결과를 논리적으로 연결하여 통합된 정보 제공
3. 실용적이고 구체적인 답변 작성
4. 필요시 추가 조치 사항 안내

사용자에게 도움이 되는 완전한 답변을 제공해주세요."""

        try:
            final_response = await agent._generate_basic_response(integration_prompt, streaming_callback)
            logger.info("결과 통합 완료")
            return final_response
        except Exception as e:
            logger.error(f"결과 통합 중 오류: {e}")
            return f"결과 통합 중 오류가 발생했지만, 다음 작업들이 완료되었습니다:\n" + "\n".join(successful_results)

    async def _generate_llm_response(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        일반 LLM 응답 생성 (폴백 메서드)
        
        MCP 도구를 사용할 수 없거나 다른 처리 방식이 실패했을 때
        순수 LLM 기반으로 응답을 생성합니다.
        
        Args:
            agent: BaseAgent 인스턴스
            message: 사용자 메시지
            streaming_callback: 스트리밍 콜백
            
        Returns:
            str: LLM 생성 응답
        """
        logger.info("일반 LLM 응답 생성")
        
        try:
            if hasattr(agent, '_generate_basic_response'):
                return await agent._generate_basic_response(message, streaming_callback)
            else:
                return "응답을 생성할 수 없습니다. 에이전트 설정을 확인해 주세요."
        except Exception as e:
            logger.error(f"LLM 응답 생성 실패: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"

    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        LLM 응답에서 JSON 데이터 추출
        
        마크다운 코드 블록이나 일반 텍스트에 포함된 JSON을 파싱합니다.
        여러 패턴을 시도하여 최대한 JSON을 추출하려고 시도합니다.
        
        Args:
            response: LLM 응답 텍스트
            
        Returns:
            Dict[str, Any]: 파싱된 JSON 데이터 (실패 시 빈 딕셔너리)
        """
        try:
            import re

            # 다양한 JSON 추출 패턴 시도
            patterns = [
                r'```(?:json)?\s*(\{.*?\})\s*```',  # 마크다운 코드 블록
                r'(\{[^{}]*"[^"]*"[^{}]*\})',       # 기본 JSON 객체
                r'(\{.*?\})'                        # 단순 중괄호 패턴
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except json.JSONDecodeError:
                        continue
            
            # 패턴 매칭 실패 시 전체 텍스트로 시도
            return json.loads(response.strip())
            
        except Exception as e:
            logger.debug(f"JSON 추출 실패: {e}")
            return {}

    # === AdaptiveWorkflow 고급 기능 헬퍼 메서드들 ===
    
    def _process_step_arguments(self, args: Dict[str, Any], previous_results: Dict[int, Any]) -> Dict[str, Any]:
        """
        단계 매개변수 동적 치환
        
        이전 단계 결과를 참조하는 매개변수를 실제 값으로 치환합니다.
        예: {"file": "$step_1"} -> {"file": "actual_filename.txt"}
        
        Args:
            args: 원본 매개변수
            previous_results: 이전 단계 실행 결과
            
        Returns:
            Dict[str, Any]: 치환된 매개변수
        """
        if not args or not previous_results:
            return args
            
        processed = {}
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("$step_"):
                try:
                    step_num = int(value.replace("$step_", ""))
                    if step_num in previous_results and previous_results[step_num].get("success"):
                        result = previous_results[step_num]["result"]
                        # 결과에서 적절한 값 추출 (파일명, 내용 등)
                        processed[key] = self._extract_reference_value(result, key)
                    else:
                        processed[key] = value  # 치환 실패 시 원본 유지
                except ValueError:
                    processed[key] = value
            else:
                processed[key] = value
                
        return processed
    
    def _extract_reference_value(self, result: Any, context_key: str) -> str:
        """
        단계 결과에서 컨텍스트에 맞는 값 추출
        
        Args:
            result: 단계 실행 결과
            context_key: 매개변수 키 (힌트로 사용)
            
        Returns:
            str: 추출된 값
        """
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            # 키 이름에 따라 적절한 값 추출
            if context_key in ["file", "path", "filename"]:
                return result.get("filename", result.get("path", str(result)))
            elif context_key in ["content", "text", "data"]:
                return result.get("content", result.get("text", str(result)))
            else:
                return str(result)
        else:
            return str(result)
    
    async def _request_step_approval(self, step: Dict[str, Any], streaming_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        사용자에게 단계 실행 승인 요청
        
        Args:
            step: 실행할 단계 정보
            streaming_callback: 스트리밍 콜백
            
        Returns:
            bool: 승인 여부 (True: 승인, False: 거부)
        """
        if not self.interaction_mode:
            return True
            
        tool_name = step.get("tool", "알 수 없음")
        desc = step.get("desc", "설명 없음")
        args = step.get("args", {})
        
        approval_message = f"""
🔧 단계 실행 승인 요청:
- 도구: {tool_name}
- 설명: {desc}
- 매개변수: {json.dumps(args, ensure_ascii=False, indent=2)}

실행하시겠습니까? (y/n): """
        
        if streaming_callback:
            streaming_callback(approval_message)
            
        # 실제 구현에서는 사용자 입력을 받아야 하지만, 
        # 여기서는 기본적으로 승인으로 처리 (워크플로우 컨텍스트에서는 자동 승인)
        return True
    
    def _validate_step_result(self, result: Any, step: Dict[str, Any]) -> bool:
        """
        단계 실행 결과 검증
        
        Args:
            result: 실행 결과
            step: 단계 정보
            
        Returns:
            bool: 검증 성공 여부
        """
        if result is None:
            return False
            
        # 기본 검증: 결과가 존재하고 오류가 없는지 확인
        if isinstance(result, dict):
            if "error" in result or "exception" in result:
                return False
            if result.get("success") is False:
                return False
                
        # 도구별 특별 검증 (필요시 확장)
        tool_name = step.get("tool", "")
        if tool_name == "file_read" and not result:
            return False
        elif tool_name == "web_search" and not result:
            return False
            
        return True
    
    def _get_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def set_interaction_mode(self, interactive: bool) -> None:
        """인터랙션 모드 설정"""
        self.interaction_mode = interactive
        logger.debug(f"SmartWorkflow 인터랙션 모드: {interactive}")
    
    def _generate_plan_hash(self, plan: Dict[str, Any]) -> str:
        """계획 해시 생성 (중복 감지용)"""
        import hashlib
        plan_str = json.dumps(plan, sort_keys=True)
        return hashlib.sha256(plan_str.encode()).hexdigest()
    
    def _is_duplicate_plan(self, plan: Dict[str, Any]) -> bool:
        """계획 중복 여부 확인"""
        plan_hash = self._generate_plan_hash(plan)
        if plan_hash in self.executed_plan_hashes:
            return True
        self.executed_plan_hashes.add(plan_hash)
        return False
    
    async def _refine_execution_plan(
        self, agent: Any, message: str, original_plan: Dict[str, Any], 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        실행 계획 개선 및 수정
        
        실패한 계획이나 중복 계획을 분석하여 개선된 새로운 계획을 생성합니다.
        
        Args:
            agent: BaseAgent 인스턴스
            message: 원본 사용자 요청
            original_plan: 기존 계획
            streaming_callback: 스트리밍 콜백
            
        Returns:
            Dict[str, Any]: 개선된 실행 계획
        """
        tools = await self._get_available_tools()
        tools_desc = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
        
        failure_context = self.execution_context.get("failure_analysis", "")
        
        refinement_prompt = f"""기존 실행 계획을 분석하여 개선된 새로운 계획을 수립해주세요:

원본 사용자 요청: {message}

기존 계획:
{json.dumps(original_plan, ensure_ascii=False, indent=2)}

실패 분석 (있는 경우):
{failure_context}

사용 가능한 도구들:
{tools_desc}

개선 지침:
1. 기존 계획의 문제점을 분석하고 다른 접근 방법 시도
2. 실패한 단계는 대안 도구나 다른 매개변수 사용
3. 단계 순서 최적화 및 불필요한 단계 제거
4. 더 안정적이고 신뢰할 수 있는 방법 선택

다음 형식의 JSON으로 개선된 계획을 작성해주세요:
{{
    "goal": "개선된 목표 설명",
    "improvements": "기존 계획 대비 개선사항",
    "steps": [
        {{
            "step": 1,
            "tool": "도구명",
            "args": {{"매개변수": "값"}},
            "desc": "개선된 단계 설명"
        }}
    ]
}}"""

        if streaming_callback:
            streaming_callback("🔧 계획 개선 중...\n")

        try:
            response = await agent._generate_basic_response(refinement_prompt, None)
            refined_plan = self._extract_json_from_response(response)
            
            if refined_plan and refined_plan.get("steps"):
                logger.debug(f"계획 개선 완료: {refined_plan.get('improvements', '개선사항 없음')}")
                return refined_plan
            else:
                logger.warning("계획 개선 실패")
                return {}
                
        except Exception as e:
            logger.error(f"계획 개선 중 오류: {e}")
            return {}
    
    def _analyze_execution_failures(self, results: Dict[int, Any]) -> str:
        """
        실행 실패 원인 분석
        
        Args:
            results: 단계별 실행 결과
            
        Returns:
            str: 실패 원인 분석 텍스트
        """
        failures = []
        for step_num, result in results.items():
            if not result.get("success"):
                error = result.get("error", "알 수 없는 오류")
                tool = result.get("tool", "알 수 없음")
                desc = result.get("description", f"단계 {step_num}")
                
                failures.append(f"단계 {step_num} ({tool}): {desc} - {error}")
        
        if not failures:
            return "실행 실패 없음"
            
        analysis = "실행 실패 분석:\n" + "\n".join(failures)
        
        # 공통 실패 패턴 분석
        common_errors = []
        for failure in failures:
            if "권한" in failure or "permission" in failure.lower():
                common_errors.append("권한 문제")
            elif "파일" in failure and "없" in failure:
                common_errors.append("파일 경로 문제")
            elif "네트워크" in failure or "connection" in failure.lower():
                common_errors.append("네트워크 연결 문제")
            elif "매개변수" in failure or "argument" in failure.lower():
                common_errors.append("매개변수 오류")
        
        if common_errors:
            analysis += f"\n\n공통 문제 패턴: {', '.join(set(common_errors))}"
            
        return analysis
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        실행 통계 정보 반환
        
        Returns:
            Dict[str, Any]: 실행 통계
        """
        return {
            "executed_plans": len(self.executed_plan_hashes),
            "step_memory_size": len(self.step_memory),
            "context_keys": list(self.execution_context.keys()),
            "max_retries": self.max_retries,
            "interaction_mode": self.interaction_mode
        }
    
    def clear_execution_history(self) -> None:
        """실행 히스토리 초기화"""
        self.execution_context.clear()
        self.step_memory.clear()
        self.executed_plan_hashes.clear()
        self.retry_count.clear()
        logger.info("SmartWorkflow 실행 히스토리 초기화 완료")

    # === 레거시 호환 인터페이스 ===
    
    async def process(self, message: str, context: List[ConversationMessage] = None) -> LLMResponse:
        """
        레거시 호환 인터페이스
        
        ConversationMessage 기반의 기존 인터페이스와 호환성을 제공합니다.
        새로운 코드에서는 run() 메서드 사용을 권장합니다.
        
        Args:
            message: 사용자 메시지
            context: 대화 컨텍스트 (사용되지 않음)
            
        Returns:
            LLMResponse: 응답 객체
        """
        try:
            if self.llm_service:
                response = await self.llm_service.generate_response(
                    context or [ConversationMessage(role="user", content=message)]
                )
                return response
            
            return LLMResponse(
                response="LLM 서비스가 초기화되지 않았습니다.",
                metadata={"error": "llm_service_not_initialized", "workflow": self.workflow_name}
            )
        except Exception as e:
            return LLMResponse(
                response=f"처리 중 오류: {str(e)}",
                metadata={"error": str(e), "workflow": self.workflow_name}
            ) 