#!/usr/bin/env python3
"""
DSPilot CLI 모드 처리 핸들러
==========================

본 모듈은 DSPilot CLI 가 **단일 질문 모드** 와 **대화형 모드**를
스위칭하기 위해 사용하는 라우터 역할을 담당합니다.

역할 및 책임
------------
1. 모드에 따른 진입점 제공
   • run_single_query(): 한 번만 Agent 호출 후 종료
   • run_interactive(): REPL 기반 다중 TURN 대화 루프
2. `CommandHandler` 와 `QueryProcessor` 협력
   • 특수 명령어(`/exit`, `/status` 등)는 CommandHandler 로 위임
   • 일반 질문은 QueryProcessor 로 전달
3. UX 관리
   • 출력 레벨(quiet/verbose)에 따라 사용자 도움말, 배너 출력

아키텍처 다이어그램
------------------
```mermaid
flowchart TD
    A[ModeHandler] -->|single query| B[QueryProcessor]
    A -->|interactive loop| C[CommandHandler]
    C -->|delegates| B
```

시퀀스 다이어그램(대화형 모드)
-----------------------------
```mermaid
sequenceDiagram
    participant User
    participant ModeHandler
    participant CommandHandler
    participant QueryProcessor
    loop REPL
        User->>ModeHandler: 입력
        ModeHandler->>CommandHandler: handle_command()
        alt 특수 명령
            CommandHandler-->ModeHandler: handled=True
            ModeHandler-->>User: 결과 메시지
        else 일반 질문
            CommandHandler-->ModeHandler: handled=None
            ModeHandler->>QueryProcessor: process_query()
            QueryProcessor-->>User: AI 응답
        end
    end
```

사용 예시
---------
```python
cli = DSPilotCLI()
await cli.mode_handler.run_interactive()  # REPL 실행
await cli.mode_handler.run_single_query("오늘 날씨 어때?")
```

테스트 전략
-----------
- 모드 전환 및 루프 탈출 시나리오를 `pytest` 에서 `monkeypatch` 로
  `input()` 을 모킹하여 검증합니다.
"""

from dspilot_cli.cli_command_handler import CommandHandler
from dspilot_cli.cli_query_processor import QueryProcessor
from dspilot_cli.constants import StyleColors
from dspilot_cli.exceptions import CLIError, ModeHandlerError
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager


class ModeHandler:
    """실행 모드별 처리를 담당하는 클래스"""

    def __init__(self, output_manager: OutputManager,
                 interaction_manager: InteractionManager,
                 command_handler: CommandHandler,
                 query_processor: QueryProcessor) -> None:
        """
        모드 핸들러 초기화

        Args:
            output_manager: 출력 관리자
            interaction_manager: 상호작용 관리자
            command_handler: 명령어 핸들러
            query_processor: 쿼리 프로세서
        """
        self.output_manager = output_manager
        self.interaction_manager = interaction_manager
        self.command_handler = command_handler
        self.query_processor = query_processor

    async def run_single_query(self, query: str) -> None:
        """
        단일 질문 모드 실행

        Args:
            query: 사용자 질문
        """
        self.output_manager.print_info(f"단일 질문 모드: {query}")

        try:
            await self.query_processor.process_query(query)
        except CLIError:
            # 상위에서 이미 처리할 예외, 그대로 전파
            raise
        except Exception as exc:  # pylint: disable=broad-except
            self.output_manager.log_if_debug(f"단일 질문 처리 오류: {exc}", "error")
            self.output_manager.print_error(f"단일 질문 처리 중 오류가 발생했습니다: {exc}")
            raise ModeHandlerError("single_query", exc) from exc

    async def run_interactive(self) -> None:
        """대화형 모드 실행"""
        self.output_manager.print_success("대화형 모드 시작")
        self.output_manager.print_info("도움말: 'help' 입력, 종료: 'exit' 또는 Ctrl+C")
        self.output_manager.print_help()

        while True:
            try:
                # 사용자 입력 받기
                user_input = self.interaction_manager.get_user_input(
                    f"\n{StyleColors.USER}👤 You: {StyleColors.RESET_ALL}"
                )

                # 명령어 처리
                command_result = await self.command_handler.handle_command(user_input)

                if command_result is False:
                    # 종료 명령
                    break
                elif command_result is None:
                    # 일반 쿼리 처리 필요
                    await self.query_processor.process_query(user_input)
                # command_result가 True인 경우는 명령어가 처리됨

            except KeyboardInterrupt:
                self.output_manager.print_info("사용자 종료 요청")
                break
            except EOFError:
                self.output_manager.print_info("입력 종료")
                break
            except CLIError:
                # 이미 처리된 CLIError – 상위로 올려 사용자에게 일관 메시지 제공
                raise
            except Exception as exc:  # pylint: disable=broad-except
                # 예기치 못한 예외
                self.output_manager.log_if_debug(f"대화형 모드 오류: {exc}", "error")
                self.output_manager.print_error(f"대화형 모드에서 오류가 발생했습니다: {exc}")
                raise ModeHandlerError("interactive", exc) from exc
