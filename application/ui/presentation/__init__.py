from __future__ import annotations

"""application.ui.presentation

Presentation layer components (PySide6 widgets).

이 패키지는 기존 UI 버블 클래스들을 재-익스포트하여 신규 모듈 구조와의
하위 호환성을 동시에 제공합니다. 실제 구현 파일은 추후 단계적으로
이동하거나 리팩토링할 예정입니다.
"""

from application.ui.presentation.ai_chat_bubble import AIChatBubble  # type: ignore
from application.ui.presentation.chat_bubble import ChatBubble  # type: ignore
from application.ui.presentation.streaming_bubble_manager import (
    StreamingBubbleManager,  # type: ignore
)
from application.ui.presentation.streaming_html_renderer import (
    StreamingHtmlRenderer,  # type: ignore
)
from application.ui.presentation.system_chat_bubble import SystemChatBubble  # type: ignore
from application.ui.presentation.user_chat_bubble import UserChatBubble  # type: ignore

__all__: list[str] = [
    "ChatBubble",
    "AIChatBubble",
    "UserChatBubble",
    "SystemChatBubble",
    "StreamingBubbleManager",
    "StreamingHtmlRenderer",
] 