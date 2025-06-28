#!/usr/bin/env python3
"""
DSPilot CLI 실행 관리 모듈 (리팩토링됨)
"""

import dataclasses  # 로컬 임포트로 순환 의존성 회피
import json
import re
from typing import Any, Callable, Dict, List, Optional

import dspilot_core.instructions.prompt_manager as prompt_manager
from dspilot_cli.constants import Defaults, ExecutionPlan
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager
from dspilot_cli.planning_service import PlanningService
from dspilot_cli.response_generator import ResponseGenerator
from dspilot_cli.step_executor import StepExecutor
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
        return await self.planning_service.analyze_request_and_plan(user_message)

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

        # 결과 내 오류 탐지
        errors.extend(self._detect_errors_in_results(step_results))

        return {"step_results": step_results, "errors": errors}

    def _detect_errors_in_results(self, step_results: Dict[int, Any]) -> List[str]:
        """결과 내 오류 키워드 탐지"""
        errors = []
        for raw in step_results.values():
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and data.get("error"):
                    errors.append(str(data.get("error")))
            except Exception:
                if re.search(r"error", str(raw), re.IGNORECASE):
                    errors.append(str(raw))
        return errors
