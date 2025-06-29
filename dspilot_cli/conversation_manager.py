#!/usr/bin/env python3
"""
DSPilot CLI 대화 히스토리 관리 모듈
=================================

본 모듈은 CLI 세션 동안 발생하는 **대화 메시지**와 **보류 중 작업(pending actions)**을
관리해 LLM 프롬프트에 필요한 컨텍스트를 제공합니다.

기능 요약
---------
1. History 관리
   • add_to_history()  : 메시지와 메타데이터 저장
   • get_recent_context(): 최근 N턴만 압축하여 문자열 컨텍스트 반환
2. Prompt 빌더
   • build_enhanced_prompt(): 대화 맥락 + 보류 작업 + 사용자 입력을 결합
3. Action 추출
   • extract_pending_actions(): LLM 응답을 스캔하여 파일 수정 제안 등을 보류 목록에 추가

아키텍처
--------
```mermaid
flowchart LR
    A[ConversationManager] --> B((History))
    A --> C((Pending Actions))
    subgraph Prompt Builder
        B --> D[Recent Context]
        C --> D
    end
```

시퀀스 다이어그램 (프롬프트 생성)
--------------------------------
```mermaid
sequenceDiagram
    participant User
    participant CM as ConversationManager
    participant Agent
    User->>CM: add_to_history(role="user")
    CM-->>Agent: build_enhanced_prompt()
    Agent-->>CM: response
    CM->>CM: extract_pending_actions()
```

사용 예시
---------
```python
cm = ConversationManager(max_context_turns=6)
cm.add_to_history("user", "안녕?")
cm.add_to_history("assistant", "반가워!")
print(cm.build_enhanced_prompt("오늘 날씨 알려줘"))
```

테스트 전략
-----------
- `pytest.mark.parametrize` 로 다양한 history 길이를 검증
- `freezegun.freeze_time` 으로 timestamp 일관성 확보
- `extract_pending_actions()` 는 mock 응답을 주입해 키워드·확장자 탐지 로직을 테스트
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import dspilot_core.instructions.prompt_manager as prompt_manager
from dspilot_cli.constants import ConversationEntry, Defaults, PromptNames

# type: ignore  # pylint: disable=import-error
from dspilot_cli.summary_utils import compress_text

# ---------------------------------------------------------------------------
# 토큰 카운터 초기화 (tiktoken 우선, 없으면 whitespace 기반 fallback)
# ---------------------------------------------------------------------------
try:
    import tiktoken

    _DEFAULT_ENCODING = "cl100k_base"  # gpt-3.5/4 호환
    _ENCODER = tiktoken.get_encoding(_DEFAULT_ENCODING)

    def _count_tokens(text: str) -> int:  # pylint: disable=missing-docstring
        return len(_ENCODER.encode(text))

except ModuleNotFoundError:  # pragma: no cover – CI에 tiktoken이 없을 때 대비

    def _count_tokens(text: str) -> int:  # type: ignore
        """토크나이저가 없을 경우 공백 단위로 근사 계산"""

        return len(text.split())


class ConversationManager:
    """대화 히스토리 관리를 담당하는 클래스

    SOLID 원칙 적용:
    - Single Responsibility: 대화 히스토리 관리만 담당
    - Open/Closed: 새로운 대화 관리 전략 추가 시 기존 코드 수정 없이 확장 가능
    - Dependency Inversion: 프롬프트 관리자에 의존하여 템플릿을 동적으로 로드
    """

    def __init__(self, max_context_turns: int = Defaults.MAX_CONTEXT_TURNS) -> None:
        """
        대화 관리자 초기화

        Args:
            max_context_turns: 컨텍스트로 사용할 최대 대화 턴 수
        """
        self.conversation_history: List[ConversationEntry] = []
        self.pending_actions: List[str] = []
        self.max_context_turns = max_context_turns

        # 토큰 예산 (전체 프롬프트 기준). 시스템/지시문 여유로 10% 버퍼 확보
        self.max_prompt_tokens = Defaults.MAX_PROMPT_TOKENS
        self._context_token_budget = int(self.max_prompt_tokens * 0.9)

        # 프롬프트 관리자 주입 (모듈 방식으로 불러와 테스트 중 모킹 가능)
        self.prompt_manager = prompt_manager.get_default_prompt_manager()

    # ------------------------------------------------------------------
    # 내부 유틸 함수들
    # ------------------------------------------------------------------

    @staticmethod
    def _role_prefix(role: str) -> str:
        """역할에 따른 프리픽스 이모티콘"""

        return "👤 User" if role == "user" else "🤖 Assistant"

    def _format_entry(self, entry: ConversationEntry) -> str:
        """ConversationEntry 를 프롬프트용 문자열로 변환"""

        role_prefix = self._role_prefix(entry.role)
        part = f"{role_prefix}: {entry.content}"

        if entry.metadata.get("used_tools"):
            tools = ", ".join(str(tool)
                              for tool in entry.metadata["used_tools"])
            part += f"\n   [사용된 도구: {tools}]"
        return part

    def _select_messages_within_budget(self, budget_tokens: int) -> Tuple[List[str], List[ConversationEntry]]:
        """토큰 예산 내에서 가장 최근 메시지들을 선택

        반환된 리스트는 *시간순(과거→현재)* 입니다.
        """

        selected_lines: List[str] = []
        selected_entries: List[ConversationEntry] = []

        current_tokens = 0

        # 최신 메시지부터 거꾸로 추가 후, 최종적으로 reverse 하여 시간순 맞춤
        for entry in reversed(self.conversation_history):
            formatted = self._format_entry(entry)
            entry_tokens = _count_tokens(formatted)

            if current_tokens + entry_tokens > budget_tokens:
                break

            selected_lines.append(formatted)
            selected_entries.append(entry)
            current_tokens += entry_tokens

        selected_lines.reverse()
        selected_entries.reverse()
        return selected_lines, selected_entries

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

        # 1) 토큰 예산으로 우선 필터링 -----------------------------------
        selected_lines, _ = self._select_messages_within_budget(
            self._context_token_budget)

        # 2) 추가로 턴 수 제한 적용 (예: 최근 5턴 유지). 토큰보다 강한 제약 아님.
        turns = max_turns or self.max_context_turns
        if turns > 0:
            max_messages = turns * 2  # user+assistant 한 턴 = 2 메시지
            if len(selected_lines) > max_messages:
                selected_lines = selected_lines[-max_messages:]

        return "\n".join(selected_lines)

    def build_enhanced_prompt(self, user_input: str) -> str:
        """
        이전 대화 맥락을 포함한 향상된 프롬프트 생성

        Args:
            user_input: 사용자 입력

        Returns:
            향상된 프롬프트
        """
        context = self.get_recent_context()

        # 보류 중인 작업이 있으면 포함
        pending_context = ""
        if self.pending_actions:
            pending_context = "\n\n[보류 중인 작업들]:\n" + \
                              "\n".join(
                                  f"- {action}" for action in self.pending_actions)

        if not context:
            # 컨텍스트 없으면 단순 프롬프트
            return f"{pending_context}\n\n{user_input}" if pending_context else user_input

        # ENHANCED 프롬프트 구성 (파일에서 로드)
        try:
            enhanced_prompt = self.prompt_manager.get_formatted_prompt(
                PromptNames.ENHANCED,
                context=context,
                pending_context=pending_context,
                user_input=user_input
            )

            if enhanced_prompt is None:
                # 프롬프트 로드 실패 시 기본 형태
                enhanced_prompt = f"이전 대화 맥락:\n{context}\n\n{pending_context}\n\n현재 사용자 요청: {user_input}"

        except Exception:
            # 포맷팅 실패 시 기본 형태
            enhanced_prompt = f"이전 대화 맥락:\n{context}\n\n{pending_context}\n\n현재 사용자 요청: {user_input}"

        # ------------------------------------------------------------------
        # 생성된 프롬프트가 토큰 예산을 초과하면 요약(compaction) 수행
        # ------------------------------------------------------------------
        total_tokens = _count_tokens(enhanced_prompt)
        if total_tokens > self.max_prompt_tokens:
            # 초과량만큼 오래된 메시지 제거 후 재생성
            # 간단 버전: 컨텍스트에서 가장 오래된 두 줄 제거 반복
            context_lines = context.split("\n")
            while context_lines and total_tokens > self.max_prompt_tokens:
                # 1) 오래된 메시지 제거 후 재평가
                context_lines = context_lines[2:]
                context = "\n".join(context_lines)

                enhanced_prompt = self.prompt_manager.get_formatted_prompt(
                    PromptNames.ENHANCED,
                    context=context,
                    pending_context=pending_context,
                    user_input=user_input
                ) or f"이전 대화 맥락:\n{context}\n\n{pending_context}\n\n현재 사용자 요청: {user_input}"

                # Ensure enhanced_prompt is a string before counting tokens
                prompt_text = str(
                    enhanced_prompt) if enhanced_prompt is not None else ""
                total_tokens = _count_tokens(prompt_text)

            # 2) 그래도 초과하면 요약 압축 시도
            if total_tokens > self.max_prompt_tokens and context_lines:
                compressed_context = compress_text("\n".join(context_lines))
                enhanced_prompt = self.prompt_manager.get_formatted_prompt(
                    PromptNames.ENHANCED,
                    context=compressed_context,
                    pending_context=pending_context,
                    user_input=user_input
                ) or f"이전 대화 맥락(요약):\n{compressed_context}\n\n{pending_context}\n\n현재 사용자 요청: {user_input}"

        return enhanced_prompt

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
