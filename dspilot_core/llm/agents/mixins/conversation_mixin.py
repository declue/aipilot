#!/usr/bin/env python3
"""ConversationMixin: 대화 히스토리 관리 기능."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List

from dspilot_core.llm.services.conversation_service import ConversationService
from dspilot_core.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class ConversationMixin:
    """대화 히스토리 관련 헬퍼 메서드"""

    conversation_service: ConversationService
    history: List[Dict[str, str]]

    # ------------------------------------------------------------------
    # 외부 API (conversation)
    # ------------------------------------------------------------------
    def add_user_message(self, message: str) -> None:  # noqa: D401
        self.conversation_service.add_user_message(message)
        self.history.append({"role": "user", "content": message})

    def add_assistant_message(self, message: str) -> None:  # noqa: D401
        self.conversation_service.add_assistant_message(message)
        self.history.append({"role": "assistant", "content": message})

    def clear_conversation(self) -> None:  # noqa: D401
        self.conversation_service.clear_conversation()
        self.history.clear()
        # thread_id 는 BaseAgent 에서 재생성
        if hasattr(self, "thread_id"):
            setattr(self, "thread_id", str(datetime.now().timestamp()))
        logger.info("대화 히스토리 초기화")

    def get_conversation_history(self) -> List[Dict[str, str]]:  # noqa: D401
        messages = self.conversation_service.get_messages_as_dict()
        history: List[Dict[str, str]] = []
        for msg in messages:
            if isinstance(msg, dict):
                history.append(
                    {
                        "role": str(msg.get("role", "")),
                        "content": str(msg.get("content", "")),
                    }
                )
        return history
