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


# 분석 프롬프트 템플릿
ANALYSIS_PROMPT_TEMPLATE = """다음 사용자 요청을 분석하여 실행 계획을 수립해주세요.

사용자 요청: {user_message}

사용 가능한 도구들:
{tools_desc}

도구 사용이 필요한 경우 실행 계획을 수립하세요. 그렇지 않으면 null을 반환하세요.

**응답 형식 (JSON):**
{{
    "need_tools": true/false,
    "plan": {{
        "description": "실행 계획 설명",
        "steps": [
            {{
                "step": 1,
                "description": "단계 설명",
                "tool_name": "도구명",
                "arguments": {{"arg": "value"}},
                "confirm_message": "사용자에게 표시할 확인 메시지"
            }}
        ]
    }}
}}

반드시 JSON 형식으로만 응답하세요."""

FINAL_ANALYSIS_PROMPT_TEMPLATE = """다음은 사용자 요청에 대한 도구 실행 결과입니다.

원래 요청: {original_prompt}

실행 결과:
{results_summary}

위 결과를 바탕으로 사용자의 요청에 대한 완전하고 유용한 최종 답변을 제공해주세요."""

ENHANCED_PROMPT_TEMPLATE = """이전 대화 맥락:
{context}

{pending_context}

현재 사용자 요청: {user_input}

위의 대화 맥락을 고려하여 응답해주세요. 특히:
1. 이전에 제안한 작업이나 변경사항을 사용자가 확인/적용을 요청하는 경우, 해당 내용을 바탕으로 즉시 실행해주세요.
2. 복합적인 요청의 경우 단계별로 계획을 수립하고 순차적으로 실행해주세요.
3. 데이터 수집, 처리, 저장이 모두 필요한 경우 각 단계를 완료한 후 다음 단계로 진행해주세요.""" 