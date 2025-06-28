#!/usr/bin/env python3
"""
DSPilot CLI 애플리케이션 클래스
"""

from datetime import datetime
from typing import Optional

from dspilot_cli.cli_command_handler import CommandHandler
from dspilot_cli.cli_mode_handler import ModeHandler
from dspilot_cli.cli_query_processor import QueryProcessor
from dspilot_cli.constants import Defaults
from dspilot_cli.conversation_manager import ConversationManager
from dspilot_cli.execution_manager import ExecutionManager
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager
from dspilot_cli.system_manager import SystemManager


class DSPilotCLI:
    """
    DSPilot CLI 메인 애플리케이션 클래스
    
    각 관리자들을 조율하고 전체 애플리케이션 흐름을 제어합니다.
    """

    execution_manager: Optional[ExecutionManager] = None
    command_handler: Optional[CommandHandler] = None
    query_processor: Optional[QueryProcessor] = None
    mode_handler: Optional[ModeHandler] = None
    output_manager: Optional[OutputManager] = None
    conversation_manager: Optional[ConversationManager] = None
    interaction_manager: Optional[InteractionManager] = None


    def __init__(self, debug_mode: bool = False, quiet_mode: bool = False,
                 full_auto_mode: bool = False, stream_mode: bool = False, verbose_mode: bool = False,
                 max_iterations: int = Defaults.MAX_ITERATIONS, validate_mode: str = Defaults.VALIDATE_MODE,
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
        

        # 세션 정보
        self.session_start = datetime.now()
        self.query_count = 0

        # 관리자들 초기화
        self._initialize_managers()

    def _initialize_managers(self) -> None:
        """관리자들을 초기화합니다."""
        # 기본 관리자들
        self.output_manager = OutputManager(
            self.quiet_mode, self.debug_mode, self.stream_mode, self.verbose_mode)
        self.conversation_manager = ConversationManager()
        self.interaction_manager = InteractionManager(
            self.output_manager, self.full_auto_mode)
        self.system_manager = SystemManager(self.output_manager)

        # 실행 관리자는 시스템 초기화 후 생성
        self.execution_manager: Optional[ExecutionManager] = None

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
        
        # 세션 정보를 명령어 핸들러에 전달
        self.command_handler.set_session_info(self.session_start, self.query_count)

        if not self.quiet_mode:
            self.output_manager.log_if_debug("DSPilotCLI 초기화 완료")

    async def initialize(self) -> bool:
        """
        시스템 초기화

        Returns:
            초기화 성공 여부
        """
        self.output_manager.print_banner()

        if not await self.system_manager.initialize():
            return False

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
                max_step_retries=self.max_step_retries
            )
            
            # 쿼리 프로세서에 실행 관리자 설정
            self.query_processor.set_execution_manager(self.execution_manager)

        # 상호작용 모드 설정
        self.system_manager.set_interaction_mode(not self.full_auto_mode)

        return True

    async def run(self, query: Optional[str] = None) -> None:
        """
        메인 실행 함수

        Args:
            query: 단일 질문 (없으면 대화형 모드)
        """
        try:
            # 초기화
            if not await self.initialize():
                return

            # 모드에 따라 실행
            if query:
                await self.mode_handler.run_single_query(query)
            else:
                await self.mode_handler.run_interactive()

        except Exception as e:
            self.output_manager.log_if_debug(f"실행 중 오류: {e}", "error")
            self.output_manager.print_error(f"실행 중 오류: {e}")
        finally:
            await self._cleanup()

    def increment_query_count(self) -> None:
        """쿼리 카운트를 증가시킵니다."""
        self.query_count += 1
        # 명령어 핸들러에 업데이트된 세션 정보 전달
        self.command_handler.set_session_info(self.session_start, self.query_count)

    def get_session_info(self) -> tuple:
        """세션 정보를 반환합니다."""
        return self.session_start, self.query_count

    async def _cleanup(self) -> None:
        """리소스 정리"""
        await self.system_manager.cleanup() 