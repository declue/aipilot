"""High-level step orchestration service.

StepExecutor 는 하나의 plan step 을 실제 실행한다. 기존 거대한 구현에서
도구 실행/매개변수 치환/결과 검증을 별도 클래스로 위임하여 SRP 와 OCP 준수.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from dspilot_cli.constants import Defaults, ExecutionStep, UserChoiceType
from dspilot_cli.execution.argument_processor import ArgumentProcessor
from dspilot_cli.execution.success_evaluator import SuccessEvaluator
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager
from dspilot_core.llm.utils.argument_fixer import GenericArgumentFixer
from dspilot_core.llm.utils.result_validator import GenericResultValidator

__all__ = ["StepExecutor"]


class StepExecutor:  # pylint: disable=too-many-instance-attributes
    """단일 단계 실행 및 검증을 담당하는 Facade 클래스."""

    def __init__(
        self,
        output_manager: OutputManager,
        interaction_manager: InteractionManager,
        llm_agent: BaseAgent,
        mcp_tool_manager: MCPToolManager,
        max_step_retries: int = Defaults.MAX_STEP_RETRIES,
        validate_mode: str = Defaults.VALIDATE_MODE,
        argument_processor: Optional[ArgumentProcessor] = None,
        success_evaluator: Optional[SuccessEvaluator] = None,
    ) -> None:
        self.output_manager = output_manager
        self.interaction_manager = interaction_manager
        self.llm_agent = llm_agent
        self.mcp_tool_manager = mcp_tool_manager
        self.max_step_retries = max_step_retries

        self.argument_processor = argument_processor or ArgumentProcessor()
        self.success_evaluator = success_evaluator or SuccessEvaluator()

        # 외부 LLM 기반 유틸 초기화
        try:
            self.result_validator = GenericResultValidator(
                llm_service=llm_agent.llm_service, mode=validate_mode
            )
            self.argument_fixer = GenericArgumentFixer(llm_agent.llm_service)
        except Exception:  # noqa: broad-except
            self.result_validator = None
            self.argument_fixer = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def execute_step(
        self,
        step: ExecutionStep,
        step_results: Dict[int, Any],
        original_prompt: str,
    ) -> bool:
        """Run a single execution step and update `step_results`."""
        self.output_manager.print_step_info(step.step, step.description)

        # ------------------------------------------------------------------
        # 1. 사용자 확인
        # ------------------------------------------------------------------
        user_choice = self.interaction_manager.get_user_confirmation(
            step.confirm_message, step.tool_name, step.arguments
        )

        if user_choice == UserChoiceType.SKIP:
            self.output_manager.print_step_skipped(step.step)
            return True
        if user_choice == UserChoiceType.MODIFY:
            new_prompt = self.interaction_manager.get_new_request()
            return False if new_prompt else True
        if user_choice == UserChoiceType.CANCEL:
            self.output_manager.print_task_cancelled()
            return False

        # ------------------------------------------------------------------
        # 2. 도구 실행 + 재시도 루프
        # ------------------------------------------------------------------
        retries = 0
        last_exec_error = ""
        exec_error = ""  # 루프 외부에서도 접근 가능하도록 초기화
        while retries <= self.max_step_retries:
            self.output_manager.print_step_execution(step.tool_name)

            # 2.1 매개변수 치환
            processed_args = self.argument_processor.process(step.arguments, step_results)
            self.output_manager.log_if_debug(f"🔍 처리된 매개변수: {processed_args}")

            # 2.2 도구 호출
            try:
                result = await self.mcp_tool_manager.call_mcp_tool(step.tool_name, processed_args)
                exec_error = ""
                self.output_manager.log_if_debug(
                    f"🔍 실행 결과: {str(result)[:200]}... (type={type(result)})"
                )
            except Exception as exec_e:  # noqa: broad-except
                exec_error = str(exec_e)
                self.output_manager.log_if_debug(f"🔍 도구 실행 예외: {exec_error}")
                result = json.dumps({"error": exec_error})

            # ------------------------------------------------------
            # 2.3 결과 검증 및 오류 메시지 즉시 출력
            # ------------------------------------------------------
            # 결과가 명시적으로 success=False 이면 우선 실패로 간주
            needs_retry = False
            explicit_fail = False

            try:
                parsed_result = json.loads(result) if isinstance(result, str) else result
                if isinstance(parsed_result, dict) and parsed_result.get("success") is False:
                    explicit_fail = True
                    exec_error = parsed_result.get("error", "도구가 success=False 반환") or exec_error
            except Exception:  # noqa: broad-except
                pass

            # 실행 예외 또는 success False 가 확인된 경우 즉시 사용자에 출력
            error_printed = False
            if exec_error and not error_printed:
                self.output_manager.print_step_error(step.step, exec_error)
                error_printed = True

            if self.result_validator is not None:
                eval_res = await self.result_validator.evaluate(
                    user_prompt=original_prompt,
                    tool_name=step.tool_name,
                    tool_args=processed_args,
                    raw_result=result,
                )
                needs_retry = self.result_validator.needs_retry(eval_res)

                if eval_res.get("note") == "parse_error" and not exec_error:
                    needs_retry = False

                if not exec_error and self.success_evaluator.is_successful(result, step.tool_name):
                    needs_retry = False
                elif explicit_fail:
                    needs_retry = True

                if needs_retry:
                    self.output_manager.print_warning(
                        f"⚠️ 결과 신뢰도 낮음 → 재시도 {retries + 1}/{self.max_step_retries}"
                    )

            if exec_error:
                needs_retry = True

            # 2.4 성공 여부, 재시도 판단 ---------------------------------
            if not needs_retry:
                step_results[step.step] = result
                self.output_manager.print_step_completed(step.step)
                return True

            # 2.5 실패 → 재시도 준비
            retries += 1
            if retries > 1 and exec_error and exec_error == last_exec_error:
                self.output_manager.print_warning("⚠️ 동일 오류 반복 → 추가 재시도 중단")
                # 동일 오류 반복 – 사용자에게 오류 사유 출력 후 실패 처리
                if exec_error and not error_printed:
                    self.output_manager.print_step_error(step.step, exec_error or "동일 오류 반복")
                    error_printed = True
                return False
            last_exec_error = exec_error

            # 2.6 ArgFixer 로 매개변수 수정 시도
            if self.argument_fixer is not None:
                fixed_args = await self.argument_fixer.suggest(
                    user_prompt=original_prompt,
                    tool_name=step.tool_name,
                    original_args=processed_args,
                    error_msg=exec_error or "low_confidence_result",
                )
                if fixed_args:
                    step.arguments.update(fixed_args)  # 이후 루프에서 사용
                    self.output_manager.print_info(f"🔧 파라미터 자동 수정 적용: {fixed_args}")

        # 모든 재시도 실패
        # 마지막 단계 실패 시 – 이미 exec_error 가 출력된 경우 중복 방지
        if not exec_error:
            if exec_error and not error_printed:
                self.output_manager.print_step_error(step.step, "결과 검증 실패")
                error_printed = True
        return False 