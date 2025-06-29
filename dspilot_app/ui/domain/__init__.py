from __future__ import annotations

"""dspilot_app.ui.domain

Domain layer – 상태 관리 및 비즈니스 로직.
현재 단계에서는 기존 매니저 클래스를 재-익스포트하여 점진적 마이그레이션을
가능하게 합니다.
"""

from dspilot_app.ui.domain.conversation_manager import ConversationManager  # type: ignore
from dspilot_app.ui.domain.message_manager import MessageManager  # type: ignore
from dspilot_app.ui.domain.reasoning_parser import ReasoningParser  # type: ignore
from dspilot_app.ui.domain.streaming_manager import StreamingManager  # type: ignore
from dspilot_app.ui.domain.streaming_state import StreamingState  # type: ignore

__all__: list[str] = [
    "ConversationManager",
    "StreamingManager",
    "ReasoningParser",
    "StreamingState",
    "MessageManager",
]
