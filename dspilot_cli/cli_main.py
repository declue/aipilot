#!/usr/bin/env python3
"""
DSPilot CLI - 메인 엔트리 포인트

이 모듈은 *프로세스 부트스트랩per* 로서 다음 책임을 집니다.

1. **명령행 인수 파싱** (`argparse`)  
   사용자 옵션을 읽어 `DSPilotCLI` 인스턴스 생성에 필요한 파라미터로 변환합니다.
2. **로깅·컬러 초기화**  
   `colorama` 를 통해 Windows 호환 ANSI 컬러 지원, 로깅 레벨 설정.
3. **특수 명령 처리**  
   `--tools`, `--diagnose` 등은 본 모듈에서 바로 처리하여 빠른 응답 제공.
4. **비동기 앱 실행**  
   `asyncio.run()` 으로 `DSPilotCLI.run()` 호출.

아래 ASCII 시퀀스 다이어그램은 주요 흐름을 보여줍니다.

```mermaid
sequenceDiagram
    participant User
    participant CLI_Main as cli_main.py
    participant DSPilotCLI
    participant SystemManager
    User->>CLI_Main: dspilot_cli --full-auto "질문"
    CLI_Main->>DSPilotCLI: 인스턴스화
    CLI_Main-->>DSPilotCLI: run(query)
    DSPilotCLI->>SystemManager: initialize()
    DSPilotCLI->>User: (응답)
```
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import colorama

from dspilot_cli.cli_application import DSPilotCLI
from dspilot_cli.constants import Defaults, StyleColors


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
  python -m dspilot_cli.cli_main "현재 시간은?" --stream    # 단일 질문 (스트리밍 출력)
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

    parser.add_argument(
        "--stream",
        action="store_true",
        help="스트리밍 모드 (LLM 응답을 실시간으로 출력)"
    )

    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=Defaults.MAX_ITERATIONS,
        help="Agent 반복 실행 최대 횟수 (기본 30)"
    )

    parser.add_argument(
        "--validate-mode",
        choices=["auto", "off", "strict"],
        default=Defaults.VALIDATE_MODE,
        help="도구 결과 검증 모드(auto/off/strict)"
    )

    parser.add_argument(
        "--step-retries",
        type=int,
        default=Defaults.MAX_STEP_RETRIES,
        help="단계 실패 시 자동 재시도 횟수 (기본 2)"
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
            "dspilot_core.llm.validators.config_validator",
            "dspilot_core.llm.agents.base_agent", "dspilot_cli"
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


async def handle_special_commands(cli: DSPilotCLI, args) -> bool:
    """특수 명령 처리. 처리된 경우 True 반환"""
    if args.tools:
        await cli.initialize()
        await cli.command_handler._show_tools()  # pylint: disable=protected-access
        return True

    if args.diagnose:
        await cli.initialize()
        await cli.command_handler._show_status_with_session()  # pylint: disable=protected-access
        return True

    return False


async def main() -> None:
    """메인 함수"""
    # 프로젝트 루트를 Python 경로에 추가
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    # 컬러 출력 초기화
    colorama.init()

    args = create_argument_parser().parse_args()

    # 모드 설정
    debug_mode = args.debug
    verbose_mode = args.verbose
    # verbose는 debug_mode에서 제외
    quiet_mode = bool(args.query) and not debug_mode
    full_auto_mode = args.full_auto
    stream_mode = args.stream
    max_iterations = args.iterations
    validate_mode = args.validate_mode
    step_retries = args.step_retries

    # 로깅 설정
    setup_logging(debug_mode or verbose_mode, quiet_mode)

    cli = DSPilotCLI(
        debug_mode=debug_mode,
        quiet_mode=quiet_mode,
        full_auto_mode=full_auto_mode,
        stream_mode=stream_mode,
        verbose_mode=verbose_mode,
        max_iterations=max_iterations,
        validate_mode=validate_mode,
        max_step_retries=step_retries
    )

    try:
        # 특수 명령 처리
        if await handle_special_commands(cli, args):
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
