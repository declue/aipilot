#!/usr/bin/env python3
"""
DSPilot CLI 명령어 처리 핸들러
"""

from datetime import datetime
from typing import Optional

from dspilot_cli.constants import Commands, Messages
from dspilot_cli.conversation_manager import ConversationManager
from dspilot_cli.output_manager import OutputManager
from dspilot_cli.system_manager import SystemManager


class CommandHandler:
    """사용자 명령어 처리를 담당하는 클래스"""

    _session_start: Optional[datetime] = None
    _query_count: int = 0

    def __init__(self, output_manager: OutputManager,
                 conversation_manager: ConversationManager,
                 system_manager: SystemManager) -> None:
        """
        명령어 핸들러 초기화

        Args:
            output_manager: 출력 관리자
            conversation_manager: 대화 관리자
            system_manager: 시스템 관리자
        """
        self.output_manager = output_manager
        self.conversation_manager = conversation_manager
        self.system_manager = system_manager

    async def handle_command(self, user_input: str) -> bool:
        """
        사용자 명령어 처리

        Args:
            user_input: 사용자 입력

        Returns:
            계속 실행 여부 (False면 종료)
        """
        command = user_input.lower().strip()

        if command in [Commands.EXIT, Commands.QUIT, "q"]:
            self.output_manager.print_info("안녕히 가세요!")
            return False
        elif command == Commands.HELP:
            self.output_manager.print_help()
        elif command == Commands.STATUS:
            await self._show_status_with_session()
        elif command == Commands.TOOLS:
            await self._show_tools()
        elif command == Commands.CLEAR:
            await self._clear_conversation()
        elif not user_input:
            # 빈 입력은 무시
            pass
        else:
            # 일반 쿼리로 처리
            return None  # None을 반환하여 쿼리 처리가 필요함을 알림

        return True

    async def _show_status(self) -> None:
        """현재 상태 출력"""
        components = self.system_manager.get_system_status()
        pending_actions = self.conversation_manager.get_pending_actions()

        # 세션 정보는 외부에서 전달받아야 하므로 임시로 None 처리
        self.output_manager.print_status(
            components,
            None,  # session_start
            0,  # query_count
            self.conversation_manager.conversation_history,
            pending_actions
        )

    async def _show_tools(self) -> None:
        """사용 가능한 도구 목록 출력"""
        tools = await self.system_manager.get_tools_list()
        self.output_manager.print_tools_list(tools)

    async def _clear_conversation(self) -> None:
        """대화 기록 초기화"""
        llm_agent = self.system_manager.get_llm_agent()
        if llm_agent:
            llm_agent.clear_conversation()
            self.conversation_manager.clear_conversation()
            self.output_manager.print_success(Messages.CONVERSATION_CLEARED)
        else:
            self.output_manager.print_error(Messages.AGENT_NOT_INITIALIZED)

    def set_session_info(self, session_start, query_count: int) -> None:
        """세션 정보를 설정합니다 (상태 출력용)"""
        self._session_start = session_start
        self._query_count = query_count

    async def _show_status_with_session(self) -> None:
        """세션 정보를 포함한 상태 출력"""
        components = self.system_manager.get_system_status()
        pending_actions = self.conversation_manager.get_pending_actions()

        self.output_manager.print_status(
            components,
            getattr(self, '_session_start', None),
            getattr(self, '_query_count', 0),
            self.conversation_manager.conversation_history,
            pending_actions
        )
