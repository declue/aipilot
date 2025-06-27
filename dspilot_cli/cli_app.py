#!/usr/bin/env python3
"""
DSPilot CLI - 고급 LLM + MCP + ReAct Agent CLI 도구
Claude Code / Codex 스타일의 직관적이고 강력한 CLI 인터페이스

사용법:
  dspilot-cli                          # 대화형 모드
  dspilot-cli "질문"                   # 단일 질문 모드
  dspilot-cli --mode basic "질문"      # 특정 모드로 질문
  dspilot-cli --diagnose              # 시스템 진단
  dspilot-cli --config                # 설정 관리
  dspilot-cli --tools                 # MCP 도구 목록
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime
from typing import Optional

import colorama
from colorama import Fore
from colorama import Style as ColoramaStyle

from dspilot_core.config.config_manager import ConfigManager
from dspilot_core.llm.agents.agent_factory import AgentFactory
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_manager import MCPManager
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager
from dspilot_core.tasks.task_manager import TaskManager
from dspilot_core.util.logger import setup_logger

# 색상 초기화
colorama.init(autoreset=True)

# 로거 설정
logger = setup_logger("dspilot_cli") or logging.getLogger("dspilot_cli")


# CLI 스타일 상수
class StyleColors:
    HEADER = Fore.CYAN + ColoramaStyle.BRIGHT
    SUCCESS = Fore.GREEN + ColoramaStyle.BRIGHT
    WARNING = Fore.YELLOW + ColoramaStyle.BRIGHT
    ERROR = Fore.RED + ColoramaStyle.BRIGHT
    INFO = Fore.BLUE + ColoramaStyle.BRIGHT
    PROMPT = Fore.MAGENTA + ColoramaStyle.BRIGHT
    TOOL = Fore.GREEN
    AI_RESPONSE = Fore.WHITE + ColoramaStyle.BRIGHT
    SYSTEM = Fore.CYAN
    METADATA = Fore.BLACK + ColoramaStyle.BRIGHT
    RESET_ALL = ColoramaStyle.RESET_ALL


class DSPilotCLI:
    """DSPilot CLI 메인 클래스"""

    def __init__(self) -> None:
        self.config_manager: Optional[ConfigManager] = None
        self.mcp_manager: Optional[MCPManager] = None
        self.mcp_tool_manager: Optional[MCPToolManager] = None
        self.task_manager: Optional[TaskManager] = None
        self.llm_agent: Optional[BaseAgent] = None
        self.session_start = datetime.now()
        self.query_count = 0

        # 설정
        self.should_exit = False

        logger.debug("DSPilotCLI 초기화")

    def print_banner(self) -> None:
        """CLI 시작 배너 출력"""
        banner = f"""
{StyleColors.HEADER}╔══════════════════════════════════════════════════════════════╗
║                          🤖 DSPilot CLI                     ║
║              Langchain + MCP + ReAct Agent CLI Tool         ║
╚══════════════════════════════════════════════════════════════╝{StyleColors.RESET_ALL}

{StyleColors.INFO}세션 시작: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}{StyleColors.RESET_ALL}
{StyleColors.SYSTEM}도움말: '/help' | 진단: '/diagnose' | 도구: '/tools' | 종료: '/exit'{StyleColors.RESET_ALL}
"""
        print(banner)

    def print_help(self) -> None:
        """도움말 출력"""
        help_text = f"""
{StyleColors.HEADER}📚 DSPilot CLI 도움말{StyleColors.RESET_ALL}

{StyleColors.SUCCESS}기본 명령어:{StyleColors.RESET_ALL}
  질문 입력                     일반적인 AI 질문 (자동 모드 선택)
  /help                        이 도움말 표시
  /exit, /quit                 CLI 종료
  /clear                       대화 히스토리 초기화
  
{StyleColors.SUCCESS}시스템 명령어:{StyleColors.RESET_ALL}
  /diagnose                    시스템 상태 진단
  /config                      현재 설정 표시
  /tools                       사용 가능한 MCP 도구 목록
  /mode [auto|basic|mcp_tools|workflow]  LLM 모드 변경
  /profile [profile_name]      LLM 프로필 변경
  
{StyleColors.SUCCESS}고급 명령어:{StyleColors.RESET_ALL}
  /debug on|off                디버그 모드 토글
  /stats                       세션 통계 표시
  /export [filename]           대화 히스토리 내보내기
  /test [tool_name]            특정 MCP 도구 테스트

{StyleColors.SUCCESS}자동 모드 특징:{StyleColors.RESET_ALL}
  • {StyleColors.INFO}auto{StyleColors.RESET_ALL}         질문 내용에 따라 최적 모드 자동 선택
  • {StyleColors.INFO}basic{StyleColors.RESET_ALL}        기본 LLM 응답 (빠름)
  • {StyleColors.INFO}mcp_tools{StyleColors.RESET_ALL}    ReAct + MCP 도구 사용 (다기능)
  • {StyleColors.INFO}workflow{StyleColors.RESET_ALL}     워크플로우 기반 처리 (복합 작업)
  
{StyleColors.SUCCESS}예시:{StyleColors.RESET_ALL}
  "오늘 날씨 어때?"            → 자동으로 MCP weather 도구 사용
  "지금 시간 알려줘"           → 자동으로 MCP time 도구 사용
  "Python 문법 설명해줘"       → 기본 LLM 응답
  "프로젝트 계획 세워줘"       → 워크플로우 모드 사용
"""
        print(help_text)

    async def initialize(self) -> bool:
        """시스템 초기화"""
        try:
            print(f"{StyleColors.SYSTEM}🔧 시스템 초기화 중...{StyleColors.RESET_ALL}")

            # 1. 설정 매니저 초기화
            print(f"{StyleColors.INFO}1. 설정 매니저 초기화 중...{StyleColors.RESET_ALL}")
            self.config_manager = ConfigManager()
            # ConfigManager는 별도 initialize가 필요 없음
            print(f"{StyleColors.SUCCESS}✓ 설정 관리자 초기화 완료{StyleColors.RESET_ALL}")

            # 2. MCP 관련 초기화
            print(f"{StyleColors.INFO}2. MCP 매니저 초기화 중...{StyleColors.RESET_ALL}")
            self.mcp_manager = MCPManager(self.config_manager)
            # MCPManager는 별도 initialize가 필요 없음
            print(f"{StyleColors.SUCCESS}✓ MCP 관리자 초기화 완료{StyleColors.RESET_ALL}")

            self.mcp_tool_manager = MCPToolManager(self.mcp_manager, self.config_manager)
            await self.mcp_tool_manager.initialize()

            # 3. 태스크 매니저 초기화 (선택적)
            print(f"{StyleColors.INFO}3. 태스크 매니저 초기화 중...{StyleColors.RESET_ALL}")
            try:
                self.task_manager = TaskManager()
                print(f"{StyleColors.SUCCESS}✓ 태스크 관리자 초기화 완료{StyleColors.RESET_ALL}")
            except Exception as e:
                print(f"{StyleColors.WARNING}⚠ 태스크 관리자 초기화 실패 (계속 진행): {e}{StyleColors.RESET_ALL}")
                logger.warning(f"태스크 관리자 초기화 실패: {e}")

            # 4. Agent 초기화 (자동 모드로 설정)
            print(f"{StyleColors.INFO}4. Agent 초기화 중...{StyleColors.RESET_ALL}")
            await self.setup_intelligent_agent()
            print(f"{StyleColors.SUCCESS}✓ LLM 에이전트 초기화 완료{StyleColors.RESET_ALL}")

            # 현재 설정 표시
            await self.show_current_config()

            return True

        except Exception as e:
            print(f"{StyleColors.ERROR}❌ 초기화 실패: {e}{StyleColors.RESET_ALL}")
            logger.error(f"초기화 실패: {e}")
            return False

    async def setup_intelligent_agent(self) -> None:
        """지능형 Agent 설정 - 자동으로 최적 모드 선택"""
        try:
            # AgentFactory를 사용해 Agent 생성 (기본적으로 mcp_tools 모드로 설정)
            llm_config = self.config_manager.get_llm_config()
            
            # MCP 도구가 사용 가능한지 확인
            tools_available = self.mcp_tool_manager and self.mcp_tool_manager.get_tool_count() > 0
            
            if tools_available:
                # MCP 도구가 있으면 mcp_tools 모드로 설정
                llm_config["mode"] = "mcp_tools"
                print(f"{StyleColors.INFO}  → MCP 도구 감지, ReAct 모드 활성화{StyleColors.RESET_ALL}")
            else:
                # 없으면 basic 모드
                llm_config["mode"] = "basic"
                print(f"{StyleColors.INFO}  → 기본 LLM 모드 설정{StyleColors.RESET_ALL}")
            
            # 설정을 임시로 업데이트 (파일은 건드리지 않음)
            if "LLM" not in self.config_manager.config:
                self.config_manager.config.add_section("LLM")
            for key, value in llm_config.items():
                self.config_manager.config["LLM"][key] = str(value)
            
            self.llm_agent = AgentFactory.create_agent(self.config_manager, self.mcp_tool_manager)
            
        except Exception as e:
            logger.error(f"지능형 Agent 설정 실패: {e}")
            # 폴백으로 기본 Agent 생성
            self.llm_agent = AgentFactory.create_agent(self.config_manager, None)

    async def show_current_config(self) -> None:
        """현재 설정 표시"""
        try:
            if not self.config_manager:
                print(
                    f"{StyleColors.ERROR}❌ 설정 관리자가 초기화되지 않았습니다{StyleColors.RESET_ALL}"
                )
                return

            llm_config = self.config_manager.get_llm_config()
            model = llm_config.get("model", "unknown")
            mode = llm_config.get("mode", "basic")
            base_url = llm_config.get("base_url", "default")

            print(f"\n{StyleColors.INFO}📋 현재 설정:{StyleColors.RESET_ALL}")
            print(f"  모델: {StyleColors.SUCCESS}{model}{StyleColors.RESET_ALL}")
            print(f"  모드: {StyleColors.SUCCESS}{mode}{StyleColors.RESET_ALL}")
            print(f"  URL:  {StyleColors.METADATA}{base_url}{StyleColors.RESET_ALL}")

            if self.mcp_tool_manager:
                tool_count = self.mcp_tool_manager.get_tool_count()
                if tool_count > 0:
                    print(
                        f"  도구: {StyleColors.TOOL}{tool_count}개 MCP 도구 사용 가능{StyleColors.RESET_ALL}"
                    )
                else:
                    print(
                        f"  도구: {StyleColors.WARNING}MCP 도구 없음{StyleColors.RESET_ALL}"
                    )

        except Exception as e:
            print(f"{StyleColors.ERROR}설정 표시 실패: {e}{StyleColors.RESET_ALL}")

    async def diagnose_system(self) -> None:
        """시스템 진단"""
        print(f"\n{StyleColors.HEADER}🔍 시스템 진단 실행 중...{StyleColors.RESET_ALL}\n")

        # 1. 기본 구성 요소 체크
        print(f"{StyleColors.INFO}1. 기본 구성 요소 체크:{StyleColors.RESET_ALL}")

        components = [
            ("ConfigManager", self.config_manager),
            ("MCPManager", self.mcp_manager),
            ("MCPToolManager", self.mcp_tool_manager),
            ("LLMAgent", self.llm_agent),
            ("TaskManager", self.task_manager),
        ]

        for name, component in components:
            status = "✓" if component else "❌"
            color = StyleColors.SUCCESS if component else StyleColors.ERROR
            print(f"  {color}{status} {name}{StyleColors.RESET_ALL}")

        # 2. LLM 설정 검증
        print(f"\n{StyleColors.INFO}2. LLM 설정 검증:{StyleColors.RESET_ALL}")
        try:
            if not self.config_manager:
                print(
                    f"  {StyleColors.ERROR}❌ 설정 관리자가 초기화되지 않음{StyleColors.RESET_ALL}"
                )
                return

            llm_config = self.config_manager.get_llm_config()

            checks = [
                ("API 키", llm_config.get("api_key")),
                ("모델명", llm_config.get("model")),
                ("베이스 URL", llm_config.get("base_url")),
                ("모드 설정", llm_config.get("mode")),
            ]

            for name, value in checks:
                status = "✓" if value else "❌"
                color = StyleColors.SUCCESS if value else StyleColors.ERROR
                masked_value = "***" if "키" in name and value else str(value)
                print(f"  {color}{status} {name}: {masked_value}{StyleColors.RESET_ALL}")

        except Exception as e:
            print(f"  {StyleColors.ERROR}❌ LLM 설정 로드 실패: {e}{StyleColors.RESET_ALL}")

        # 3. MCP 도구 상태
        print(f"\n{StyleColors.INFO}3. MCP 도구 상태:{StyleColors.RESET_ALL}")
        if self.mcp_tool_manager:
            try:
                tools = await self.mcp_tool_manager.get_langchain_tools()
                print(
                    f"  {StyleColors.SUCCESS}✓ 총 {len(tools)}개 도구 사용 가능{StyleColors.RESET_ALL}"
                )

                if tools:
                    print(f"  {StyleColors.TOOL}주요 도구:{StyleColors.RESET_ALL}")
                    for tool in tools[:5]:  # 상위 5개만 표시
                        print(f"    • {tool.name}: {tool.description}")
                    if len(tools) > 5:
                        print(f"    • ... 및 {len(tools)-5}개 더")
                else:
                    print(
                        f"  {StyleColors.WARNING}⚠ 사용 가능한 도구가 없습니다{StyleColors.RESET_ALL}"
                    )

            except Exception as e:
                print(
                    f"  {StyleColors.ERROR}❌ MCP 도구 상태 확인 실패: {e}{StyleColors.RESET_ALL}"
                )
        else:
            print(
                f"  {StyleColors.ERROR}❌ MCP 도구 관리자가 초기화되지 않음{StyleColors.RESET_ALL}"
            )

        # 4. 간단한 테스트 수행
        print(f"\n{StyleColors.INFO}4. 기능 테스트:{StyleColors.RESET_ALL}")
        try:
            if not self.llm_agent:
                print(
                    f"  {StyleColors.ERROR}❌ LLM 에이전트가 초기화되지 않음{StyleColors.RESET_ALL}"
                )
                return

            test_result = await self.llm_agent.generate_response(
                "테스트 메시지입니다. 간단히 '테스트 성공'이라고 답해주세요."
            )

            if test_result.get("response"):
                print(f"  {StyleColors.SUCCESS}✓ LLM 응답 생성 테스트 통과{StyleColors.RESET_ALL}")
                used_tools = test_result.get("used_tools", [])
                if used_tools:
                    print(f"    사용된 도구: {', '.join(used_tools)}")
            else:
                print(f"  {StyleColors.WARNING}⚠ LLM 응답이 비어있음{StyleColors.RESET_ALL}")

        except Exception as e:
            print(f"  {StyleColors.ERROR}❌ 기능 테스트 실패: {e}{StyleColors.RESET_ALL}")

        print(f"\n{StyleColors.HEADER}진단 완료 ✓{StyleColors.RESET_ALL}")

    async def show_tools(self) -> None:
        """사용 가능한 MCP 도구 목록 표시"""
        print(f"\n{StyleColors.HEADER}🔧 사용 가능한 MCP 도구{StyleColors.RESET_ALL}\n")

        if not self.mcp_tool_manager:
            print(
                f"{StyleColors.ERROR}❌ MCP 도구 관리자가 초기화되지 않았습니다{StyleColors.RESET_ALL}"
            )
            return

        try:
            tools = await self.mcp_tool_manager.get_langchain_tools()

            if not tools:
                print(f"{StyleColors.WARNING}⚠ 사용 가능한 도구가 없습니다{StyleColors.RESET_ALL}")
                return

            print(
                f"{StyleColors.SUCCESS}총 {len(tools)}개 도구 사용 가능:{StyleColors.RESET_ALL}\n"
            )

            # 카테고리별로 분류
            categories = {
                "시간": ["time", "current_time", "clock"],
                "날씨": ["weather", "forecast", "climate"],
                "검색": ["search", "web", "duckduckgo", "google"],
                "파일": ["file", "read", "write", "filesystem"],
                "기타": [],
            }

            categorized_tools: dict[str, list] = {cat: [] for cat in categories}

            for tool in tools:
                assigned = False
                for category, keywords in categories.items():
                    if category != "기타" and any(kw in tool.name.lower() for kw in keywords):
                        categorized_tools[category].append(tool)
                        assigned = True
                        break
                if not assigned:
                    categorized_tools["기타"].append(tool)

            # 카테고리별 출력
            for category, tools_in_cat in categorized_tools.items():
                if tools_in_cat:
                    print(f"{StyleColors.INFO}{category} 도구:{StyleColors.RESET_ALL}")
                    for tool in tools_in_cat:
                        print(
                            f"  {StyleColors.TOOL}• {tool.name}{StyleColors.RESET_ALL}: {tool.description}"
                        )
                    print()

        except Exception as e:
            print(f"{StyleColors.ERROR}❌ 도구 목록 조회 실패: {e}{StyleColors.RESET_ALL}")

    async def process_command(self, user_input: str) -> bool:
        """명령어 처리 (True: 계속, False: 종료)"""
        user_input = user_input.strip()

        if user_input in ["/exit", "/quit"]:
            return False
        elif user_input == "/help":
            self.print_help()
        elif user_input == "/clear":
            if self.llm_agent:
                self.llm_agent.clear_conversation()
                print(
                    f"{StyleColors.SUCCESS}✓ 대화 히스토리가 초기화되었습니다{StyleColors.RESET_ALL}"
                )
            else:
                print(
                    f"{StyleColors.ERROR}❌ LLM 에이전트가 초기화되지 않았습니다{StyleColors.RESET_ALL}"
                )
        elif user_input == "/diagnose":
            await self.diagnose_system()
        elif user_input == "/config":
            await self.show_current_config()
        elif user_input == "/tools":
            await self.show_tools()
        elif user_input == "/stats":
            self.show_session_stats()
        elif user_input.startswith("/debug"):
            self.toggle_debug(user_input)
        elif user_input.startswith("/mode"):
            await self.change_mode(user_input)
        elif user_input.startswith("/test"):
            await self.test_tool(user_input)
        else:
            await self.process_ai_query(user_input)

        return True

    def show_session_stats(self) -> None:
        """세션 통계 표시"""
        duration = datetime.now() - self.session_start
        print(f"\n{StyleColors.INFO}📊 세션 통계:{StyleColors.RESET_ALL}")
        print(f"  세션 시간: {duration}")
        print(f"  처리한 질문: {self.query_count}개")
        if self.llm_agent:
            try:
                history = self.llm_agent.get_conversation_history()
                print(f"  대화 기록: {len(history)}개 메시지")
            except:
                pass

    def toggle_debug(self, command: str) -> None:
        """디버그 모드 토글"""
        parts = command.split()
        if len(parts) > 1:
            mode = parts[1].lower()
            if mode == "on":
                logging.getLogger().setLevel(logging.DEBUG)
                print(f"{StyleColors.SUCCESS}✓ 디버그 모드 활성화{StyleColors.RESET_ALL}")
            elif mode == "off":
                logging.getLogger().setLevel(logging.INFO)
                print(f"{StyleColors.SUCCESS}✓ 디버그 모드 비활성화{StyleColors.RESET_ALL}")
        else:
            current_level = logging.getLogger().level
            status = "활성화" if current_level == logging.DEBUG else "비활성화"
            print(f"{StyleColors.INFO}현재 디버그 모드: {status}{StyleColors.RESET_ALL}")

    async def change_mode(self, command: str) -> None:
        """LLM 모드 변경"""
        parts = command.split()
        if len(parts) < 2:
            print(f"{StyleColors.WARNING}사용법: /mode [auto|basic|mcp_tools|workflow]{StyleColors.RESET_ALL}")
            return

        mode = parts[1].lower()
        if mode not in ["auto", "basic", "mcp_tools", "workflow"]:
            print(f"{StyleColors.ERROR}지원하지 않는 모드: {mode}{StyleColors.RESET_ALL}")
            return

        try:
            if mode == "auto":
                await self.setup_intelligent_agent()
                print(f"{StyleColors.SUCCESS}✓ 자동 모드로 변경 (질문에 따라 최적 모드 선택){StyleColors.RESET_ALL}")
            else:
                # 수동 모드 설정
                if "LLM" not in self.config_manager.config:
                    self.config_manager.config.add_section("LLM")
                self.config_manager.config["LLM"]["mode"] = mode
                
                # Agent 재생성
                self.llm_agent = AgentFactory.create_agent(self.config_manager, self.mcp_tool_manager)
                print(f"{StyleColors.SUCCESS}✓ 모드를 '{mode}'로 변경했습니다{StyleColors.RESET_ALL}")
                
        except Exception as e:
            print(f"{StyleColors.ERROR}❌ 모드 변경 실패: {e}{StyleColors.RESET_ALL}")

    async def test_tool(self, command: str) -> None:
        """특정 도구 테스트"""
        parts = command.split()
        if len(parts) < 2:
            print(f"{StyleColors.WARNING}사용법: /test [tool_name]{StyleColors.RESET_ALL}")
            return

        tool_name = parts[1]

        try:
            if not self.mcp_tool_manager:
                print(f"{StyleColors.ERROR}❌ MCP 도구 관리자가 없습니다{StyleColors.RESET_ALL}")
                return

            # 간단한 도구 테스트
            print(f"{StyleColors.INFO}🧪 '{tool_name}' 도구 테스트 중...{StyleColors.RESET_ALL}")

            # 도구 찾기
            tools = await self.mcp_tool_manager.get_langchain_tools()
            target_tool = None
            for tool in tools:
                if tool_name.lower() in tool.name.lower():
                    target_tool = tool
                    break
            
            if not target_tool:
                print(f"{StyleColors.ERROR}❌ 도구 '{tool_name}'을 찾을 수 없습니다{StyleColors.RESET_ALL}")
                return
            
            # 기본 테스트 인수 준비
            if "weather" in tool_name.lower():
                test_args = {"city": "서울"}
            elif "time" in tool_name.lower():
                test_args = {}
            else:
                test_args = {"query": "test"}

            # 도구 실행
            result = await target_tool.ainvoke(test_args)

            print(f"{StyleColors.SUCCESS}✓ 테스트 결과:{StyleColors.RESET_ALL}")
            print(
                f"{StyleColors.METADATA}{str(result)[:500]}{'...' if len(str(result)) > 500 else ''}{StyleColors.RESET_ALL}"
            )

        except Exception as e:
            print(f"{StyleColors.ERROR}❌ 도구 테스트 실패: {e}{StyleColors.RESET_ALL}")

    def analyze_query_type(self, query: str) -> str:
        """질문 유형 분석하여 최적 모드 결정"""
        query_lower = query.lower()
        
        # 워크플로우가 필요한 복합 작업 키워드
        workflow_keywords = [
            "계획", "전략", "분석", "설계", "프로젝트", "단계별", "로드맵", 
            "체계적", "종합적", "방법론", "프로세스", "framework", "plan", 
            "strategy", "analysis", "design", "step by step"
        ]
        
        # MCP 도구가 필요한 키워드
        tool_keywords = [
            "날씨", "시간", "검색", "찾아", "알아봐", "조사", "파일", "저장",
            "weather", "time", "search", "find", "file", "save", "web", "internet"
        ]
        
        # 복합 작업인지 확인
        if any(keyword in query_lower for keyword in workflow_keywords):
            return "workflow"
        
        # 도구가 필요한 작업인지 확인
        if any(keyword in query_lower for keyword in tool_keywords):
            return "mcp_tools"
        
        # 기본적으로는 basic 모드
        return "basic"

    async def process_ai_query(self, query: str) -> None:
        """AI 질문 처리 - 자동으로 최적 모드 선택"""
        self.query_count += 1
        start_time = time.time()

        # 질문 유형 분석하여 최적 모드 결정
        suggested_mode = self.analyze_query_type(query)
        current_mode = self.config_manager.get_llm_config().get("mode", "basic")
        
        # 자동 모드이거나 모드 변경이 필요한 경우
        if current_mode == "auto" or suggested_mode != current_mode:
            try:
                # 임시로 모드 변경
                if "LLM" not in self.config_manager.config:
                    self.config_manager.config.add_section("LLM")
                
                old_mode = self.config_manager.config["LLM"].get("mode", "basic")
                self.config_manager.config["LLM"]["mode"] = suggested_mode
                
                # 모드가 실제로 변경된 경우만 Agent 재생성
                if old_mode != suggested_mode:
                    print(f"{StyleColors.INFO}🧠 질문 분석: {suggested_mode} 모드로 자동 전환{StyleColors.RESET_ALL}")
                    self.llm_agent = AgentFactory.create_agent(self.config_manager, self.mcp_tool_manager)
                    
            except Exception as e:
                logger.warning(f"자동 모드 전환 실패: {e}")

        print(
            f"\n{StyleColors.AI_RESPONSE}🤖 Assistant:{StyleColors.RESET_ALL} ", end="", flush=True
        )

        try:
            if not self.llm_agent:
                print(
                    f"\n{StyleColors.ERROR}❌ LLM 에이전트가 초기화되지 않았습니다{StyleColors.RESET_ALL}"
                )
                return

            # 스트리밍 콜백
            def streaming_callback(chunk: str) -> None:
                print(chunk, end="", flush=True)

            # AI 응답 생성
            result = await self.llm_agent.generate_response(query, streaming_callback)

            print()  # 새 줄

            # 메타데이터 표시
            elapsed = time.time() - start_time
            used_tools = result.get("used_tools", [])
            reasoning = result.get("reasoning", "")
            workflow = result.get("workflow", "")

            if used_tools or reasoning or workflow:
                print(f"\n{StyleColors.METADATA}📋 메타데이터:{StyleColors.RESET_ALL}")
                if workflow:
                    print(f"  워크플로우: {workflow}")
                if used_tools:
                    print(f"  사용된 도구: {', '.join(used_tools)}")
                if reasoning and reasoning.strip():
                    print(f"  추론 과정: {reasoning[:100]}...")
                print(f"  응답 시간: {elapsed:.2f}초")
                print(f"  모드: {suggested_mode}")

        except Exception as e:
            print(f"\n{StyleColors.ERROR}❌ 오류 발생: {e}{StyleColors.RESET_ALL}")
            logger.error(f"AI 질문 처리 실패: {e}")

    async def interactive_mode(self) -> None:
        """대화형 모드"""
        self.print_banner()

        if not await self.initialize():
            print(f"{StyleColors.ERROR}❌ 초기화 실패로 종료합니다{StyleColors.RESET_ALL}")
            return

        print(
            f"\n{StyleColors.SUCCESS}✓ 초기화 완료! 질문을 입력하거나 명령어를 사용하세요.{StyleColors.RESET_ALL}"
        )
        print(
            f"{StyleColors.INFO}💡 자동 모드: 질문 내용에 따라 최적의 처리 방식을 자동 선택합니다{StyleColors.RESET_ALL}"
        )

        while True:
            try:
                # 사용자 입력
                user_input = input(f"\n{StyleColors.PROMPT}🧑 You:{StyleColors.RESET_ALL} ").strip()

                if not user_input:
                    continue

                # 명령어 처리
                should_continue = await self.process_command(user_input)
                if not should_continue:
                    break

            except KeyboardInterrupt:
                print(
                    f"\n\n{StyleColors.WARNING}Ctrl+C 감지. 종료하려면 '/exit'를 입력하세요.{StyleColors.RESET_ALL}"
                )
            except Exception as e:
                print(f"\n{StyleColors.ERROR}❌ 예상치 못한 오류: {e}{StyleColors.RESET_ALL}")
                logger.error(f"대화형 모드 오류: {e}")

        # 정리
        print(f"\n{StyleColors.SUCCESS}👋 세션을 종료합니다. 감사합니다!{StyleColors.RESET_ALL}")
        if self.llm_agent:
            await self.llm_agent.cleanup()
        if self.mcp_tool_manager:
            await self.mcp_tool_manager.cleanup()

    async def single_query_mode(self, query: str, mode: Optional[str] = None) -> None:
        """단일 질문 모드"""
        print(f"{StyleColors.SYSTEM}🚀 DSPilot CLI - 단일 질문 모드{StyleColors.RESET_ALL}\n")

        if not await self.initialize():
            print(f"{StyleColors.ERROR}❌ 초기화 실패{StyleColors.RESET_ALL}")
            return

        if mode:
            # 특정 모드 설정
            if "LLM" not in self.config_manager.config:
                self.config_manager.config.add_section("LLM")
            self.config_manager.config["LLM"]["mode"] = mode
            self.llm_agent = AgentFactory.create_agent(self.config_manager, self.mcp_tool_manager)

        print(f"{StyleColors.PROMPT}질문: {query}{StyleColors.RESET_ALL}")
        await self.process_ai_query(query)

        # 정리
        if self.llm_agent:
            await self.llm_agent.cleanup()
        if self.mcp_tool_manager:
            await self.mcp_tool_manager.cleanup()


async def main() -> int:
    """메인 진입점"""
    parser = argparse.ArgumentParser(
        description="DSPilot CLI - 고급 LLM + MCP + ReAct Agent CLI 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  %(prog)s                                    # 대화형 모드 (자동 모드 선택)
  %(prog)s "오늘 날씨 어때?"                   # 단일 질문 (자동 도구 사용)
  %(prog)s --mode mcp_tools "Python이란?"     # 특정 모드로 질문
  %(prog)s --diagnose                         # 시스템 진단
  %(prog)s --tools                            # 도구 목록
        """,
    )

    # 위치 인수 (선택적 질문)
    parser.add_argument("query", nargs="?", help="처리할 질문 (생략시 대화형 모드)")

    # 옵션 인수
    parser.add_argument("--mode", "-m", choices=["auto", "basic", "mcp_tools", "workflow"], help="LLM 모드 선택")
    parser.add_argument("--diagnose", "-d", action="store_true", help="시스템 진단 후 종료")
    parser.add_argument(
        "--tools", "-t", action="store_true", help="사용 가능한 도구 목록 표시 후 종료"
    )
    parser.add_argument("--config", "-c", action="store_true", help="현재 설정 표시 후 종료")
    parser.add_argument("--debug", action="store_true", help="디버그 모드 활성화")

    args = parser.parse_args()

    # 디버그 모드 설정
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        print(f"{StyleColors.INFO}🐛 디버그 모드 활성화{StyleColors.RESET_ALL}")

    cli = DSPilotCLI()

    try:
        # 진단 모드
        if args.diagnose:
            print(f"{StyleColors.HEADER}🔍 DSPilot 시스템 진단{StyleColors.RESET_ALL}")
            await cli.initialize()
            await cli.diagnose_system()
            return 0

        # 도구 목록 모드
        if args.tools:
            print(f"{StyleColors.HEADER}🔧 DSPilot MCP 도구 목록{StyleColors.RESET_ALL}")
            await cli.initialize()
            await cli.show_tools()
            return 0

        # 설정 표시 모드
        if args.config:
            print(f"{StyleColors.HEADER}⚙️ DSPilot 현재 설정{StyleColors.RESET_ALL}")
            await cli.initialize()
            await cli.show_current_config()
            return 0

        # 단일 질문 모드
        if args.query:
            await cli.single_query_mode(args.query, args.mode)
        else:
            # 대화형 모드
            await cli.interactive_mode()

    except KeyboardInterrupt:
        print(f"\n{StyleColors.WARNING}🛑 사용자에 의해 중단되었습니다{StyleColors.RESET_ALL}")
    except Exception as e:
        print(f"{StyleColors.ERROR}❌ 예상치 못한 오류: {e}{StyleColors.RESET_ALL}")
        logger.error(f"메인 실행 오류: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
