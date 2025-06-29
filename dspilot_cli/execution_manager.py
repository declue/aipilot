#!/usr/bin/env python3
"""
DSPilot CLI 실행 관리 모듈 (ExecutionManager)
===========================================

이 모듈은 DSPilot CLI 의 **계획→실행→응답 생성** 전 과정을 오케스트레이션
합니다. 내부적으로 세 개의 서브컴포넌트(PlanningService, StepExecutor,
ResponseGenerator)를 사용하여 MVC 패턴의 *Controller* 역할을 수행합니다.

컴포넌트 구조
-------------
```mermaid
flowchart LR
    U[User Prompt] --> EM(ExecutionManager)
    EM --> PS[PlanningService]
    PS -->|ExecutionPlan| EM
    EM --> SE[StepExecutor]
    SE -->|StepResults| EM
    EM --> RG[ResponseGenerator]
    RG -->|Final Answer| U
```

시퀀스 다이어그램 (대화형 모드)
------------------------------
```mermaid
sequenceDiagram
    participant User
    participant EM as ExecutionManager
    participant PS as PlanningService
    participant SE as StepExecutor
    participant RG as ResponseGenerator
    User->>EM: analyze_request_and_plan()
    EM->>PS: plan
    PS-->>EM: ExecutionPlan
    loop steps
        EM->>SE: execute_step()
        SE-->>EM: result
    end
    EM->>RG: generate_final_response()
    RG-->>User: answer
```

주요 메서드
-----------
- analyze_request_and_plan(): 도구 필요 여부 판단 및 계획 수립
- execute_interactive_plan(): 단계별 실행 + 결과 취합 + 최종 응답

테스트 전략
-----------
1. PlanningService, StepExecutor, ResponseGenerator 를 **mock** 하여 순서 및
   데이터 흐름을 검증 (단위 테스트)
2. 실제 MCP 도구에 연결한 **통합 테스트** 로 계획→실행 성공 경로 확인
"""

import dataclasses  # 로컬 임포트로 순환 의존성 회피
from typing import Any, Callable, Dict, List, Optional

import dspilot_core.instructions.prompt_manager as prompt_manager
from dspilot_cli.constants import Defaults, ExecutionPlan
from dspilot_cli.execution.step_executor import StepExecutor
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager
from dspilot_cli.plan_evaluator import PlanEvaluator
from dspilot_cli.plan_history_manager import PlanHistoryManager
from dspilot_cli.plan_refiner import PlanRefiner
from dspilot_cli.planning_service import PlanningService
from dspilot_cli.response_generator import ResponseGenerator
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager


class ExecutionManager:
    """
    계획 수립 및 실행 관리를 담당하는 클래스 (리팩토링됨)
    
    SOLID 원칙 적용:
    - 전체 계획 실행 조율만 담당 (SRP)
    - 세부 실행은 분리된 서비스들에게 위임 (DIP)
    """

    def __init__(
            self,
            output_manager: OutputManager,
            interaction_manager: InteractionManager,
            llm_agent: BaseAgent,
            mcp_tool_manager: MCPToolManager,
            validate_mode: str = Defaults.VALIDATE_MODE,
            max_step_retries: int = Defaults.MAX_STEP_RETRIES
    ) -> None:
        """
        실행 관리자 초기화

        Args:
            output_manager: 출력 관리자
            interaction_manager: 상호작용 관리자
            llm_agent: LLM 에이전트
            mcp_tool_manager: MCP 도구 관리자
            validate_mode: 결과 검증 모드
            max_step_retries: 최대 단계 재시도 횟수
        """
        self.output_manager = output_manager
        self.interaction_manager = interaction_manager
        self.llm_agent = llm_agent
        self.mcp_tool_manager = mcp_tool_manager

        # 분리된 서비스들 초기화 (DIP 적용)
        self.planning_service = PlanningService(
            output_manager, llm_agent, mcp_tool_manager)
        self.step_executor = StepExecutor(
            output_manager, interaction_manager, llm_agent, mcp_tool_manager,
            max_step_retries, validate_mode)
        self.response_generator = ResponseGenerator(
            output_manager, llm_agent)

        # 계획 평가기 (중복/오류 탐지)
        self.plan_history_manager = PlanHistoryManager()
        self.plan_evaluator = PlanEvaluator(self.plan_history_manager)

        # 계획 리파이너
        self.plan_refiner = PlanRefiner()

        # 프롬프트 관리자 (테스트 편의성 위해 모듈 import 방식 사용)
        self.prompt_manager = prompt_manager.get_default_prompt_manager()

    async def analyze_request_and_plan(self, user_message: str) -> Optional[ExecutionPlan]:
        """
        요청 분석 및 실행 계획 수립

        Args:
            user_message: 사용자 메시지

        Returns:
            실행 계획 (도구가 필요하지 않으면 None)
        """
        plan_raw = await self.planning_service.analyze_request_and_plan(user_message)

        if not plan_raw:
            return None

        refined_plan, _ = self.plan_refiner.refine(plan_raw)
        return refined_plan

    async def execute_interactive_plan(self, plan: ExecutionPlan, original_prompt: str,
                                       streaming_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        대화형 계획 실행

        Args:
            plan: 실행 계획
            original_prompt: 원본 프롬프트
            streaming_callback: 스트리밍 콜백 함수
            
        Returns:
            Dict[str, Any]: {
               "step_results": Dict[int, Any],
               "errors": List[str]
            }
        """
        if not plan.steps:
            return {"step_results": {}, "errors": []}

        self.output_manager.print_execution_plan(dataclasses.asdict(plan))
        step_results: Dict[int, Any] = {}
        errors: List[str] = []

        # 각 단계 실행
        for step in plan.steps:
            success = await self.step_executor.execute_step(step, step_results, original_prompt)
            if not success:
                # 중단된 경우 오류로 간주하고 종료
                errors.append(f"단계 {step.step} 중단")
                break

        # 최종 결과 분석 및 출력
        await self.response_generator.generate_final_response(
            original_prompt, step_results, streaming_callback)

        # 결과 내 오류 탐지 – PlanEvaluator 공통 로직 사용
        errors.extend(self.plan_evaluator.detect_errors_in_results(step_results))

        return {"step_results": step_results, "errors": errors}
