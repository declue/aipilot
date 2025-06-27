#!/usr/bin/env python3
"""
DSPilot CLI 시스템 관리 모듈
"""

import logging
import os
from typing import Any, List, Optional, Tuple

from dspilot_cli.constants import Messages
from dspilot_cli.output_manager import OutputManager
from dspilot_core.config.config_manager import ConfigManager
from dspilot_core.llm.agents.agent_factory import AgentFactory
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_manager import MCPManager
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager
from dspilot_core.util.logger import setup_logger


class SystemManager:
    """시스템 초기화 및 관리를 담당하는 클래스"""

    def __init__(self, output_manager: OutputManager) -> None:
        """
        시스템 관리자 초기화

        Args:
            output_manager: 출력 관리자
        """
        self.output_manager = output_manager
        self.logger = setup_logger(
            "dspilot_cli") or logging.getLogger("dspilot_cli")

        # 시스템 구성요소들
        self.config_manager: Optional[ConfigManager] = None
        self.mcp_manager: Optional[MCPManager] = None
        self.mcp_tool_manager: Optional[MCPToolManager] = None
        self.llm_agent: Optional[BaseAgent] = None

    def _setup_mcp_logging(self) -> None:
        """MCP 관련 로깅 제어 설정"""
        # 루트 로거의 핸들러를 조작하여 MCP 관련 로그 필터링
        root_logger = logging.getLogger()
        
        # MCP 관련 로그를 필터링하는 커스텀 필터 클래스
        class MCPLogFilter(logging.Filter):
            def filter(self, record):
                # GitHub MCP 서버 관련 로그 차단
                if "GitHub MCP Server" in record.getMessage():
                    return False
                if "shutting down server" in record.getMessage():
                    return False
                if "Processing request of type" in record.getMessage():
                    return False
                # DuckDuckGo MCP 서버 관련 로그 차단  
                if "DuckDuckGo MCP 서버 프로세스 시작" in record.getMessage():
                    return False
                if "Python Executable:" in record.getMessage():
                    return False
                if "sys.path:" in record.getMessage():
                    return False
                # stdioserverError 관련 로그 차단
                if "stdioserverError" in record.getMessage():
                    return False
                return True
        
        # 모든 핸들러에 필터 추가
        mcp_filter = MCPLogFilter()
        for handler in root_logger.handlers:
            handler.addFilter(mcp_filter)
            
        # 특정 MCP 로거들도 레벨 조정
        mcp_loggers = [
            "mcp.server.lowlevel.server",
            "mcp.server.fastmcp", 
            "fastmcp",
            "__main__",
            "rich.logging"  # Rich 로깅도 포함
        ]
        
        for logger_name in mcp_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.ERROR)  # ERROR 이상만 출력
            logger.addFilter(mcp_filter)
            
        # 환경 변수도 설정
        os.environ.setdefault("DUCKDUCKGO_LOG_LEVEL", "ERROR")
        os.environ.setdefault("CODER_MCP_VERBOSE", "false")
        os.environ.setdefault("FILE_MCP_VERBOSE", "false")

    async def initialize(self) -> Tuple[bool, str]:
        """
        시스템 구성요소들을 초기화합니다.

        Returns:
            Tuple[bool, str]: (성공 여부, 상태 메시지)
        """
        try:
            # MCP 관련 로깅 제어
            self._setup_mcp_logging()

            # 1. 설정 매니저 초기화
            self.output_manager.print_info("설정 매니저 초기화 중...")
            self.config_manager = ConfigManager()
            self.config_manager.load_config()
            self.output_manager.print_success("설정 관리자 초기화 완료")

            # 2. MCPManager 초기화
            if not await self._initialize_mcp_manager():
                return False, "MCPManager 초기화 실패"

            # 3. MCPToolManager 초기화
            if not await self._initialize_mcp_tool_manager():
                return False, "MCPToolManager 초기화 실패"

            # 4. Agent 초기화
            if not await self._initialize_llm_agent():
                return False, "LLM Agent 초기화 실패"

            self.output_manager.log_if_debug("시스템 초기화 완료")
            return True, "시스템 초기화 완료"

        except Exception as e:
            self.output_manager.log_if_debug(f"초기화 실패: {e}", "error")
            self.output_manager.print_error(
                f"{Messages.INITIALIZATION_FAILED}: {e}")
            return False, f"초기화 실패: {e}"

    async def cleanup(self) -> None:
        """리소스 정리"""
        try:
            self.output_manager.print_system(Messages.CLEANUP_STARTED)

            # 각 구성요소 정리 (역순으로)
            if self.llm_agent:
                await self.llm_agent.cleanup()

            if self.mcp_tool_manager:
                await self.mcp_tool_manager.cleanup()

            if self.mcp_manager:
                await self.mcp_manager.cleanup()

            self.output_manager.print_success(Messages.CLEANUP_COMPLETED)

        except Exception as e:
            self.output_manager.log_if_debug(f"정리 중 오류: {e}", "error")

    def get_system_status(self) -> List[Tuple[str, Any]]:
        """
        시스템 상태 정보 반환

        Returns:
            (구성요소명, 구성요소) 튜플 리스트
        """
        return [
            ("설정 관리자", self.config_manager),
            ("MCP 관리자", self.mcp_manager),
            ("MCP 도구 관리자", self.mcp_tool_manager),
            ("Agent", self.llm_agent),
        ]

    async def get_tools_list(self) -> List[Any]:
        """
        사용 가능한 도구 목록 반환

        Returns:
            도구 목록
        """
        tools = []
        if self.mcp_tool_manager and hasattr(self.mcp_tool_manager, 'tools'):
            tools = getattr(self.mcp_tool_manager, 'tools', [])
        return tools

    def set_interaction_mode(self, interactive: bool) -> None:
        """
        상호작용 모드 설정

        Args:
            interactive: 상호작용 모드 여부
        """
        if self.llm_agent:
            try:
                # 동적으로 메서드 호출 시도
                if hasattr(self.llm_agent, 'set_interaction_mode'):
                    method = getattr(self.llm_agent, 'set_interaction_mode')
                    method(interactive)  # type: ignore
            except (AttributeError, TypeError):
                # 메서드가 없거나 호출 실패 시 조용히 넘어감
                pass

    async def _initialize_mcp_manager(self) -> bool:
        """MCPManager 초기화"""
        try:
            if not self.config_manager:
                raise ValueError("ConfigManager가 초기화되지 않음")

            self.mcp_manager = MCPManager(self.config_manager)
            self.output_manager.print_success("✓ MCP 관리자 초기화 완료")
            return True
        except Exception as e:
            self.output_manager.print_error(f"MCP 관리자 초기화 실패: {e}")
            return False

    async def _initialize_mcp_tool_manager(self) -> bool:
        """MCPToolManager 초기화"""
        try:
            if not self.config_manager or not self.mcp_manager:
                raise ValueError("ConfigManager 또는 MCPManager가 초기화되지 않음")

            self.mcp_tool_manager = MCPToolManager(
                self.mcp_manager, self.config_manager)
            init_success = await self.mcp_tool_manager.initialize()

            if init_success:
                self.output_manager.print_success("✓ MCP 도구 관리자 초기화 완료")
            else:
                self.output_manager.print_warning(
                    "⚠ MCP 도구 초기화 실패 (기본 모드만 사용 가능)")

            return True  # 도구 초기화 실패해도 계속 진행
        except Exception as e:
            self.output_manager.print_error(f"MCP 도구 관리자 초기화 실패: {e}")
            return False

    async def _initialize_llm_agent(self) -> bool:
        """LLM Agent 초기화"""
        try:
            if not self.config_manager or not self.mcp_tool_manager:
                raise ValueError("ConfigManager 또는 MCPToolManager가 초기화되지 않음")

            self.output_manager.log_if_debug("Agent 생성 중...")
            self.llm_agent = AgentFactory.create_agent(
                self.config_manager, self.mcp_tool_manager)
            self.output_manager.print_success("✓ Agent 초기화 완료")
            return True
        except Exception as e:
            self.output_manager.print_error(f"Agent 초기화 실패: {e}")
            return False

    def is_initialized(self) -> bool:
        """
        시스템이 완전히 초기화되었는지 확인

        Returns:
            초기화 완료 여부
        """
        return all([
            self.config_manager is not None,
            self.mcp_manager is not None,
            self.mcp_tool_manager is not None,
            self.llm_agent is not None
        ])

    def get_config_manager(self) -> Optional[ConfigManager]:
        """ConfigManager 반환"""
        return self.config_manager

    def get_mcp_manager(self) -> Optional[MCPManager]:
        """MCPManager 반환"""
        return self.mcp_manager

    def get_mcp_tool_manager(self) -> Optional[MCPToolManager]:
        """MCPToolManager 반환"""
        return self.mcp_tool_manager

    def get_llm_agent(self) -> Optional[BaseAgent]:
        """LLM Agent 반환"""
        return self.llm_agent
