#!/usr/bin/env python3
"""
DSPilot CLI 실행 관리 모듈
"""

import json
from typing import Any, Dict, List, Optional

from dspilot_cli.constants import (
    ANALYSIS_PROMPT_TEMPLATE,
    FINAL_ANALYSIS_PROMPT_TEMPLATE,
    Defaults,
    ExecutionPlan,
    ExecutionStep,
    UserChoiceType,
)
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager
from dspilot_core.llm.models.conversation_message import ConversationMessage


class ExecutionManager:
    """계획 수립 및 실행 관리를 담당하는 클래스"""

    def __init__(
        self,
        output_manager: OutputManager,
        interaction_manager: InteractionManager,
        llm_agent: BaseAgent,
        mcp_tool_manager: MCPToolManager,
    ) -> None:
        """
        실행 관리자 초기화
        
        Args:
            output_manager: 출력 관리자
            interaction_manager: 상호작용 관리자
            llm_agent: LLM 에이전트
            mcp_tool_manager: MCP 도구 관리자
        """
        self.output_manager = output_manager
        self.interaction_manager = interaction_manager
        self.llm_agent = llm_agent
        self.mcp_tool_manager = mcp_tool_manager

    async def analyze_request_and_plan(self, user_message: str) -> Optional[ExecutionPlan]:
        """
        요청 분석 및 실행 계획 수립
        
        Args:
            user_message: 사용자 메시지
            
        Returns:
            실행 계획 (도구가 필요하지 않으면 None)
        """
        try:
            # 사용 가능한 도구 목록 확인
            available_tools = await self._get_available_tools()
            if not available_tools:
                return None

            # 도구 목록 생성
            tools_desc = "\n".join([
                f"- {tool.name}: {tool.description}"
                for tool in available_tools
            ])

            # 계획 수립 프롬프트
            analysis_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
                user_message=user_message,
                tools_desc=tools_desc
            )

            context = [ConversationMessage(role="user", content=analysis_prompt)]
            response = await self.llm_agent.llm_service.generate_response(context)

            # JSON 파싱
            plan_data = self._parse_plan_response(response.response)
            if plan_data and plan_data.get("need_tools", False):
                return self._create_execution_plan(plan_data.get("plan", {}))

        except Exception as e:
            self.output_manager.log_if_debug(f"계획 수립 실패: {e}", "warning")

        return None

    async def execute_interactive_plan(self, plan: ExecutionPlan, original_prompt: str) -> None:
        """
        대화형 계획 실행
        
        Args:
            plan: 실행 계획
            original_prompt: 원본 프롬프트
        """
        if not plan.steps:
            return

        self.output_manager.print_execution_plan(plan.__dict__)
        step_results: Dict[int, Any] = {}

        for step in plan.steps:
            if not await self._execute_step(step, step_results):
                return

        # 최종 결과 분석 및 출력
        await self._generate_final_response(original_prompt, step_results)

    async def _execute_step(self, step: ExecutionStep, step_results: Dict[int, Any]) -> bool:
        """
        단일 단계 실행
        
        Args:
            step: 실행 단계
            step_results: 이전 단계 결과들
            
        Returns:
            계속 진행 여부
        """
        self.output_manager.print_step_info(step.step, step.description)

        # 사용자 확인 (full-auto 모드가 아닌 경우)
        user_choice = self.interaction_manager.get_user_confirmation(
            step.confirm_message, step.tool_name, step.arguments
        )

        if user_choice == UserChoiceType.SKIP:
            self.output_manager.print_step_skipped(step.step)
            return True
        elif user_choice == UserChoiceType.MODIFY:
            # 사용자가 수정을 원하는 경우
            new_prompt = self.interaction_manager.get_new_request()
            if new_prompt:
                # 새로운 요청으로 처리 (이것은 외부에서 처리해야 함)
                # 여기서는 단순히 실행을 중단
                return False
        elif user_choice == UserChoiceType.CANCEL:
            self.output_manager.print_task_cancelled()
            return False

        # 도구 실행
        try:
            self.output_manager.print_step_execution(step.tool_name)

            # 이전 단계 결과 참조 처리
            processed_args = self._process_step_arguments(step.arguments, step_results)

            # 도구 실행
            result = await self.mcp_tool_manager.call_mcp_tool(step.tool_name, processed_args)
            step_results[step.step] = result

            self.output_manager.print_step_completed(step.step)
            return True

        except Exception as e:
            error_msg = str(e)
            self.output_manager.print_step_error(step.step, error_msg)

            # 오류 발생 시 사용자에게 계속 진행할지 묻기
            if not self.interaction_manager.get_continue_confirmation():
                return False

        return True

    async def _get_available_tools(self) -> List[Any]:
        """사용 가능한 도구 목록 가져오기"""
        available_tools = []
        if self.mcp_tool_manager and hasattr(self.mcp_tool_manager, 'get_langchain_tools'):
            try:
                available_tools = await self.mcp_tool_manager.get_langchain_tools()
            except Exception as e:
                self.output_manager.log_if_debug(f"도구 목록 가져오기 실패: {e}", "warning")
        return available_tools

    def _parse_plan_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """응답에서 JSON 계획 파싱"""
        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _create_execution_plan(self, plan_data: Dict[str, Any]) -> ExecutionPlan:
        """계획 데이터로부터 ExecutionPlan 객체 생성"""
        steps = []
        for step_data in plan_data.get("steps", []):
            step = ExecutionStep(
                step=step_data.get("step", 0),
                description=step_data.get("description", ""),
                tool_name=step_data.get("tool_name", ""),
                arguments=step_data.get("arguments", {}),
                confirm_message=step_data.get("confirm_message", "")
            )
            steps.append(step)

        return ExecutionPlan(
            description=plan_data.get("description", "도구 실행 계획"),
            steps=steps
        )

    def _process_step_arguments(self, arguments: Dict[str, Any], step_results: Dict[int, Any]) -> Dict[str, Any]:
        """
        단계 매개변수 처리 (이전 단계 결과 참조)
        
        Args:
            arguments: 원본 매개변수
            step_results: 이전 단계 결과들
            
        Returns:
            처리된 매개변수
        """
        processed = {}

        for key, value in arguments.items():
            if isinstance(value, str) and value.startswith("$step_"):
                # 이전 단계 결과 참조
                try:
                    step_num = int(value.split("_")[1])
                    if step_num in step_results:
                        processed[key] = step_results[step_num]
                    else:
                        processed[key] = value  # 참조 실패 시 원본 유지
                except (ValueError, IndexError):
                    processed[key] = value
            else:
                processed[key] = value

        return processed

    async def _generate_final_response(self, original_prompt: str, step_results: Dict[int, Any]) -> None:
        """
        최종 응답 생성
        
        Args:
            original_prompt: 원본 프롬프트
            step_results: 단계 실행 결과들
        """
        if not step_results:
            return

        # 결과 요약
        results_summary = "\n".join([
            f"단계 {step}: {str(result)[:Defaults.RESULT_SUMMARY_MAX_LENGTH]}..." 
            if len(str(result)) > Defaults.RESULT_SUMMARY_MAX_LENGTH 
            else f"단계 {step}: {result}"
            for step, result in step_results.items()
        ])

        # 최종 분석 프롬프트
        final_prompt = FINAL_ANALYSIS_PROMPT_TEMPLATE.format(
            original_prompt=original_prompt,
            results_summary=results_summary
        )

        try:
            context = [ConversationMessage(role="user", content=final_prompt)]
            response = await self.llm_agent.llm_service.generate_response(context)

            response_data = {
                "response": response.response,
                "used_tools": list(step_results.keys()),
                "step_results": step_results
            }
            self.output_manager.print_response(
                response.response, 
                response_data.get("used_tools", [])
            )

        except Exception as e:
            self.output_manager.log_if_debug(f"최종 응답 생성 실패: {e}", "error")
            # 폴백: 원시 결과 출력
            self.output_manager.print_success("작업 완료")
            self.output_manager.print_info(f"결과: {results_summary}") 