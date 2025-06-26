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

import argparse
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

    def __init__(self, debug_mode: bool = False, quiet_mode: bool = False) -> None:
        self.config_manager: Optional[ConfigManager] = None
        self.llm_agent: Optional[BaseAgent] = None
        self.mcp_manager: Optional[MCPManager] = None
        self.mcp_tool_manager: Optional[MCPToolManager] = None
        self.session_start = datetime.now()
        self.query_count = 0
        
        # 출력 모드 설정
        self.debug_mode = debug_mode
        self.quiet_mode = quiet_mode
        
        # 대화 히스토리 관리
        self.conversation_history = []
        self.pending_actions = []  # 보류 중인 작업들
        
        if not self.quiet_mode:
            logger.info("DSPilotCLI 초기화")

    def print_if_not_quiet(self, message: str) -> None:
        """조용한 모드가 아닐 때만 출력"""
        if not self.quiet_mode:
            print(message)

    def log_if_debug(self, message: str, level: str = "info") -> None:
        """디버그 모드일 때만 로그 출력"""
        if self.debug_mode:
            if level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)
            else:
                logger.info(message)

    def add_to_history(self, role: str, content: str, metadata: dict = None) -> None:
        """대화 히스토리에 메시지 추가"""
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.conversation_history.append(entry)

    def get_recent_context(self, max_turns: int = 5) -> str:
        """최근 대화 컨텍스트를 문자열로 반환"""
        if not self.conversation_history:
            return ""
        
        # 최근 N턴의 대화만 가져오기
        recent_messages = self.conversation_history[-max_turns*2:] if len(self.conversation_history) > max_turns*2 else self.conversation_history
        
        context_parts = []
        for entry in recent_messages:
            role_prefix = "👤 User" if entry["role"] == "user" else "🤖 Assistant"
            context_parts.append(f"{role_prefix}: {entry['content']}")
            
            # 도구 사용 정보가 있으면 추가
            if entry["metadata"].get("used_tools"):
                tools = ", ".join(entry["metadata"]["used_tools"])
                context_parts.append(f"   [사용된 도구: {tools}]")
        
        return "\n".join(context_parts)

    def build_enhanced_prompt(self, user_input: str) -> str:
        """이전 대화 맥락을 포함한 향상된 프롬프트 생성 (키워드 판단 제거)"""
        context = self.get_recent_context()
        
        if not context:
            return user_input

        # 보류 중인 작업이 있으면 포함
        pending_context = ""
        if self.pending_actions:
            pending_context = "\n\n[보류 중인 작업들]:\n" + "\n".join(f"- {action}" for action in self.pending_actions)

        enhanced_prompt = f"""이전 대화 맥락:
{context}

{pending_context}

현재 사용자 요청: {user_input}

위의 대화 맥락을 고려하여 응답해주세요. 특히:
1. 이전에 제안한 작업이나 변경사항을 사용자가 확인/적용을 요청하는 경우, 해당 내용을 바탕으로 즉시 실행해주세요.
2. 복합적인 요청의 경우 단계별로 계획을 수립하고 순차적으로 실행해주세요.
3. 데이터 수집, 처리, 저장이 모두 필요한 경우 각 단계를 완료한 후 다음 단계로 진행해주세요."""

        return enhanced_prompt

    def extract_pending_actions(self, response_data: dict) -> None:
        """응답에서 보류 중인 작업들을 추출하여 저장"""
        response = response_data.get("response", "")
        
        # 간단한 패턴으로 제안된 변경사항 감지 (범용적 접근)
        if any(keyword in response.lower() for keyword in ["수정하겠습니다", "변경하겠습니다", "적용하겠습니다", "수정할까요", "변경할까요"]):
            # 코드 블록이나 파일 경로가 포함된 경우
            if "```" in response or any(ext in response for ext in [".py", ".js", ".ts", ".java", ".cpp", ".txt"]):
                self.pending_actions.append("파일 수정/생성 작업")
        
        # 최대 3개의 보류 작업만 유지
        if len(self.pending_actions) > 3:
            self.pending_actions = self.pending_actions[-3:]

    def clear_pending_actions(self) -> None:
        """보류 중인 작업들 초기화"""
        self.pending_actions.clear()

    def print_banner(self) -> None:
        """CLI 시작 배너 출력"""
        if self.quiet_mode:
            return
            
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
            self.print_if_not_quiet(f"{StyleColors.SYSTEM}🔧 시스템 초기화 중...{StyleColors.RESET_ALL}")

            # ConfigManager 초기화
            self.config_manager = ConfigManager()
            self.print_if_not_quiet(f"{StyleColors.SUCCESS}✓ 설정 관리자 초기화 완료{StyleColors.RESET_ALL}")

            # MCPManager 초기화
            self.mcp_manager = MCPManager(self.config_manager)
            self.print_if_not_quiet(f"{StyleColors.SUCCESS}✓ MCP 관리자 초기화 완료{StyleColors.RESET_ALL}")

            # MCPToolManager 초기화 및 MCP 도구 로드
            self.mcp_tool_manager = MCPToolManager(self.mcp_manager, self.config_manager)
            init_success = await self.mcp_tool_manager.initialize()

            if init_success:
                self.print_if_not_quiet(
                    f"{StyleColors.SUCCESS}✓ MCP 도구 관리자 초기화 완료{StyleColors.RESET_ALL}"
                )
            else:
                self.print_if_not_quiet(
                    f"{StyleColors.WARNING}⚠ MCP 도구 초기화 실패 (기본 모드만 사용 가능){StyleColors.RESET_ALL}"
                )

            # Agent 초기화
            self.log_if_debug("Agent 생성 중...")
            self.llm_agent = AgentFactory.create_agent(self.config_manager, self.mcp_tool_manager)
            
            self.print_if_not_quiet(f"{StyleColors.SUCCESS}✓ Agent 초기화 완료{StyleColors.RESET_ALL}")

            return True

        except Exception as e:
            self.log_if_debug(f"초기화 실패: {e}", "error")
            if not self.quiet_mode:
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
        print(f"  대화 히스토리: {len(self.conversation_history)}개 메시지")
        
        # 보류 중인 작업 정보
        if self.pending_actions:
            print(f"\n{StyleColors.WARNING}⏳ 보류 중인 작업:{StyleColors.RESET_ALL}")
            for i, action in enumerate(self.pending_actions, 1):
                print(f"  {i}. {action}")
        else:
            print(f"\n{StyleColors.SUCCESS}✅ 보류 중인 작업 없음{StyleColors.RESET_ALL}")

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
        """
        print(help_text)

    async def print_tools_list(self) -> None:
        """사용 가능한 MCP 도구 목록 출력"""
        print(f"\n{StyleColors.INFO}🔧 사용 가능한 MCP 도구:{StyleColors.RESET_ALL}")
        
        if self.mcp_tool_manager and hasattr(self.mcp_tool_manager, 'tools'):
            tools = getattr(self.mcp_tool_manager, 'tools', [])
            if tools:
                for i, tool in enumerate(tools, 1):
                    tool_name = getattr(tool, 'name', 'Unknown')
                    tool_desc = getattr(tool, 'description', 'No description')
                    print(f"  {i:2d}. {StyleColors.SUCCESS}{tool_name}{StyleColors.RESET_ALL}")
                    print(f"      {tool_desc}")
                print(f"\n{StyleColors.INFO}총 {len(tools)}개의 도구가 사용 가능합니다.{StyleColors.RESET_ALL}")
            else:
                print(f"  {StyleColors.WARNING}사용 가능한 도구가 없습니다.{StyleColors.RESET_ALL}")
        else:
            print(f"  {StyleColors.ERROR}MCP 도구 관리자가 초기화되지 않았습니다.{StyleColors.RESET_ALL}")

    async def run_interactive(self) -> None:
        """대화형 모드 실행"""
        self.print_if_not_quiet(f"\n{StyleColors.SUCCESS}🎯 대화형 모드 시작{StyleColors.RESET_ALL}")
        self.print_if_not_quiet(f"{StyleColors.INFO}도움말: 'help' 입력, 종료: 'exit' 또는 Ctrl+C{StyleColors.RESET_ALL}")
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
                elif user_input.lower() == "tools":
                    await self.print_tools_list()
                    continue
                elif user_input.lower() == "clear":
                    if self.llm_agent:
                        self.llm_agent.clear_conversation()
                        # CLI 히스토리도 초기화
                        self.conversation_history.clear()
                        self.clear_pending_actions()
                        print(f"{StyleColors.SUCCESS}✓ 대화 기록이 초기화되었습니다.{StyleColors.RESET_ALL}")
                    continue
                elif not user_input:
                    continue

                # AI 응답 처리
                await self.process_query(user_input)

            except KeyboardInterrupt:
                print(f"\n{StyleColors.INFO}👋 사용자 종료 요청{StyleColors.RESET_ALL}")
                break
            except EOFError:
                print(f"\n{StyleColors.INFO}👋 입력 종료{StyleColors.RESET_ALL}")
                break
            except Exception as e:
                self.log_if_debug(f"대화형 모드 오류: {e}", "error")
                print(f"{StyleColors.ERROR}❌ 오류: {e}{StyleColors.RESET_ALL}")

    async def run_single_query(self, query: str) -> None:
        """단일 질문 모드 실행"""
        if not self.quiet_mode:
            print(f"{StyleColors.INFO}🎯 단일 질문 모드: {query}{StyleColors.RESET_ALL}")
        await self.process_query(query)

    async def process_query(self, user_input: str) -> None:
        """사용자 질문 처리"""
        # 사용자 입력을 히스토리에 추가
        self.add_to_history("user", user_input)

        # AI 응답 생성 (향상된 프롬프트 사용)
        if self.llm_agent:
            self.log_if_debug(f"=== CLI: AI 질문 처리 시작: '{user_input}' ===")
            
            # 이전 대화 맥락을 포함한 프롬프트 생성
            enhanced_prompt = self.build_enhanced_prompt(user_input)
            self.log_if_debug(f"=== CLI: 향상된 프롬프트 생성: '{enhanced_prompt[:100]}...' ===")
            self.log_if_debug(f"=== CLI: 사용할 Agent: {type(self.llm_agent).__name__} ===")
            
            if not self.quiet_mode:
                print(f"{StyleColors.SYSTEM}🤖 처리 중...{StyleColors.RESET_ALL}")
            
            try:
                response_data = await self.llm_agent.generate_response(enhanced_prompt)
                self.log_if_debug(f"=== CLI: Agent 응답 수신 완료 ===")

                # 응답 출력
                response = response_data.get("response", "응답을 생성할 수 없습니다.")
                
                if self.quiet_mode:
                    # 조용한 모드에서는 응답만 출력
                    print(response)
                else:
                    # 일반 모드에서는 스타일링 적용
                    print(f"{StyleColors.ASSISTANT}🤖 Assistant: {response}{StyleColors.RESET_ALL}")

                # 사용된 도구 정보
                used_tools = response_data.get("used_tools", [])
                if used_tools and not self.quiet_mode:
                    tools = ", ".join(used_tools)
                    print(f"{StyleColors.INFO}🔧 사용된 도구: {tools}{StyleColors.RESET_ALL}")

                # Assistant 응답을 히스토리에 추가
                self.add_to_history("assistant", response, {"used_tools": used_tools})

                self.query_count += 1

                # 응답에서 보류 중인 작업들 추출
                self.extract_pending_actions(response_data)
                
                # 도구가 실제로 사용되었다면 보류 작업 클리어 (실행 완료로 간주)
                if used_tools:
                    self.clear_pending_actions()
                    
            except Exception as e:
                self.log_if_debug(f"=== CLI: AI 질문 처리 실패: {e} ===", "error")
                error_msg = f"처리 중 오류가 발생했습니다: {str(e)}"
                if self.quiet_mode:
                    print(error_msg)
                else:
                    print(f"{StyleColors.ERROR}❌ {error_msg}{StyleColors.RESET_ALL}")
                
        else:
            error_msg = "Agent가 초기화되지 않았습니다."
            if self.quiet_mode:
                print(error_msg)
            else:
                print(f"{StyleColors.ERROR}❌ {error_msg}{StyleColors.RESET_ALL}")

    async def cleanup(self) -> None:
        """리소스 정리"""
        try:
            self.print_if_not_quiet(f"{StyleColors.SYSTEM}🧹 리소스 정리 중...{StyleColors.RESET_ALL}")

            if self.llm_agent:
                await self.llm_agent.cleanup()

            if self.mcp_tool_manager:
                await self.mcp_tool_manager.cleanup()

            if self.mcp_manager:
                await self.mcp_manager.cleanup()

            self.print_if_not_quiet(f"{StyleColors.SUCCESS}✓ 정리 완료{StyleColors.RESET_ALL}")

        except Exception as e:
            self.log_if_debug(f"정리 중 오류: {e}", "error")

    async def run(self, query: Optional[str] = None) -> None:
        """메인 실행 함수"""
        try:
            # 초기화
            if not await self.initialize():
                return

            # 모드에 따라 실행
            if query:
                await self.run_single_query(query)
            else:
                await self.run_interactive()

        except Exception as e:
            self.log_if_debug(f"실행 중 오류: {e}", "error")
            error_msg = f"실행 중 오류: {e}"
            if self.quiet_mode:
                print(error_msg)
            else:
                print(f"{StyleColors.ERROR}❌ {error_msg}{StyleColors.RESET_ALL}")
        finally:
            await self.cleanup()


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description="DSPilot CLI - AI-Powered Development Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python dspilot_cli.py                          # 대화형 모드
  python dspilot_cli.py "현재 시간은?"             # 단일 질문 (간결 출력)
  python dspilot_cli.py "현재 시간은?" --debug     # 단일 질문 (상세 로그)
  python dspilot_cli.py --tools                  # 도구 목록
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
    
    return parser.parse_args()


async def main() -> None:
    """메인 함수"""
    args = parse_arguments()
    
    # 디버그 모드 설정
    debug_mode = args.debug or args.verbose
    
    # 조용한 모드 설정 (단일 질문 모드이고 디버그가 아닌 경우)
    quiet_mode = bool(args.query) and not debug_mode
    
    # 로깅 레벨 설정
    if debug_mode:
        logging.getLogger().setLevel(logging.DEBUG)
    elif quiet_mode:
        # 조용한 모드에서는 모든 로깅 완전 차단
        logging.getLogger().setLevel(logging.CRITICAL + 1)  # 모든 로그 차단
        
        # 특정 모듈들의 로그도 명시적으로 차단
        for module_name in [
            "mcp_manager", "mcp_tool_manager", "llm_service", 
            "application.llm.validators.config_validator",
            "application.llm.agents.base_agent", "dspilot_cli"
        ]:
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(logging.CRITICAL + 1)
            module_logger.disabled = True
    
    cli = DSPilotCLI(debug_mode=debug_mode, quiet_mode=quiet_mode)
    
    try:
        # 특수 명령 처리
        if args.tools:
            await cli.initialize()
            await cli.print_tools_list()
            return
        
        if args.diagnose:
            await cli.initialize()
            cli.print_status()
            return
        
        # 일반 실행
        await cli.run(query=args.query)
        
    except Exception as e:
        if debug_mode:
            logger.error(f"메인 함수 오류: {e}")
            print(f"{StyleColors.ERROR}❌ 오류 발생: {e}{StyleColors.RESET_ALL}")
        elif not quiet_mode:
            print(f"오류 발생: {e}")
        # 조용한 모드에서는 오류도 출력하지 않음


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 종료되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
        logging.error(f"메인 함수 오류: {e}")
