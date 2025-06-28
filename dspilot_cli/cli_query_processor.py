#!/usr/bin/env python3
"""
DSPilot CLI 쿼리 처리 프로세서
"""

import hashlib
import json
from typing import Callable, Optional

from dspilot_cli.conversation_manager import ConversationManager
from dspilot_cli.execution_manager import ExecutionManager
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager


# pylint: disable=not-callable

class QueryProcessor:
    """사용자 쿼리 처리를 담당하는 클래스"""

    def __init__(self, output_manager: OutputManager,
                 conversation_manager: ConversationManager,
                 interaction_manager: InteractionManager,
                 max_iterations: int) -> None:
        """
        쿼리 프로세서 초기화

        Args:
            output_manager: 출력 관리자
            conversation_manager: 대화 관리자
            interaction_manager: 상호작용 관리자
            max_iterations: 최대 반복 횟수
        """
        self.output_manager = output_manager
        self.conversation_manager = conversation_manager
        self.interaction_manager = interaction_manager
        self.max_iterations = max_iterations
        self.execution_manager: Optional[ExecutionManager] = None

        # 외부에서 설정할 콜백들
        # 쿼리 처리 완료 콜백
        self.on_query_processed: Optional[Callable[[], None]] = None

    def set_execution_manager(self, execution_manager: ExecutionManager) -> None:
        """실행 관리자를 설정합니다."""
        self.execution_manager = execution_manager

    async def process_query(self, user_input: str) -> None:
        """
        사용자 질문 처리

        Args:
            user_input: 사용자 입력
        """
        if not self.execution_manager:
            self.output_manager.print_error("실행 관리자가 초기화되지 않았습니다.")
            return

        iterations = 0
        current_input = user_input
        continue_prompt = "계속 진행해줘"
        executed_plans = set()

        while iterations < self.max_iterations:
            try:
                # 사용자 입력을 히스토리에 추가 (반복 포함)
                if iterations == 0:
                    self.conversation_manager.add_to_history(
                        "user", current_input)

                self.output_manager.log_if_debug(
                    f"=== CLI: 대화형 Agent 처리 시작 (iteration {iterations + 1}/{self.max_iterations}): '{current_input}' ===")

                # 에이전트 실행 (계획 수립 및 실행 포함)
                result_flags = await self._run_interactive_agent(current_input)
                has_errors = result_flags.get("has_errors", False)
                plan_executed = result_flags.get("has_plan", False)

                # ------------------------------------------------------------------
                # 엄격한 오류 판단 - 실제 실행 실패만 오류로 간주 -------------------
                # ------------------------------------------------------------------
                # LLM이 "콘텐츠 부족" 등으로 판단하더라도, 실제 도구 실행이 성공했다면
                # 오류가 아닌 것으로 간주하여 불필요한 재시도를 방지합니다.
                actual_execution_errors = []
                if isinstance(result_flags, dict) and "steps" in result_flags:
                    for step_result in result_flags["steps"]:
                        if isinstance(step_result, dict):
                            exec_error = step_result.get("exec_error", "")
                            if exec_error and exec_error.strip():
                                actual_execution_errors.append(exec_error)

                # 실제 실행 오류가 없다면 has_errors를 False로 강제 설정
                if not actual_execution_errors:
                    has_errors = False
                    self.output_manager.print_success("✅ 모든 단계 실행 완료 - 작업 성공")

                # --------------------------------------------------------------
                # 오류가 없으면 즉시 루프 종료 ---------------------------------
                # --------------------------------------------------------------
                if not has_errors:
                    break

                # 오류가 있을 때만 추가 계획 분석
                enhanced_prompt = self.conversation_manager.build_enhanced_prompt("")
                next_plan = await self.execution_manager.analyze_request_and_plan(enhanced_prompt)

                # ------------------------------------------------------------------
                # 반복 종료 조건 강화 ----------------------------------------------
                # ------------------------------------------------------------------
                if next_plan is None or (plan_executed and not has_errors):
                    # 1) LLM이 추가 계획을 제시하지 않은 경우
                    # 2) 직전 계획이 오류 없이 성공 → LLM이 계획을 또 제시하더라도   
                    #    동일/유사 작업 반복일 가능성이 높으므로 종료
                    if next_plan is None and has_errors:
                        # 오류가 있었지만 추가 계획이 없을 때: 다른 방법 시도 요청
                        iterations += 1
                        current_input = "다른 방법으로 시도해줘"
                        continue
                    break  # 추가 계획이 없으면 종료

                # 중복 계획 체크
                plan_hash = self._generate_plan_hash(next_plan)
                if plan_hash in executed_plans:
                    self.output_manager.print_warning("⚠️ 중복 계획 감지 → 종료")
                    break
                executed_plans.add(plan_hash)

                # 다음 계획 실행
                iterations += 1
                current_input = f"다음 계획을 실행해주세요: {next_plan.description}"

            except Exception as e:
                self.output_manager.log_if_debug(
                    f"=== CLI: 대화형 Agent 처리 실패: {e} ===", "error")
                self.output_manager.print_error(f"처리 중 오류가 발생했습니다: {str(e)}")
                break

        if iterations >= self.max_iterations:
            self.output_manager.print_warning(
                f"최대 반복 횟수({self.max_iterations})에 도달했습니다. 작업을 종료합니다.")

        # 쿼리 처리 완료 콜백 호출
        if self.on_query_processed and callable(self.on_query_processed):
            self.on_query_processed()  # type: ignore[attr-defined,call-arg]

    async def _run_interactive_agent(self, user_input: str) -> dict:
        """
        대화형 Agent 실행

        Args:
            user_input: 사용자 입력

        Returns:
            dict: 실행된 계획이 있었는지 여부 (True: 계획 실행, False: 직접 응답)
        """
        if not self.execution_manager:
            self.output_manager.print_error("실행 관리자가 초기화되지 않았습니다.")
            return {
                "has_plan": False,
                "has_errors": False
            }

        # 이전 대화 맥락을 포함한 프롬프트 생성
        enhanced_prompt = self.conversation_manager.build_enhanced_prompt(
            user_input)
        self.output_manager.log_if_debug(
            f"=== CLI: 향상된 프롬프트 생성: '{enhanced_prompt[:100]}...' ==="
        )

        # 스트리밍 콜백 설정
        streaming_callback = None
        if hasattr(self.output_manager, 'stream_mode') and self.output_manager.stream_mode:
            streaming_callback = self.output_manager.handle_streaming_chunk

        # 1단계: 요청 분석 및 계획 수립
        plan = await self.execution_manager.analyze_request_and_plan(enhanced_prompt)

        if not plan:
            # 도구가 필요하지 않은 경우 직접 응답
            # system_manager를 통해 llm_agent 가져오기 (임시 해결책)
            # 더 나은 방법은 의존성 주입을 통해 llm_agent를 직접 받는 것
            if hasattr(self.execution_manager, '_llm_agent'):
                llm_agent = self.execution_manager._llm_agent

                if hasattr(self.output_manager, 'stream_mode') and self.output_manager.stream_mode:
                    self.output_manager.start_streaming_output()

                response_data = await llm_agent.generate_response(enhanced_prompt, streaming_callback)

                if hasattr(self.output_manager, 'stream_mode') and self.output_manager.stream_mode:
                    self.output_manager.finish_streaming_output()

                await self._display_response(response_data)
            return {
                "has_plan": False,
                "has_errors": False
            }

        # 2단계: 대화형 실행 (스트리밍 콜백 전달)
        result_info = await self.execution_manager.execute_interactive_plan(plan, enhanced_prompt, streaming_callback)
        has_errors = bool(result_info.get("errors")) if isinstance(
            result_info, dict) else False

        # errors logged as pending actions also
        if has_errors:
            for err in result_info.get("errors", []):
                self.output_manager.print_warning(f"도구 실행 오류 감지: {err}")

        return {
            "has_plan": True,
            "has_errors": has_errors
        }

    async def _display_response(self, response_data: dict) -> None:
        """
        AI 응답 출력

        Args:
            response_data: 응답 데이터
        """
        response = response_data.get("response", "응답을 생성할 수 없습니다.")
        used_tools = response_data.get("used_tools", [])

        # 스트리밍 모드가 아닌 경우에만 응답 출력 (스트리밍 모드에서는 이미 출력됨)
        if not (hasattr(self.output_manager, 'stream_mode') and self.output_manager.stream_mode):
            self.output_manager.print_response(response, used_tools)

        # Assistant 응답을 히스토리에 추가
        self.conversation_manager.add_to_history(
            "assistant", response, {"used_tools": used_tools})

        # 쿼리 카운트 증가 콜백 호출
        if self.on_query_processed:
            self.on_query_processed()  # type: ignore[attr-defined,call-arg]

        # 응답에서 보류 중인 작업들 추출
        self.conversation_manager.extract_pending_actions(response_data)

        # 도구가 실제로 사용되었다면 보류 작업 클리어 (실행 완료로 간주)
        if used_tools:
            self.conversation_manager.clear_pending_actions()

    def _generate_plan_hash(self, plan: dict) -> str:
        """
        계획을 해시로 변환하는 함수

        Args:
            plan: 계획 데이터

        Returns:
            str: 해시된 계획
        """
        return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
