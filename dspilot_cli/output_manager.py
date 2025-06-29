#!/usr/bin/env python3
"""
DSPilot CLI 출력 관리 모듈
=========================

`OutputManager` 는 CLI 애플리케이션의 **모든 터미널 I/O** 를 단일 지점에서
관리합니다. 표준 출력은 물론, 로깅·컬러 스타일·스트리밍 버퍼 관리까지 담당해
다양한 모드(조용한 모드, 디버그, 스트리밍 등)에 대응합니다.

역할 & 특징
-----------
1. **스타일 레이어** : `StyleColors` 로 정의된 ANSI 컬러 코드를 이용해 가독성
   높은 메시지를 출력합니다.
2. **로깅 래퍼**      : Python `logging` API 를 감싸 `debug_mode`·`verbose_mode`
   여부에 따라 동적 로그 레벨 제어.
3. **스트리밍 지원**  : OpenAI / LLM 응답을 청크 단위로 받아 실시간 표시.
4. **사용자 상호작용 UI** : `InteractionManager` 에서 요청하는 선택 프롬프트를
   표준화된 형식으로 출력.
5. **테스트 친화성**  : 모든 출력 함수는 순수 I/O 이외의 부작용이 없어 모킹이
   용이하도록 설계했습니다.

간략 시퀀스
------------
```text
print_response()
    ├─ quiet_mode ?
    │    ├─ True  → 응답만 출력
    │    └─ False → 컬러 태그 적용 후 출력
    └─ (stream_mode 시) chunk → handle_streaming_chunk()
```
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from dspilot_cli.constants import Messages, StyleColors


class OutputManager:
    """출력 관리를 담당하는 클래스"""

    def __init__(self, 
                 quiet_mode: bool = False, 
                 debug_mode: bool = False, 
                 stream_mode: bool = False,
                 verbose_mode: bool = False) -> None:
        """
        출력 관리자 초기화

        Args:
            quiet_mode: 조용한 모드 여부
            debug_mode: 디버그 모드 여부
            stream_mode: 스트리밍 모드 여부
            verbose_mode: 상세 출력 모드 여부
        """
        self.quiet_mode = quiet_mode
        self.debug_mode = debug_mode
        self.stream_mode = stream_mode
        self.verbose_mode = verbose_mode
        self.logger = logging.getLogger("dspilot_cli")

        # 스트리밍 관련 상태
        self._streaming_active = False
        self._streaming_buffer = ""

    def print_if_not_quiet(self, message: str) -> None:
        """조용한 모드가 아닐 때만 출력"""
        if not self.quiet_mode:
            print(message)

    def log_if_debug(self, message: str, level: str = "info") -> None:
        """디버그 모드일 때만 로그 출력"""
        if self.debug_mode:
            if level == "error":
                self.logger.error(message)
            elif level == "warning":
                self.logger.warning(message)
            else:
                self.logger.info(message)

    def print_banner(self) -> None:
        """CLI 시작 배너 출력"""
        if self.quiet_mode:
            return

        banner = (
            f"{StyleColors.HEADER}==============================\n"
            f"   🐬  DSPilot CLI   \n"
            f"=============================={StyleColors.RESET_ALL}"
        )
        print(banner)

    def print_help(self) -> None:
        """도움말 출력"""
        help_text = f"""
{StyleColors.INFO}📖 사용 가능한 명령어:{StyleColors.RESET_ALL}

  {StyleColors.SYSTEM}help{StyleColors.RESET_ALL}     - 이 도움말 표시
  {StyleColors.SYSTEM}status{StyleColors.RESET_ALL}   - 시스템 상태 및 대화 히스토리 확인
  {StyleColors.SYSTEM}clear{StyleColors.RESET_ALL}    - 대화 기록 및 보류 작업 초기화
  {StyleColors.SYSTEM}exit{StyleColors.RESET_ALL}     - 프로그램 종료
  {StyleColors.SYSTEM}quit{StyleColors.RESET_ALL}     - 프로그램 종료

  {StyleColors.INFO}💡 일반 질문이나 요청을 입력하면 AI가 응답합니다.{StyleColors.RESET_ALL}
  {StyleColors.SUCCESS}🔄 멀티턴 대화: 이전 대화 맥락을 기억하여 연속된 작업을 처리합니다.{StyleColors.RESET_ALL}
  {StyleColors.WARNING}🤝 대화형 모드: MCP 도구 사용 시 사용자 확인 후 실행합니다.{StyleColors.RESET_ALL}
  {StyleColors.SYSTEM}⚡ --full-auto 옵션: 도구를 자동으로 실행합니다.{StyleColors.RESET_ALL}
        """
        print(help_text)

    def print_status(self, components: List[tuple], session_start: datetime,
                     query_count: int, conversation_history: List[Any],
                     pending_actions: List[str]) -> None:
        """현재 상태 출력"""
        print(f"\n{StyleColors.INFO}📊 시스템 상태:{StyleColors.RESET_ALL}")

        for name, component in components:
            status = "✓ 활성" if component is not None else "✗ 비활성"
            color = StyleColors.SUCCESS if component is not None else StyleColors.ERROR
            print(f"  {color}{name}: {status}{StyleColors.RESET_ALL}")

        # 세션 정보
        runtime = datetime.now() - session_start
        print(f"\n{StyleColors.INFO}📈 세션 정보:{StyleColors.RESET_ALL}")
        print(f"  실행 시간: {runtime}")
        print(f"  처리된 쿼리: {query_count}개")
        print(f"  대화 히스토리: {len(conversation_history)}개 메시지")

        # 보류 중인 작업 정보
        if pending_actions:
            print(f"\n{StyleColors.WARNING}⏳ 보류 중인 작업:{StyleColors.RESET_ALL}")
            for i, action in enumerate(pending_actions, 1):
                print(f"  {i}. {action}")
        else:
            print(
                f"\n{StyleColors.SUCCESS}{Messages.NO_PENDING_ACTIONS}{StyleColors.RESET_ALL}")

    def print_tools_list(self, tools: List[Any]) -> None:
        """사용 가능한 MCP 도구 목록 출력"""
        print(f"\n{StyleColors.INFO}🔧 사용 가능한 MCP 도구:{StyleColors.RESET_ALL}")

        if tools:
            for i, tool in enumerate(tools, 1):
                tool_name = getattr(tool, 'name', 'Unknown')
                tool_desc = getattr(tool, 'description', 'No description')
                print(
                    f"  {i:2d}. {StyleColors.SUCCESS}{tool_name}{StyleColors.RESET_ALL}")
                print(f"      {tool_desc}")
            print(
                f"\n{StyleColors.INFO}총 {len(tools)}개의 도구가 사용 가능합니다.{StyleColors.RESET_ALL}")
        else:
            print(f"  {StyleColors.WARNING}사용 가능한 도구가 없습니다.{StyleColors.RESET_ALL}")

    def print_execution_plan(self, plan: Dict[str, Any]) -> None:
        """실행 계획 출력"""
        steps = plan.get("steps", [])
        if not self.quiet_mode or self.verbose_mode:
            plan_text = plan.get("description", "도구 실행 계획")
            print(
                f"{StyleColors.INFO}📋 실행 계획: {plan_text}{StyleColors.RESET_ALL}")
            print(
                f"{StyleColors.INFO}총 {len(steps)}개 단계가 있습니다.{StyleColors.RESET_ALL}\n")

    def print_step_info(self, step_num: int, description: str) -> None:
        """단계 정보 출력"""
        if not self.quiet_mode or self.verbose_mode:
            print(
                f"{StyleColors.SYSTEM}🔄 단계 {step_num}: {description}{StyleColors.RESET_ALL}")

    def print_step_execution(self, tool_name: str) -> None:
        """단계 실행 정보 출력"""
        if not self.quiet_mode or self.verbose_mode:
            print(f"{StyleColors.SYSTEM}⚡ {tool_name} 실행 중...{StyleColors.RESET_ALL}")

    def print_step_completed(self, step_num: int) -> None:
        """단계 완료 정보 출력"""
        if not self.quiet_mode or self.verbose_mode:
            print(f"{StyleColors.SUCCESS}✅ 단계 {step_num} 완료{StyleColors.RESET_ALL}")

    def print_step_skipped(self, step_num: int) -> None:
        """단계 건너뛰기 정보 출력"""
        print(f"{StyleColors.WARNING}⏭️ 단계 {step_num} 건너뛰기{StyleColors.RESET_ALL}")

    def print_step_error(self, step_num: int, error: str) -> None:
        """단계 오류 정보 출력"""
        # quiet_mode 라도 오류는 반드시 사용자에게 보여준다.
        if self.quiet_mode and not (self.debug_mode or self.verbose_mode):
            # 최소 포맷으로 출력
            print(f"[ERROR] 단계 {step_num} 실패: {error}")
        else:
            # 컬러 적용 출력
            print(f"{StyleColors.ERROR}❌ 단계 {step_num} 실행 실패: {error}{StyleColors.RESET_ALL}")

    def print_task_cancelled(self) -> None:
        """작업 중단 정보 출력"""
        print(f"{StyleColors.INFO}✅ 작업을 중단합니다.{StyleColors.RESET_ALL}")

    def print_user_confirmation(self,
                                message: str,
                                tool_name: str,
                                arguments: Optional[Dict[str, Any]]) -> None:
        """사용자 확인 메시지 출력"""
        print(f"\n{StyleColors.WARNING}🔍 {message}{StyleColors.RESET_ALL}")
        print(f"{StyleColors.INFO}도구: {tool_name}{StyleColors.RESET_ALL}")
        if arguments:
            print(f"{StyleColors.INFO}매개변수: {arguments}{StyleColors.RESET_ALL}")

        print(f"{StyleColors.USER}선택:{StyleColors.RESET_ALL}")
        print(f"  {StyleColors.SUCCESS}y{StyleColors.RESET_ALL} - 실행")
        print(f"  {StyleColors.WARNING}s{StyleColors.RESET_ALL} - 건너뛰기")
        print(f"  {StyleColors.INFO}m{StyleColors.RESET_ALL} - 새로운 요청으로 수정")
        print(f"  {StyleColors.ERROR}n{StyleColors.RESET_ALL} - 중단")

    def print_invalid_choice(self) -> None:
        """잘못된 선택 메시지 출력"""
        print(
            f"{StyleColors.ERROR}잘못된 선택입니다. y/s/m/n 중 하나를 입력하세요.{StyleColors.RESET_ALL}")

    def print_continue_prompt(self) -> None:
        """계속 진행 확인 메시지 출력"""
        print(
            f"{StyleColors.WARNING}계속 진행하시겠습니까? (y/n): {StyleColors.RESET_ALL}", end="")

    def print_response(self, response: str, used_tools: Optional[List[Any]] = None) -> None:
        """AI 응답 출력"""
        if self.quiet_mode:
            # 조용한 모드에서는 응답만 출력
            print(response)
        else:
            # 일반 모드에서는 스타일링 적용
            print(
                f"{StyleColors.ASSISTANT}🤖 Assistant: {response}{StyleColors.RESET_ALL}")

        # 사용된 도구 정보
        if used_tools and not self.quiet_mode:
            tools = ", ".join(str(tool) for tool in used_tools)
            print(f"{StyleColors.INFO}🔧 사용된 도구: {tools}{StyleColors.RESET_ALL}")

    def print_error(self, message: str) -> None:
        """에러 메시지 출력"""
        if self.quiet_mode:
            print(message)
        else:
            print(f"{StyleColors.ERROR}❌ {message}{StyleColors.RESET_ALL}")

        # 디버그/상세 모드일 때는 스택트레이스 출력으로 원인 파악 지원
        if self.debug_mode or self.verbose_mode:
            tb = traceback.format_exc()
            if tb and tb.strip() != "NoneType: None":
                print(f"{StyleColors.WARNING}{tb}{StyleColors.RESET_ALL}")

    def print_warning(self, message: str) -> None:
        """경고 메시지 출력"""
        if not self.quiet_mode:
            print(f"{StyleColors.WARNING}⚠ {message}{StyleColors.RESET_ALL}")

    def print_info(self, message: str) -> None:
        """정보 메시지 출력"""
        if not self.quiet_mode:
            print(f"{StyleColors.INFO}{message}{StyleColors.RESET_ALL}")

    def print_success(self, message: str) -> None:
        """성공 메시지 출력"""
        if not self.quiet_mode:
            print(f"{StyleColors.SUCCESS}{message}{StyleColors.RESET_ALL}")

    def print_system(self, message: str) -> None:
        """시스템 메시지 출력"""
        if not self.quiet_mode:
            print(f"{StyleColors.SYSTEM}{message}{StyleColors.RESET_ALL}")

    def start_streaming_output(self) -> None:
        """스트리밍 출력 시작"""
        if self.stream_mode:
            self._streaming_active = True
            self._streaming_buffer = ""
            # "Assistant:" 레이블 제거 - 바로 응답만 출력

    def handle_streaming_chunk(self, chunk: str) -> None:
        """스트리밍 청크 처리"""
        if self.stream_mode and self._streaming_active:
            print(chunk, end="", flush=True)
            self._streaming_buffer += chunk

    def finish_streaming_output(self) -> None:
        """스트리밍 출력 완료"""
        if self.stream_mode and self._streaming_active:
            print()  # 단순히 줄바꿈만 추가
            self._streaming_active = False
