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
        
        # 대화 히스토리 관리
        self.conversation_history = []
        self.pending_actions = []  # 보류 중인 작업들
        
        logger.info("DSPilotCLI 초기화")

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
        """이전 대화 맥락을 포함한 향상된 프롬프트 생성"""
        context = self.get_recent_context()
        
        if not context:
            return user_input
        
        # 보류 중인 작업이 있으면 포함
        pending_context = ""
        if self.pending_actions:
            pending_context = "\n\n[보류 중인 작업들]:\n" + "\n".join(f"- {action}" for action in self.pending_actions)
        
        # 사용자 요청 패턴 분석을 위한 힌트 추가
        workflow_hints = self._analyze_request_pattern(user_input)
        
        enhanced_prompt = f"""이전 대화 맥락:
{context}

{pending_context}

{workflow_hints}

현재 사용자 요청: {user_input}

위의 대화 맥락과 워크플로우 힌트를 고려하여 응답해주세요. 특히:
1. 이전에 제안한 작업이나 변경사항을 사용자가 확인/적용을 요청하는 경우, 해당 내용을 바탕으로 즉시 실행해주세요.
2. 복합적인 요청의 경우 단계별로 계획을 수립하고 순차적으로 실행해주세요.
3. 데이터 수집, 처리, 저장이 모두 필요한 경우 각 단계를 완료한 후 다음 단계로 진행해주세요."""

        return enhanced_prompt

    def _analyze_request_pattern(self, user_input: str) -> str:
        """사용자 요청 패턴을 분석하여 워크플로우 힌트 제공"""
        hints = []
        input_lower = user_input.lower()
        
        # 파일 저장 관련 패턴
        if any(keyword in input_lower for keyword in ["저장", "save", "파일", "file", ".json", ".txt", ".csv"]):
            hints.append("📁 파일 저장 작업이 감지됨 → 데이터 수집 후 적절한 형식으로 파일 저장 필요")
        
        # 검색 및 정보 수집 패턴
        if any(keyword in input_lower for keyword in ["뉴스", "검색", "찾아", "정보", "현재", "오늘", "최신"]):
            hints.append("🔍 정보 수집 작업이 감지됨 → 웹 검색 또는 실시간 데이터 조회 필요")
        
        # 복합 작업 패턴 (수집 + 저장)
        has_collection = any(keyword in input_lower for keyword in ["뉴스", "검색", "정보", "데이터"])
        has_storage = any(keyword in input_lower for keyword in ["저장", "파일", ".json", ".txt"])
        if has_collection and has_storage:
            hints.append("🔄 복합 워크플로우 감지됨 → 1단계: 데이터 수집, 2단계: 처리/정제, 3단계: 파일 저장")
        
        # 시간 관련 패턴
        if any(keyword in input_lower for keyword in ["시간", "time", "날짜", "date", "현재", "지금"]):
            hints.append("⏰ 시간 정보 요청 감지됨 → 현재 시간/날짜 조회 필요")
        
        # 날씨 관련 패턴
        if any(keyword in input_lower for keyword in ["날씨", "weather", "기온", "온도"]):
            hints.append("🌤️ 날씨 정보 요청 감지됨 → 날씨 데이터 조회 필요")
        
        # 연속 작업 패턴 (이전 작업 참조)
        if any(keyword in input_lower for keyword in ["적용", "실행", "해줘", "진행", "계속"]):
            hints.append("▶️ 이전 작업 연속 실행 요청 감지됨 → 보류된 작업 또는 제안된 변경사항 실행")
        
        if not hints:
            hints.append("💭 일반적인 요청 → 사용자 의도에 따라 적절한 도구 선택")
        
        return "\n[워크플로우 힌트]:\n" + "\n".join(f"  {hint}" for hint in hints)

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
            self.mcp_tool_manager = MCPToolManager(self.mcp_manager, self.config_manager)
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
                        # CLI 히스토리도 초기화
                        self.conversation_history.clear()
                        self.clear_pending_actions()
                        print(f"{StyleColors.SUCCESS}✓ 대화 기록이 초기화되었습니다.{StyleColors.RESET_ALL}")
                    continue
                elif not user_input:
                    continue

                # 사용자 입력을 히스토리에 추가
                self.add_to_history("user", user_input)

                # AI 응답 생성 (향상된 프롬프트 사용)
                if self.llm_agent:
                    print(f"{StyleColors.SYSTEM}🤖 처리 중...{StyleColors.RESET_ALL}")
                    
                    # 이전 대화 맥락을 포함한 프롬프트 생성
                    enhanced_prompt = self.build_enhanced_prompt(user_input)
                    response_data = await self.llm_agent.generate_response(enhanced_prompt)

                    # 응답 출력
                    response = response_data.get("response", "응답을 생성할 수 없습니다.")
                    print(f"{StyleColors.ASSISTANT}🤖 Assistant: {response}{StyleColors.RESET_ALL}")

                    # 사용된 도구 정보
                    used_tools = response_data.get("used_tools", [])
                    if used_tools:
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
