#!/usr/bin/env python3
"""
DSPilot CLI 모드 처리 핸들러
"""

from dspilot_cli.cli_command_handler import CommandHandler
from dspilot_cli.cli_query_processor import QueryProcessor
from dspilot_cli.constants import StyleColors
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
        await self.query_processor.process_query(query)

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
            except Exception as e:
                self.output_manager.log_if_debug(f"대화형 모드 오류: {e}", "error")
                self.output_manager.print_error(f"오류: {e}") 