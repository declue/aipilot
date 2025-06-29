#!/usr/bin/env python3
"""
DSPilot CLI 애플리케이션 클래스

이 모듈은 커맨드라인 상에서 DSPilot Agent 를 실행하기 위한
엔트리포인트 역할을 합니다. 각종 *Manager* 들을 조합하여
1) 시스템 초기화 → 2) 쿼리 전처리 → 3) Agent 실행 → 4) 후처리
의 전형적인 CLI 파이프라인을 구성합니다.

주요 구성 요소 개요
-------------------
1. OutputManager       : 모든 터미널/로그 출력 통합 관리
2. SystemManager       : LLM, MCP ToolManager 등 시스템 전역 객체 초기화
3. ConversationManager : 사용자의 대화 맥락 상태 저장/조회
4. InteractionManager  : 사용자 입력/행동(Yes/No 확인 등) 제어
5. ExecutionManager    : 실제 워크플로우(step) 실행 컨트롤러
6. QueryProcessor      : 사용자 자연어 → 실행 계획(steps) 변환
7. CommandHandler      : `/exit`, `/mode` 와 같은 특수 명령 처리
8. ModeHandler         : 단일 질의 모드 vs 대화형 모드 스위칭

```
┌─────────────┐      ┌────────────────┐      ┌──────────────────┐
│ User Input  │ ─→  │ QueryProcessor │ ─→  │ ExecutionManager │
└─────────────┘      └────────────────┘      └──────────────────┘
        ↑                                                   ↓
        │                        (tool results)            │
        └──────── InteractionManager / OutputManager ──────┘
```
이 구조 덕분에 각 레이어가 **단일 책임 원칙(SRP)** 을 유지하며
테스트 또한 개별 모듈 단위로 작성할 수 있습니다.
"""

import traceback
from typing import Optional

# 외부 모듈
from dspilot_cli.cli_command_handler import CommandHandler
from dspilot_cli.cli_mode_handler import ModeHandler
from dspilot_cli.cli_query_processor import QueryProcessor
from dspilot_cli.constants import Defaults
from dspilot_cli.conversation_manager import ConversationManager
from dspilot_cli.exceptions import CLIError, ManagerInitializationError, SystemInitializationError
from dspilot_cli.execution_manager import ExecutionManager
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager
from dspilot_cli.session import Session
from dspilot_cli.system_manager import SystemManager


class DSPilotCLI:
    """
    DSPilot CLI 메인 애플리케이션 클래스

    역할:
    1. 모든 Manager / Handler 를 생성 및 조립
    2. `initialize()` 단계에서 시스템 의존성(LLM, MCP 등)을 준비
    3. `run()` 단계에서 **단일 질의 모드** 와 **대화형 모드** 중 선택 실행
    4. 실행 후 `_cleanup()` 으로 자원 정리

    주의: __init__ 에서는 *가벼운* 작업만 수행해야 합니다.
    네트워크 호출·모델 로딩 등 무거운 작업은 `initialize()` 로 분리하여
    빠른 CLI 기동 시간을 보장합니다.
    """

    execution_manager: Optional[ExecutionManager] = None
    command_handler: Optional[CommandHandler] = None
    query_processor: Optional[QueryProcessor] = None
    mode_handler: Optional[ModeHandler] = None
    output_manager: Optional[OutputManager] = None
    conversation_manager: Optional[ConversationManager] = None
    interaction_manager: Optional[InteractionManager] = None

    def __init__(self,
                 debug_mode: bool = False,
                 quiet_mode: bool = False,
                 full_auto_mode: bool = False,
                 stream_mode: bool = False,
                 verbose_mode: bool = False,
                 max_iterations: int = Defaults.MAX_ITERATIONS,
                 validate_mode: str = Defaults.VALIDATE_MODE,
                 max_step_retries: int = Defaults.MAX_STEP_RETRIES) -> None:
        """
        DSPilot CLI 애플리케이션 초기화

        Args:
            debug_mode: 디버그 모드 여부
            quiet_mode: 조용한 모드 여부
            full_auto_mode: 전체 자동 모드 여부
            stream_mode: 스트리밍 모드 여부
            verbose_mode: 상세 출력 모드 여부
            max_iterations: Agent 반복 실행 최대 횟수 (기본 30)
            validate_mode: 도구 결과 검증 모드(auto/off/strict)
            max_step_retries: 단계 실패 시 자동 재시도 횟수 (기본 2)
        """
        # 기본 설정 저장
        self.debug_mode = debug_mode
        self.quiet_mode = quiet_mode
        self.full_auto_mode = full_auto_mode
        self.stream_mode = stream_mode
        self.verbose_mode = verbose_mode
        self.max_iterations = max_iterations
        self.validate_mode = validate_mode
        self.max_step_retries = max_step_retries

        # 세션 정보 객체화
        self.session: Session = Session()

        # 관리자들 초기화
        self._initialize_managers()

    def _initialize_managers(self) -> None:
        """관리자들을 초기화합니다."""
        try:
            # 기본 관리자들
            self.output_manager = OutputManager(
                self.quiet_mode, self.debug_mode, self.stream_mode, self.verbose_mode)

            self.conversation_manager = ConversationManager()
            self.interaction_manager = InteractionManager(
                self.output_manager, self.full_auto_mode)
            self.system_manager = SystemManager(self.output_manager)

            # 실행 관리자는 시스템 초기화 후 생성
            self.execution_manager = None

            # 핸들러들 초기화
            self.command_handler = CommandHandler(
                self.output_manager, self.conversation_manager, self.system_manager)
            self.query_processor = QueryProcessor(
                self.output_manager, self.conversation_manager, self.interaction_manager,
                self.max_iterations)
            self.mode_handler = ModeHandler(
                self.output_manager, self.interaction_manager, self.command_handler,
                self.query_processor)

            # 콜백 설정
            self.query_processor.on_query_processed = self.increment_query_count

            # 세션 객체를 명령어 핸들러에 전달
            self.command_handler.set_session(self.session)

            if not self.quiet_mode:
                self.output_manager.log_if_debug("DSPilotCLI 초기화 완료")

        except Exception as exc:  # pylint: disable=broad-except
            # OutputManager 가 준비되지 않았을 수도 있으므로 print 사용
            print(f"관리자 초기화 실패: {exc}")
            raise ManagerInitializationError("Manager 초기화", exc) from exc

    async def initialize(self) -> bool:
        """시스템 초기화 단계

        순서
        1. 배너 출력 (OutputManager)
        2. SystemManager 로 하드 의존성(LLM, Tools) 준비
        3. 준비된 객체로 ExecutionManager 구성
        4. QueryProcessor 에 ExecutionManager 주입
        5. 상호작용 모드 설정 (full_auto 여부에 따라)
        """
        if not self.output_manager:
            raise CLIError("OutputManager 초기화 실패")
        if not self.interaction_manager:
            raise CLIError("InteractionManager 초기화 실패")
        if not self.system_manager:
            raise CLIError("SystemManager 초기화 실패")
        if not self.query_processor:
            raise CLIError("QueryProcessor 초기화 실패")
        if not self.mode_handler:
            raise CLIError("ModeHandler 초기화 실패")

        self.output_manager.print_banner()

        success, message = await self.system_manager.initialize()
        if not success:
            # 시스템 초기화 실패 – 예외 발생시켜 run() 에서 처리
            raise SystemInitializationError(message)

        # 실행 관리자 초기화 (시스템 구성요소들이 준비된 후)
        llm_agent = self.system_manager.get_llm_agent()
        mcp_tool_manager = self.system_manager.get_mcp_tool_manager()

        if llm_agent and mcp_tool_manager:
            self.execution_manager = ExecutionManager(
                self.output_manager,
                self.interaction_manager,
                llm_agent,
                mcp_tool_manager,
                validate_mode=self.validate_mode,
                max_step_retries=self.max_step_retries,
            )

            # 쿼리 프로세서에 실행 관리자 설정
            self.query_processor.set_execution_manager(self.execution_manager)

        # 상호작용 모드 설정 (full_auto_mode 가 False 이면 interactive)
        self.system_manager.set_interaction_mode(not self.full_auto_mode)

        return True

    async def run(self, query: Optional[str] = None) -> None:
        """메인 실행 메소드
        Args:
            query: 단일 질의. None 이면 대화형 모드로 진입
        """
        if not self.output_manager:
            raise CLIError("OutputManager 초기화 실패")

        try:
            # 초기화
            if not await self.initialize():
                return

            if not self.mode_handler:
                raise CLIError("ModeHandler 초기화 실패")

            # 모드에 따라 실행
            if query:
                await self.mode_handler.run_single_query(query)
            else:
                await self.mode_handler.run_interactive()

        except KeyboardInterrupt:
            # 사용자가 Ctrl+C 로 중단한 경우
            if self.output_manager:
                self.output_manager.print_warning("사용자 중단(Ctrl+C) 감지 – 종료합니다.")
        except CLIError as cli_err:
            # 커스텀 예외 – 사용자에게 친숙한 메시지 출력
            self.output_manager.print_error(str(cli_err))
            self.output_manager.log_if_debug(f"CLIError: {cli_err}", "error")
        except Exception as e:  # pylint: disable=broad-except
            # 알 수 없는 예외 – 상세 스택트레이스는 디버그 모드에서만
            tb = traceback.format_exc()
            self.output_manager.log_if_debug(tb, "error")
            self.output_manager.print_error(f"예상치 못한 오류가 발생했습니다: {e}")
        finally:
            await self._cleanup()

    def increment_query_count(self) -> None:
        """QueryProcessor 가 호출하는 콜백
        쿼리 처리 시마다 세션 카운터를 증가시켜 통계 및 로그에 활용합니다.
        """
        if not self.command_handler:
            raise CLIError("CommandHandler 초기화 실패")
        # 세션 객체에 카운트 증가
        self.session.increment_query_count()

        # CommandHandler 는 동일한 Session 인스턴스를 참조하므로
        # 별도 갱신 호출이 필요 없지만, 테스트 호환성을 위해 호출 유지
        if hasattr(self.command_handler, "set_session"):
            self.command_handler.set_session(self.session)

    def get_session_info(self) -> tuple:
        """세션 정보를 반환합니다."""
        return self.session.start_time, self.session.query_count

    async def _cleanup(self) -> None:
        """세션 종료 시 리소스 정리
        현재는 SystemManager 에게 위임하여 LLM 세션 종료, 임시 파일 삭제 등을
        수행합니다. 추후 리소스가 늘어나면 이 메소드에서 추가 정리를 할 수도 있습니다.
        """
        try:
            await self.system_manager.cleanup()
        except Exception as exc:  # pylint: disable=broad-except
            # 비치명적 예외로 간주 – 프로그램 종료 단계이므로 재발생하지 않음
            # 필요 시 호출부에서 Logging 으로 확인 가능
            if self.output_manager:
                self.output_manager.log_if_debug(f"정리 단계 오류: {exc}", "error")
