#!/usr/bin/env python3
"""
DSPilot CLI 단계 실행 서비스
"""

import json
from typing import Any, Dict

from dspilot_cli.constants import Defaults, ExecutionStep, UserChoiceType
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager


class StepExecutor:
    """단일 단계 실행 및 검증을 담당하는 서비스"""

    def __init__(self, output_manager: OutputManager,
                 interaction_manager: InteractionManager,
                 llm_agent: BaseAgent,
                 mcp_tool_manager: MCPToolManager,
                 max_step_retries: int = Defaults.MAX_STEP_RETRIES,
                 validate_mode: str = Defaults.VALIDATE_MODE) -> None:
        """
        단계 실행자 초기화

        Args:
            output_manager: 출력 관리자
            interaction_manager: 상호작용 관리자
            llm_agent: LLM 에이전트
            mcp_tool_manager: MCP 도구 관리자
            max_step_retries: 최대 단계 재시도 횟수
            validate_mode: 결과 검증 모드
        """
        self.output_manager = output_manager
        self.interaction_manager = interaction_manager
        self.llm_agent = llm_agent
        self.mcp_tool_manager = mcp_tool_manager
        self.max_step_retries = max_step_retries

        # 결과 검증기 초기화
        self._initialize_validators(validate_mode)

    def _initialize_validators(self, validate_mode: str) -> None:
        """검증기 초기화 (Private Method - SRP 준수)"""
        try:
            from dspilot_core.llm.utils.argument_fixer import (
                GenericArgumentFixer,  # pylint: disable=import-error
            )
            from dspilot_core.llm.utils.result_validator import (
                GenericResultValidator,  # pylint: disable=import-error
            )
            self.result_validator = GenericResultValidator(
                llm_service=self.llm_agent.llm_service,
                mode=validate_mode
            )
            self.argument_fixer = GenericArgumentFixer(
                self.llm_agent.llm_service)
        except Exception:  # noqa: broad-except
            self.result_validator = None
            self.argument_fixer = None

    async def execute_step(self, step: ExecutionStep, 
                          step_results: Dict[int, Any], 
                          original_prompt: str) -> bool:
        """
        단일 단계 실행

        Args:
            step: 실행 단계
            step_results: 이전 단계 결과들
            original_prompt: 원본 프롬프트

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
            retries = 0
            while retries <= self.max_step_retries:
                self.output_manager.print_step_execution(step.tool_name)

                # 이전 단계 결과 참조 처리
                processed_args = self._process_step_arguments(
                    step.arguments, step_results)

                # 도구 실행
                try:
                    result = await self.mcp_tool_manager.call_mcp_tool(step.tool_name, processed_args)
                    exec_error = ""
                except Exception as exec_e:
                    exec_error = str(exec_e)
                    result = json.dumps({"error": exec_error})

                # 결과 검증 (옵션)
                needs_retry = False
                if self.result_validator:
                    eval_res = await self.result_validator.evaluate(
                        user_prompt=original_prompt,
                        tool_name=step.tool_name,
                        tool_args=processed_args,
                        raw_result=result
                    )
                    needs_retry = self.result_validator.needs_retry(eval_res)

                    # ------------------------------------------------------------------
                    # LLM 검증 결과를 해석할 수 없을 때(parse_error 등) -----------------
                    # ------------------------------------------------------------------
                    # LLM 응답 파싱이 실패하면 eval_res["note"] == "parse_error" 로 세팅된다.
                    # 이 경우 결과가 크게 문제 없어 보이고(exec_error 비어 있음) 동일한 재시도는
                    # 의미가 없을 수 있다. 반복을 최소화하기 위해, 파싱 실패이면서 실행 오류가
                    # 없으면 성공으로 간주한다.
                    if eval_res.get("note") == "parse_error" and not exec_error:
                        needs_retry = False

                    if needs_retry:
                        self.output_manager.print_warning(
                            f"⚠️ 결과 신뢰도 낮음 → 재시도 {retries+1}/{self.max_step_retries}")

                # 실행 예외가 있었으면 무조건 retry
                if exec_error:
                    needs_retry = True

                if not needs_retry:
                    step_results[step.step] = result
                    self.output_manager.print_step_completed(step.step)
                    return True

                retries += 1

                # 동일한 오류 메시지가 반복될 경우 조기 중단 ------------------------
                if retries > 1 and exec_error and exec_error == step_results.get(f"_last_error_{step.step}"):
                    self.output_manager.print_warning("⚠️ 동일 오류 반복 → 추가 재시도 중단")
                    return False

                # 오류 메시지 기록
                if exec_error:
                    step_results[f"_last_error_{step.step}"] = exec_error

                # 매개변수 수정 시도
                if self.argument_fixer:
                    fixed = await self.argument_fixer.suggest(
                        user_prompt=original_prompt,
                        tool_name=step.tool_name,
                        original_args=processed_args,
                        error_msg=exec_error or "low_confidence_result"
                    )
                    if fixed:
                        processed_args.update(fixed)
                        self.output_manager.print_info(
                            f"🔧 파라미터 자동 수정 적용: {fixed}")
                        continue

            # 재시도 모두 실패 → 오류 처리
            self.output_manager.print_step_error(step.step, "결과 검증 실패")
            return False
        except Exception as e:
            error_msg = str(e)
            self.output_manager.print_step_error(step.step, error_msg)
            return False

    def _process_step_arguments(self,
                                arguments: Dict[str, Any],
                                step_results: Dict[int, Any]) -> Dict[str, Any]:
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