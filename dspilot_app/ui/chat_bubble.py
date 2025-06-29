from __future__ import annotations

"""Deprecated location for ChatBubble.

실제 구현은 `dspilot_app.ui.presentation.base_chat_bubble` 로 이동했습니다.
이 모듈은 하위 호환성을 위해 남겨둔 래퍼입니다.
"""

from dspilot_app.ui.presentation.base_chat_bubble import ChatBubble  # type: ignore

__all__: list[str] = ["ChatBubble"]
