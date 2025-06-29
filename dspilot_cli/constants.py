#!/usr/bin/env python3
"""
DSPilot CLI 상수 및 타입 정의
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from colorama import Fore, Style


class UserChoiceType(Enum):
    """사용자 선택 타입"""
    PROCEED = "proceed"
    SKIP = "skip"
    MODIFY = "modify"
    CANCEL = "cancel"


class LogLevel(Enum):
    """로그 레벨"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


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


@dataclass
class ConversationEntry:
    """대화 히스토리 엔트리"""
    role: str
    content: str
    timestamp: str
    metadata: Dict[str, Any]


@dataclass
class ExecutionStep:
    """실행 단계 정의"""
    step: int
    description: str
    tool_name: str
    arguments: Dict[str, Any]
    confirm_message: str


@dataclass
class ExecutionPlan:
    """실행 계획 정의"""
    description: str
    steps: List[ExecutionStep]


# CLI 명령어 상수
class Commands:
    """CLI 명령어 상수"""
    HELP = "help"
    STATUS = "status"
    CLEAR = "clear"
    TOOLS = "tools"
    EXIT = "exit"
    QUIT = "quit"


# 시스템 메시지 상수
class Messages:
    """시스템 메시지 상수"""
    INITIALIZING = "🔧 시스템 초기화 중..."
    INITIALIZATION_FAILED = "❌ 초기화 실패"
    AGENT_NOT_INITIALIZED = "Agent가 초기화되지 않았습니다."
    ANALYZING = "🤖 분석 중..."
    TASK_COMPLETED = "✅ 작업 완료"
    NO_PENDING_ACTIONS = "✅ 보류 중인 작업 없음"
    CLEANUP_STARTED = "🧹 리소스 정리 중..."
    CLEANUP_COMPLETED = "✓ 정리 완료"
    USER_INTERRUPTED = "👋 사용자 종료 요청"
    CONVERSATION_CLEARED = "✓ 대화 기록이 초기화되었습니다."


# 기본 설정값
class Defaults:
    """기본 설정값"""
    MAX_CONTEXT_TURNS = 5
    MAX_PENDING_ACTIONS = 3
    RESULT_SUMMARY_MAX_LENGTH = 200
    PROMPT_PREVIEW_LENGTH = 100
    MAX_ITERATIONS = 30
    MAX_STEP_RETRIES = 2
    VALIDATE_MODE = "auto"  # auto|off|strict

    # 1회 프롬프트 토큰 예산 (시스템/유저/컨텍스트 포함)
    MAX_PROMPT_TOKENS = 1000000


# 프롬프트 이름 상수 (파일 기반으로 변경)
class PromptNames:
    """프롬프트 파일 이름 상수"""
    ANALYSIS = "analysis_prompts"
    FINAL_ANALYSIS = "final_analysis_prompts"
    ENHANCED = "enhanced_prompts"
