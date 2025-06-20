from __future__ import annotations

"""Deprecated location for ConversationManager.

실제 구현은 `application.ui.domain.conversation_manager` 로 이동했습니다.
"""

from application.ui.domain.conversation_manager import ConversationManager  # type: ignore

__all__: list[str] = ["ConversationManager"]
