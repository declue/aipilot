#!/usr/bin/env python3
"""
DSPilot CLI 쿼리 프로세서

이 모듈은 DSPilot CLI 파이프라인에서
1) 사용자 자연어 입력 수집 → 2) 대화 히스토리 업데이트 → 3) LLM 프롬프트 생성
4) 요청 분석·계획 수립 → 5) MCP Tool 실행 → 6) 출력 및 반복 제어
까지의 전 과정을 오케스트레이션합니다.

주요 구성 요소 개요
-------------------
1. OutputManager       : 터미널/로그/스트리밍 출력 통합
2. ConversationManager : 대화 맥락 관리 및 향상된 프롬프트 생성
3. InteractionManager  : 사용자 인터랙션(Yes/No, 중단) 제어
4. ExecutionManager    : LLM 분석·계획 및 MCP Tool 실행 제어
5. QueryProcessor      : 본 모듈 – 상위 4개 매니저를 엮어 *단일 책임*으로 "쿼리 → 결과" 변환

동작 시퀀스
-----------
```
┌─────────────┐   1  ┌────────────────┐   2  ┌──────────────────┐   3
│ User Input  │ ───▶│ ConversationMgr │ ───▶│ ExecutionManager │
└─────────────┘      └────────────────┘      └──────────────────┘
                                         ▲            │
                                         │ 4          │ tool results
                                         │            ▼
                                         └──────── QueryProcessor
```

• 반복 제어: max_iterations 한도 내에서 실패 시 재분석·재시도  
• 성공 조건: MCP Tool 실행 오류가 없거나 LLM 직접응답 완료  
• 안전 장치: 중복 계획 해시 감지, 단계 오류 최대 재시도, 스트리밍 모드 지원

이 모듈은 *상호작용 CLI* 워크플로의 핵심 루프를 담당하며,
SOLID 원칙 중 SRP(단일 책임)와 OC(확장/폐쇄)를 충족하도록 설계되었습니다.
"""

from typing import Callable, Optional

from dspilot_cli.conversation_manager import ConversationManager
from dspilot_cli.execution_manager import ExecutionManager
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager
from dspilot_cli.plan_evaluator import PlanEvaluator
from dspilot_cli.plan_history_manager import PlanHistoryManager


class QueryProcessor:
    """
    대화형 Query Processor

    책임(Responsibilities)
    ----------------------
    • 사용자 입력을 ConversationManager 에 기록하고, 과거 맥락을 합쳐 '향상된 프롬프트'를 생성  
    • ExecutionManager 에게 분석·계획 수립 및 MCP Tool 실행을 위임  
    • 실행 결과를 평가하여 오류 여부·중복 계획·반복 횟수 등을 판단해 재시도 또는 루프 종료 결정  
    • OutputManager 를 통해 스트리밍/비스트리밍 출력, InteractionManager 를 통한 사용자 상호작용을 지원  
    • on_query_processed 콜백을 통해 외부(예: Session)와 느슨하게 결합된 후처리 트리거를 제공

    속성(Attributes)
    ----------------
    output_manager       : 출력·로그·스트리밍 제어  
    conversation_manager : 대화 맥락 및 pending actions 관리  
    interaction_manager  : 사용자 인터렉션(Yes/No, 입력 요청) 처리  
    max_iterations       : 실패 시 재시도 최대 횟수  
    execution_manager    : 실행 계획 분석 및 MCP Tool 실행 컨트롤러 (set_execution_manager 로 주입)
    """

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

        # 계획 평가기 (중복/오류 관리)
        self.plan_history_manager = PlanHistoryManager()
        self.plan_evaluator = PlanEvaluator(self.plan_history_manager)

        # 외부에서 설정할 콜백 – 기본은 no-op Lambda 로 설정해
        # "not callable" 린터 경고 및 None 체크를 제거합니다.
        self.on_query_processed: Callable[[], None] = lambda: None

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

        while iterations < self.max_iterations:
            try:
                # 사용자 입력을 히스토리에 추가 (반복 포함)
                if iterations == 0:
                    self.conversation_manager.add_to_history(
                        "user", current_input)

                self.output_manager.log_if_debug(
                    f"=== CLI: 대화형 Agent 처리 시작 (iteration {
                        iterations + 1}/{self.max_iterations
                                         }): '{current_input}' ===")

                # 에이전트 실행 (계획 수립 및 실행 포함)
                result_info = await self._run_interactive_agent(current_input)
                has_errors = result_info.get("has_errors", False)
                plan_duplicate = result_info.get("plan_duplicate", False)
                plan_executed = result_info.get("has_plan", False)

                # ------------------------------------------------------------------
                # 엄격한 오류 판단 - 실제 실행 실패만 오류로 간주 -------------------
                # ------------------------------------------------------------------
                # LLM이 "콘텐츠 부족" 등으로 판단하더라도, 실제 도구 실행이 성공했다면
                # 오류가 아닌 것으로 간주하여 불필요한 재시도를 방지합니다.
                actual_execution_errors = []
                if isinstance(result_info, dict) and "steps" in result_info:
                    for step_result in result_info["steps"]:
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
                enhanced_prompt = self.conversation_manager.build_enhanced_prompt(
                    "")
                next_plan = await self.execution_manager.analyze_request_and_plan(enhanced_prompt)

                # ------------------------------------------------------------------
                # 반복 종료 조건 평가 ---------------------------
                # ------------------------------------------------------------------
                if plan_duplicate:
                    self.output_manager.print_warning("⚠️ 중복 계획 감지 → 종료")
                    break

                if next_plan is None or (plan_executed and not has_errors):
                    if next_plan is None and has_errors:
                        iterations += 1
                        current_input = "다른 방법으로 시도해줘"
                        continue
                    break

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
        self.on_query_processed()

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

        # --------------------------------------------------------------
        # 중복 계획 감지 – 실행 전에 체크하여 불필요한 실행 방지
        # --------------------------------------------------------------
        plan_duplicate = False
        if plan:
            plan_duplicate = self.plan_evaluator.is_duplicate(plan)
            if plan_duplicate:
                return {"has_plan": True, "plan_duplicate": True, "has_errors": False}

        if not plan:
            # 도구가 필요하지 않은 경우 직접 응답
            # system_manager를 통해 llm_agent 가져오기 (임시 해결책)
            # 더 나은 방법은 의존성 주입을 통해 llm_agent를 직접 받는 것
            if hasattr(self.execution_manager, '_llm_agent'):
                llm_agent = self.execution_manager._llm_agent  # pylint: disable=protected-access

                if hasattr(self.output_manager, 'stream_mode') and self.output_manager.stream_mode:
                    self.output_manager.start_streaming_output()

                response_data = await llm_agent.generate_response(
                    enhanced_prompt, streaming_callback)

                if hasattr(self.output_manager, 'stream_mode') and self.output_manager.stream_mode:
                    self.output_manager.finish_streaming_output()

                await self._display_response(response_data)
            return {
                "has_plan": False,
                "plan_duplicate": False,
                "has_errors": False
            }

        # 2단계: 대화형 실행 (스트리밍 콜백 전달)
        result_info = await self.execution_manager.execute_interactive_plan(plan, enhanced_prompt, streaming_callback)
        step_results = result_info.get("step_results", {}) if isinstance(result_info, dict) else {}

        eval_flags = self.plan_evaluator.evaluate(plan, step_results)
        has_errors = eval_flags.get("has_errors", False)
        self.output_manager.log_if_debug(
            f"PlanEvaluator flags: {eval_flags}")

        return {
            "has_plan": True,
            "plan_duplicate": plan_duplicate,
            "has_errors": has_errors,
            "steps": list(step_results.values()),
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
        self.on_query_processed()

        # 응답에서 보류 중인 작업들 추출
        self.conversation_manager.extract_pending_actions(response_data)

        # 도구가 실제로 사용되었다면 보류 작업 클리어 (실행 완료로 간주)
        if used_tools:
            self.conversation_manager.clear_pending_actions()
