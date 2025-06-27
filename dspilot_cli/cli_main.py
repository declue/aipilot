#!/usr/bin/env python3
"""
DSPilot CLI - 모듈화된 메인 CLI 클래스
SOLID 원칙과 단일 책임 원칙을 적용한 구조
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import colorama

from dspilot_cli.constants import Commands, Messages, StyleColors
from dspilot_cli.conversation_manager import ConversationManager
from dspilot_cli.execution_manager import ExecutionManager
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager
from dspilot_cli.system_manager import SystemManager


class DSPilotCLI:
    """
    DSPilot CLI 메인 클래스 (모듈화됨)

    단일 책임 원칙을 따르며, 각 기능이 별도 클래스로 분리됨:
    - OutputManager: 출력 관리
    - ConversationManager: 대화 히스토리 관리
    - InteractionManager: 사용자 상호작용
    - ExecutionManager: 계획 수립 및 실행
    - SystemManager: 시스템 초기화 및 관리
    """

    def __init__(self, debug_mode: bool = False, quiet_mode: bool = False,
                 full_auto_mode: bool = False) -> None:
        """
        DSPilot CLI 초기화

        Args:
            debug_mode: 디버그 모드 여부
            quiet_mode: 조용한 모드 여부
            full_auto_mode: 전체 자동 모드 여부
        """
        # 기본 설정
        self.debug_mode = debug_mode
        self.quiet_mode = quiet_mode
        self.full_auto_mode = full_auto_mode

        # 세션 정보
        self.session_start = datetime.now()
        self.query_count = 0

        # 의존성 주입으로 관리자들 초기화
        self.output_manager = OutputManager(quiet_mode, debug_mode)
        self.conversation_manager = ConversationManager()
        self.interaction_manager = InteractionManager(
            self.output_manager, full_auto_mode)
        self.system_manager = SystemManager(self.output_manager)

        # 실행 관리자는 시스템 초기화 후 생성
        self.execution_manager: Optional[ExecutionManager] = None

        if not self.quiet_mode:
            self.output_manager.log_if_debug("DSPilotCLI 초기화")

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
                mcp_tool_manager
            )

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
                await self._run_single_query(query)
            else:
                await self._run_interactive()

        except Exception as e:
            self.output_manager.log_if_debug(f"실행 중 오류: {e}", "error")
            self.output_manager.print_error(f"실행 중 오류: {e}")
        finally:
            await self._cleanup()

    async def _run_single_query(self, query: str) -> None:
        """
        단일 질문 모드 실행

        Args:
            query: 사용자 질문
        """
        self.output_manager.print_info(f"단일 질문 모드: {query}")
        await self._process_query(query)

    async def _run_interactive(self) -> None:
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
                if not await self._handle_command(user_input):
                    break

            except KeyboardInterrupt:
                self.output_manager.print_info("사용자 종료 요청")
                break
            except EOFError:
                self.output_manager.print_info("입력 종료")
                break
            except Exception as e:
                self.output_manager.log_if_debug(f"대화형 모드 오류: {e}", "error")
                self.output_manager.print_error(f"오류: {e}")

    async def _handle_command(self, user_input: str) -> bool:
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
            await self._show_status()
        elif command == Commands.TOOLS:
            await self._show_tools()
        elif command == Commands.CLEAR:
            await self._clear_conversation()
        elif not user_input:
            # 빈 입력은 무시
            pass
        else:
            # AI 응답 처리
            await self._process_query(user_input)

        return True

    async def _process_query(self, user_input: str) -> None:
        """
        사용자 질문 처리

        Args:
            user_input: 사용자 입력
        """
        # 사용자 입력을 히스토리에 추가
        self.conversation_manager.add_to_history("user", user_input)

        # AI 응답 생성
        llm_agent = self.system_manager.get_llm_agent()
        if not llm_agent:
            self.output_manager.print_error(Messages.AGENT_NOT_INITIALIZED)
            return

        self.output_manager.log_if_debug(
            f"=== CLI: 대화형 Agent 처리 시작: '{user_input}' ===")
        self.output_manager.print_system(Messages.ANALYZING)

        try:
            await self._run_interactive_agent(user_input)
        except Exception as e:
            self.output_manager.log_if_debug(
                f"=== CLI: 대화형 Agent 처리 실패: {e} ===", "error")
            self.output_manager.print_error(f"처리 중 오류가 발생했습니다: {str(e)}")

    async def _run_interactive_agent(self, user_input: str) -> None:
        """
        대화형 Agent 실행

        Args:
            user_input: 사용자 입력
        """
        if not self.execution_manager:
            self.output_manager.print_error("실행 관리자가 초기화되지 않았습니다.")
            return

        # 이전 대화 맥락을 포함한 프롬프트 생성
        enhanced_prompt = self.conversation_manager.build_enhanced_prompt(
            user_input)
        self.output_manager.log_if_debug(
            f"=== CLI: 향상된 프롬프트 생성: '{enhanced_prompt[:100]}...' ==="
        )

        # 1단계: 요청 분석 및 계획 수립
        plan = await self.execution_manager.analyze_request_and_plan(enhanced_prompt)

        if not plan:
            # 도구가 필요하지 않은 경우 직접 응답
            llm_agent = self.system_manager.get_llm_agent()
            if llm_agent:
                response_data = await llm_agent.generate_response(enhanced_prompt)
                await self._display_response(response_data)
            return

        # 2단계: 대화형 실행
        await self.execution_manager.execute_interactive_plan(plan, enhanced_prompt)

    async def _display_response(self, response_data: dict) -> None:
        """
        AI 응답 출력

        Args:
            response_data: 응답 데이터
        """
        response = response_data.get("response", "응답을 생성할 수 없습니다.")
        used_tools = response_data.get("used_tools", [])

        self.output_manager.print_response(response, used_tools)

        # Assistant 응답을 히스토리에 추가
        self.conversation_manager.add_to_history(
            "assistant", response, {"used_tools": used_tools})

        self.query_count += 1

        # 응답에서 보류 중인 작업들 추출
        self.conversation_manager.extract_pending_actions(response_data)

        # 도구가 실제로 사용되었다면 보류 작업 클리어 (실행 완료로 간주)
        if used_tools:
            self.conversation_manager.clear_pending_actions()

    async def _show_status(self) -> None:
        """현재 상태 출력"""
        components = self.system_manager.get_system_status()
        pending_actions = self.conversation_manager.get_pending_actions()

        self.output_manager.print_status(
            components,
            self.session_start,
            self.query_count,
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

    async def _cleanup(self) -> None:
        """리소스 정리"""
        await self.system_manager.cleanup()


def create_argument_parser() -> argparse.ArgumentParser:
    """명령행 인수 파서 생성"""
    parser = argparse.ArgumentParser(
        description="DSPilot CLI - AI-Powered Development Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python -m dspilot_cli.cli_main                          # 대화형 모드 (도구 사용 시 사용자 확인)
  python -m dspilot_cli.cli_main --full-auto              # 대화형 모드 (도구 자동 실행)
  python -m dspilot_cli.cli_main "현재 시간은?"             # 단일 질문 (간결 출력)
  python -m dspilot_cli.cli_main "현재 시간은?" --full-auto # 단일 질문 (자동 실행)
  python -m dspilot_cli.cli_main "현재 시간은?" --debug     # 단일 질문 (상세 로그)
  python -m dspilot_cli.cli_main --tools                  # 도구 목록
        """
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="처리할 질문 또는 명령 (없으면 대화형 모드)"
    )

    parser.add_argument(
        "--tools",
        action="store_true",
        help="사용 가능한 MCP 도구 목록 표시"
    )

    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="시스템 진단 실행"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="상세 로그 및 중간 과정 출력"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="상세 로그 출력 (--debug와 동일)"
    )

    parser.add_argument(
        "--full-auto",
        action="store_true",
        help="전체 자동 모드 (사용자 확인 없이 도구 자동 실행)"
    )

    return parser


def setup_logging(debug_mode: bool, quiet_mode: bool) -> None:
    """로깅 설정"""
    if debug_mode:
        logging.getLogger().setLevel(logging.DEBUG)
    elif quiet_mode:
        # 조용한 모드에서는 모든 로깅 완전 차단
        logging.getLogger().setLevel(logging.CRITICAL + 1)

        # 특정 모듈들의 로그도 명시적으로 차단
        for module_name in [
            "mcp_manager", "mcp_tool_manager", "llm_service",
            "application.llm.validators.config_validator",
            "application.llm.agents.base_agent", "dspilot_cli"
        ]:
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(logging.CRITICAL + 1)
            module_logger.disabled = True
    else:
        # 일반 모드에서도 MCP 도구들의 로그는 숨김
        mcp_loggers = [
            "mcp.server.lowlevel.server",  # MCP 서버 기본 로그
            "__main__",  # MCP 도구들의 메인 모듈 로그
            "fastmcp",  # FastMCP 로그
            "mcp.server.fastmcp",  # FastMCP 서버 로그
        ]

        for logger_name in mcp_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)  # WARNING 이상만 표시


async def main() -> None:
    """메인 함수"""
    # 프로젝트 루트를 Python 경로에 추가
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    # 컬러 출력 초기화
    colorama.init()

    args = create_argument_parser().parse_args()

    # 모드 설정
    debug_mode = args.debug or args.verbose
    quiet_mode = bool(args.query) and not debug_mode
    full_auto_mode = args.full_auto

    # 로깅 설정
    setup_logging(debug_mode, quiet_mode)

    cli = DSPilotCLI(
        debug_mode=debug_mode,
        quiet_mode=quiet_mode,
        full_auto_mode=full_auto_mode
    )

    try:
        # 특수 명령 처리
        if args.tools:
            await cli.initialize()
            await cli._show_tools()# pylint: disable=protected-access
            return

        if args.diagnose:
            await cli.initialize()
            await cli._show_status() # pylint: disable=protected-access
            return

        # 일반 실행
        await cli.run(query=args.query)

    except KeyboardInterrupt:
        if not quiet_mode:
            print(
                f"\n{StyleColors.WARNING}🛑 사용자에 의해 중단되었습니다{StyleColors.RESET_ALL}")
    except Exception as e:
        if debug_mode:
            print(f"{StyleColors.ERROR}❌ 오류 발생: {e}{StyleColors.RESET_ALL}")
        elif not quiet_mode:
            print(f"오류 발생: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 종료되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
