#!/usr/bin/env python3
"""
DSPilot CLI - 고급 LLM + MCP + ReAct Agent CLI 도구
Claude Code / Codex 스타일의 직관적이고 강력한 CLI 인터페이스

사용법:
  python dspilot_cli.py                    # 대화형 모드
  python dspilot_cli.py "질문"             # 단일 질문 모드
  python dspilot_cli.py --diagnose         # 시스템 진단
  python dspilot_cli.py --tools            # MCP 도구 목록
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import colorama
from colorama import Fore, Style

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from application.config.config_manager import ConfigManager
from application.llm.agents.agent_factory import AgentFactory
from application.llm.agents.base_agent import BaseAgent
from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager
from application.util.logger import setup_logger

# 컬러 출력 초기화
colorama.init()

logger = setup_logger("dspilot_cli") or logging.getLogger("dspilot_cli")


class StyleColors:
    """색상 스타일 정의"""

    HEADER = Fore.CYAN + Style.BRIGHT
    SUCCESS = Fore.GREEN + Style.BRIGHT
    WARNING = Fore.YELLOW + Style.BRIGHT
    ERROR = Fore.RED + Style.BRIGHT
    INFO = Fore.BLUE + Style.BRIGHT
    SYSTEM = Fore.MAGENTA + Style.BRIGHT
    USER = Fore.WHITE + Style.BRIGHT
    ASSISTANT = Fore.CYAN
    RESET_ALL = Style.RESET_ALL


class DSPilotCLI:
    """DSPilot CLI 메인 클래스"""

    def __init__(self) -> None:
        self.config_manager: Optional[ConfigManager] = None
        self.llm_agent: Optional[BaseAgent] = None
        self.mcp_manager: Optional[MCPManager] = None
        self.mcp_tool_manager: Optional[MCPToolManager] = None
        self.session_start = datetime.now()
        self.query_count = 0

        logger.info("DSPilotCLI 초기화")

    def print_banner(self) -> None:
        """CLI 시작 배너 출력"""
        banner = f"""
{StyleColors.HEADER}
╔════════════════════════════════════════════════════════════════╗
║                          🚀 DSPilot CLI                        ║
║                    AI-Powered Development Assistant            ║
╚════════════════════════════════════════════════════════════════╝
{StyleColors.RESET_ALL}
        """
        print(banner)

    async def initialize(self) -> bool:
        """시스템 초기화"""
        try:
            self.print_banner()
            print(f"{StyleColors.SYSTEM}🔧 시스템 초기화 중...{StyleColors.RESET_ALL}")

            # ConfigManager 초기화
            self.config_manager = ConfigManager()
            print(f"{StyleColors.SUCCESS}✓ 설정 관리자 초기화 완료{StyleColors.RESET_ALL}")

            # MCPManager 초기화
            self.mcp_manager = MCPManager(self.config_manager)
            print(f"{StyleColors.SUCCESS}✓ MCP 관리자 초기화 완료{StyleColors.RESET_ALL}")

            # MCPToolManager 초기화 및 MCP 도구 로드
            self.mcp_tool_manager = MCPToolManager(self.mcp_manager)
            init_success = await self.mcp_tool_manager.initialize()

            if init_success:
                print(
                    f"{StyleColors.SUCCESS}✓ MCP 도구 관리자 초기화 완료{StyleColors.RESET_ALL}"
                )
            else:
                print(
                    f"{StyleColors.WARNING}⚠ MCP 도구 초기화 실패 (기본 모드만 사용 가능){StyleColors.RESET_ALL}"
                )

            # Agent 초기화
            self.llm_agent = AgentFactory.create_agent(self.config_manager, self.mcp_tool_manager)
            print(f"{StyleColors.SUCCESS}✓ Agent 초기화 완료{StyleColors.RESET_ALL}")

            return True

        except Exception as e:
            logger.error(f"초기화 실패: {e}")
            print(f"{StyleColors.ERROR}❌ 초기화 실패: {e}{StyleColors.RESET_ALL}")
            return False

    def print_status(self) -> None:
        """현재 상태 출력"""
        print(f"\n{StyleColors.INFO}📊 시스템 상태:{StyleColors.RESET_ALL}")

        status_items = [
            ("설정 관리자", self.config_manager),
            ("MCP 관리자", self.mcp_manager),
            ("MCP 도구 관리자", self.mcp_tool_manager),
            ("Agent", self.llm_agent),
        ]

        for name, component in status_items:
            status = "✓ 활성" if component is not None else "✗ 비활성"
            color = StyleColors.SUCCESS if component is not None else StyleColors.ERROR
            print(f"  {color}{name}: {status}{StyleColors.RESET_ALL}")

        # 세션 정보
        runtime = datetime.now() - self.session_start
        print(f"\n{StyleColors.INFO}📈 세션 정보:{StyleColors.RESET_ALL}")
        print(f"  실행 시간: {runtime}")
        print(f"  처리된 쿼리: {self.query_count}개")

    def print_help(self) -> None:
        """도움말 출력"""
        help_text = f"""
{StyleColors.INFO}📖 사용 가능한 명령어:{StyleColors.RESET_ALL}

  {StyleColors.SYSTEM}help{StyleColors.RESET_ALL}     - 이 도움말 표시
  {StyleColors.SYSTEM}status{StyleColors.RESET_ALL}   - 시스템 상태 확인
  {StyleColors.SYSTEM}clear{StyleColors.RESET_ALL}    - 대화 기록 초기화
  {StyleColors.SYSTEM}exit{StyleColors.RESET_ALL}     - 프로그램 종료
  {StyleColors.SYSTEM}quit{StyleColors.RESET_ALL}     - 프로그램 종료

  {StyleColors.INFO}💡 일반 질문이나 요청을 입력하면 AI가 응답합니다.{StyleColors.RESET_ALL}
        """
        print(help_text)

    async def run_interactive(self) -> None:
        """대화형 모드 실행"""
        print(f"\n{StyleColors.SUCCESS}🎯 대화형 모드 시작{StyleColors.RESET_ALL}")
        print(f"{StyleColors.INFO}도움말: 'help' 입력, 종료: 'exit' 또는 Ctrl+C{StyleColors.RESET_ALL}")
        self.print_help()

        while True:
            try:
                # 사용자 입력 받기
                user_input = input(f"\n{StyleColors.USER}👤 You: {StyleColors.RESET_ALL}").strip()

                # 명령어 처리
                if user_input.lower() in ["exit", "quit", "q"]:
                    print(f"{StyleColors.INFO}👋 안녕히 가세요!{StyleColors.RESET_ALL}")
                    break
                elif user_input.lower() == "help":
                    self.print_help()
                    continue
                elif user_input.lower() == "status":
                    self.print_status()
                    continue
                elif user_input.lower() == "clear":
                    if self.llm_agent:
                        self.llm_agent.clear_conversation()
                        print(f"{StyleColors.SUCCESS}✓ 대화 기록이 초기화되었습니다.{StyleColors.RESET_ALL}")
                    continue
                elif not user_input:
                    continue

                # AI 응답 생성
                if self.llm_agent:
                    print(f"{StyleColors.SYSTEM}🤖 처리 중...{StyleColors.RESET_ALL}")
                    response_data = await self.llm_agent.generate_response(user_input)

                    # 응답 출력
                    response = response_data.get("response", "응답을 생성할 수 없습니다.")
                    print(f"{StyleColors.ASSISTANT}🤖 Assistant: {response}{StyleColors.RESET_ALL}")

                    # 추가 정보 출력
                    if response_data.get("used_tools"):
                        tools = ", ".join(response_data["used_tools"])
                        print(f"{StyleColors.INFO}🔧 사용된 도구: {tools}{StyleColors.RESET_ALL}")

                    self.query_count += 1
                else:
                    print(f"{StyleColors.ERROR}❌ Agent가 초기화되지 않았습니다.{StyleColors.RESET_ALL}")

            except KeyboardInterrupt:
                print(f"\n{StyleColors.INFO}👋 사용자 종료 요청{StyleColors.RESET_ALL}")
                break
            except EOFError:
                print(f"\n{StyleColors.INFO}👋 입력 종료{StyleColors.RESET_ALL}")
                break
            except Exception as e:
                logger.error(f"대화형 모드 오류: {e}")
                print(f"{StyleColors.ERROR}❌ 오류: {e}{StyleColors.RESET_ALL}")

    async def cleanup(self) -> None:
        """리소스 정리"""
        try:
            print(f"{StyleColors.SYSTEM}🧹 리소스 정리 중...{StyleColors.RESET_ALL}")

            if self.llm_agent:
                await self.llm_agent.cleanup()

            if self.mcp_tool_manager:
                await self.mcp_tool_manager.cleanup()

            if self.mcp_manager:
                await self.mcp_manager.cleanup()

            print(f"{StyleColors.SUCCESS}✓ 정리 완료{StyleColors.RESET_ALL}")

        except Exception as e:
            logger.error(f"정리 중 오류: {e}")

    async def run(self) -> None:
        """메인 실행 함수"""
        try:
            # 초기화
            if not await self.initialize():
                return

            # 대화형 모드 실행
            await self.run_interactive()

        except Exception as e:
            logger.error(f"실행 중 오류: {e}")
            print(f"{StyleColors.ERROR}❌ 실행 중 오류: {e}{StyleColors.RESET_ALL}")
        finally:
            await self.cleanup()


async def main() -> None:
    """메인 함수"""
    cli = DSPilotCLI()
    await cli.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 종료되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
        logging.error(f"메인 함수 오류: {e}")
