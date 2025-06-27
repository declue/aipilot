#!/usr/bin/env python3
"""
DSPilot CLI 대화 히스토리 관리 모듈
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from dspilot_cli.constants import ENHANCED_PROMPT_TEMPLATE, ConversationEntry, Defaults


class ConversationManager:
    """대화 히스토리 관리를 담당하는 클래스"""

    def __init__(self, max_context_turns: int = Defaults.MAX_CONTEXT_TURNS) -> None:
        """
        대화 관리자 초기화

        Args:
            max_context_turns: 컨텍스트로 사용할 최대 대화 턴 수
        """
        self.conversation_history: List[ConversationEntry] = []
        self.pending_actions: List[str] = []
        self.max_context_turns = max_context_turns

    def add_to_history(self,
                       role: str,
                       content: str,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        대화 히스토리에 메시지 추가

        Args:
            role: 역할 (user, assistant)
            content: 메시지 내용
            metadata: 추가 메타데이터
        """
        entry = ConversationEntry(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        self.conversation_history.append(entry)

    def get_recent_context(self, max_turns: Optional[int] = None) -> str:
        """
        최근 대화 컨텍스트를 문자열로 반환

        Args:
            max_turns: 최대 턴 수 (지정하지 않으면 기본값 사용)

        Returns:
            컨텍스트 문자열
        """
        if not self.conversation_history:
            return ""

        turns = max_turns or self.max_context_turns
        # 최근 N턴의 대화만 가져오기
        recent_messages = (
            self.conversation_history[-turns*2:]
            if len(self.conversation_history) > turns*2
            else self.conversation_history
        )

        context_parts = []
        for entry in recent_messages:
            role_prefix = "👤 User" if entry.role == "user" else "🤖 Assistant"
            context_parts.append(f"{role_prefix}: {entry.content}")

            # 도구 사용 정보가 있으면 추가
            if entry.metadata.get("used_tools"):
                tools = ", ".join(str(tool)
                                  for tool in entry.metadata["used_tools"])
                context_parts.append(f"   [사용된 도구: {tools}]")

        return "\n".join(context_parts)

    def build_enhanced_prompt(self, user_input: str) -> str:
        """
        이전 대화 맥락을 포함한 향상된 프롬프트 생성

        Args:
            user_input: 사용자 입력

        Returns:
            향상된 프롬프트
        """
        context = self.get_recent_context()

        if not context:
            return user_input

        # 보류 중인 작업이 있으면 포함
        pending_context = ""
        if self.pending_actions:
            pending_context = "\n\n[보류 중인 작업들]:\n" + \
                "\n".join(f"- {action}" for action in self.pending_actions)

        return ENHANCED_PROMPT_TEMPLATE.format(
            context=context,
            pending_context=pending_context,
            user_input=user_input
        )

    def extract_pending_actions(self, response_data: Dict[str, Any]) -> None:
        """
        응답에서 보류 중인 작업들을 추출하여 저장

        Args:
            response_data: 응답 데이터
        """
        response = response_data.get("response", "")

        # 간단한 패턴으로 제안된 변경사항 감지 (범용적 접근)
        keywords = ["수정하겠습니다", "변경하겠습니다", "적용하겠습니다", "수정할까요", "변경할까요"]
        if any(keyword in response.lower() for keyword in keywords):
            # 코드 블록이나 파일 경로가 포함된 경우
            extensions = [".py", ".js", ".ts", ".java", ".cpp", ".txt"]
            if "```" in response or any(ext in response for ext in extensions):
                self.pending_actions.append("파일 수정/생성 작업")

        # 최대 N개의 보류 작업만 유지
        if len(self.pending_actions) > Defaults.MAX_PENDING_ACTIONS:
            self.pending_actions = self.pending_actions[-Defaults.MAX_PENDING_ACTIONS:]

    def clear_pending_actions(self) -> None:
        """보류 중인 작업들 초기화"""
        self.pending_actions.clear()

    def clear_conversation(self) -> None:
        """대화 히스토리 초기화"""
        self.conversation_history.clear()
        self.clear_pending_actions()

    def get_conversation_count(self) -> int:
        """대화 메시지 개수 반환"""
        return len(self.conversation_history)

    def get_pending_actions(self) -> List[str]:
        """보류 중인 작업 목록 반환"""
        return self.pending_actions.copy()

    def has_pending_actions(self) -> bool:
        """보류 중인 작업이 있는지 확인"""
        return bool(self.pending_actions)
