"""
대화 관리 서비스
"""

import logging
from typing import Any, Dict, List

from application.llm.models.conversation_message import ConversationMessage
from application.util.logger import setup_logger

logger = setup_logger("conversation_service") or logging.getLogger("conversation_service")


class ConversationService:
    """대화 관리 서비스"""

    def __init__(self):
        self._messages: List[ConversationMessage] = []

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> None:
        """메시지 추가"""
        if metadata is None:
            metadata = {}

        message = ConversationMessage(role=role, content=content, metadata=metadata)
        self._messages.append(message)
        logger.debug(f"메시지 추가: {role} - {content[:50]}...")

    def add_user_message(self, content: str, metadata: Dict[str, Any] = None) -> None:
        """사용자 메시지 추가"""
        self.add_message("user", content, metadata)

    def add_assistant_message(self, content: str, metadata: Dict[str, Any] = None) -> None:
        """어시스턴트 메시지 추가"""
        self.add_message("assistant", content, metadata)

    def add_system_message(self, content: str, metadata: Dict[str, Any] = None) -> None:
        """시스템 메시지 추가"""
        self.add_message("system", content, metadata)

    def get_messages(self) -> List[ConversationMessage]:
        """모든 메시지 반환"""
        return self._messages.copy()

    def get_messages_as_dict(self) -> List[Dict[str, Any]]:
        """메시지를 딕셔너리 형태로 반환"""
        return [msg.to_dict() for msg in self._messages]

    def clear_conversation(self) -> None:
        """대화 히스토리 초기화"""
        self._messages.clear()
        logger.info("대화 히스토리 초기화")

    def get_message_count(self) -> int:
        """메시지 개수 반환"""
        return len(self._messages)

    def get_last_message(self) -> ConversationMessage:
        """마지막 메시지 반환"""
        if not self._messages:
            raise ValueError("메시지가 없습니다")
        return self._messages[-1]

    def remove_last_message(self) -> ConversationMessage:
        """마지막 메시지 제거 후 반환"""
        if not self._messages:
            raise ValueError("제거할 메시지가 없습니다")
        removed_message = self._messages.pop()
        logger.debug(
            f"마지막 메시지 제거: {removed_message.role} - {removed_message.content[:50]}..."
        )
        return removed_message
