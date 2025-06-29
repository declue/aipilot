#!/usr/bin/env python3
"""
DSPilot CLI 명령어 처리 핸들러
=============================

`CommandHandler` 는 대화형 모드에서 사용자가 입력하는 **특수 명령어**를
파싱하고, 각 명령에 해당하는 서브루틴을 호출합니다. 일반 자연어 질의는
`None` 을 반환하여 `QueryProcessor` 로 전달되고, 종료 명령은 `False` 를
반환하여 상위 루프를 종료시키는 **삼진(Boolean | None) 프로토콜**을 사용합
니다.

지원 명령어
-----------
| 명령어 | 축약 | 설명 |
|--------|------|------|
| help   |  -   | CLI 도움말 출력 |
| status |  -   | 시스템 상태 및 세션 통계 표시 |
| tools  |  -   | 사용 가능한 MCP 도구 목록 |
| clear  |  -   | 대화 히스토리 및 보류 작업 초기화 |
| exit   | quit | 프로그램 종료 |

상태 다이어그램
----------------
```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle -->|help| ShowHelp
    Idle -->|status| ShowStatus
    Idle -->|tools| ShowTools
    Idle -->|clear| ClearConv
    Idle -->|exit| Exit
    ShowHelp --> Idle
    ShowStatus --> Idle
    ShowTools --> Idle
    ClearConv --> Idle
```

설계 원칙
---------
1. **SRP** : 파일은 *명령어 파싱/라우팅* 만 담당하며, 출력은 `OutputManager` 에
   위임합니다.
2. **OCP** : 새 명령 추가 시 `handle_command()` 의 `elif` 블록만 확장하면 되며
   외부 모듈 수정이 필요 없습니다.
3. **Stateless** : 세션 시작시간과 쿼리 카운터를 *소프트 스테이트* 로만 보관해
   테스트가 용이합니다.

확장 가이드
------------
새 명령을 추가하려면 다음 순서를 따르세요.
1. `dspilot_cli.constants.Commands` 에 상수 추가.
2. `handle_command()` 에 분기 추가 (가능하면 독립 메서드로 추출).
3. `OutputManager` 에 필요한 출력 메서드가 없으면 확장.

테스트 전략
-----------
- `pytest.mark.parametrize` 로 다양한 입력값과 반환값을 검증합니다.
- `pytest-asyncio` 로 비동기 `_show_status_with_session()` 경로를 테스트합니다.
"""

from datetime import datetime
from typing import Optional

from dspilot_cli.constants import Commands, Messages
from dspilot_cli.conversation_manager import ConversationManager
from dspilot_cli.exceptions import CLIError, CommandHandlerError
from dspilot_cli.output_manager import OutputManager
from dspilot_cli.session import Session
from dspilot_cli.system_manager import SystemManager


class CommandHandler:
    """사용자 명령어 처리를 담당하는 클래스"""

    _session: Optional[Session] = None

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

        # 세션 정보는 외부에서 주입되며, 객체 자체를 보관한다.
        self._session: Optional[Session] = None

    async def handle_command(self, user_input: str) -> Optional[bool]:
        """
        사용자 명령어 처리

        Args:
            user_input: 사용자 입력

        Returns:
            계속 실행 여부 (False면 종료)
        """
        try:
            command = user_input.lower().strip()

            if command in [Commands.EXIT, Commands.QUIT, "q"]:
                self.output_manager.print_info("안녕히 가세요!")
                return False

            # 이후 분기는 종료(return)하지 않으므로 별도 if-elif 체인을 사용
            if command == Commands.HELP:
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

        except CLIError:
            # 이미 처리된 CLIError 는 그대로 전파
            raise
        except Exception as exc:  # pylint: disable=broad-except
            # 예기치 못한 예외 – 로깅 후 커스텀 예외로 래핑
            self.output_manager.log_if_debug(f"명령어 처리 중 오류: {exc}", "error")
            self.output_manager.print_error(f"명령어 처리 중 오류가 발생했습니다: {exc}")
            raise CommandHandlerError(user_input, exc) from exc

    async def _show_status(self) -> None:
        """현재 상태 출력"""
        components = self.system_manager.get_system_status()
        pending_actions = self.conversation_manager.get_pending_actions()

        # 세션 객체가 없으면 임시로 현재 시각/0을 사용
        if self._session is None:
            session_start = datetime.now()
            query_count = 0
        else:
            session_start = self._session.start_time
            query_count = self._session.query_count

        self.output_manager.print_status(
            components,
            session_start,
            query_count,
            self.conversation_manager.conversation_history,
            pending_actions,
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

    def set_session(self, session: Session) -> None:
        """세션 객체를 주입받아 상태 출력 시 활용합니다."""
        self._session = session

    async def _show_status_with_session(self) -> None:
        """세션 정보를 포함한 상태 출력"""
        components = self.system_manager.get_system_status()
        pending_actions = self.conversation_manager.get_pending_actions()

        # 세션 객체가 없으면 임시로 현재 시각/0을 사용
        if self._session is None:
            session_start = datetime.now()
            query_count = 0
        else:
            session_start = self._session.start_time
            query_count = self._session.query_count

        self.output_manager.print_status(
            components,
            session_start,
            query_count,
            self.conversation_manager.conversation_history,
            pending_actions,
        )
