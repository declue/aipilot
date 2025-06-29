from __future__ import annotations

"""Stub module for backward-compatible import path.

Eventually, the full implementation will be migrated here. For now we simply
re-export the existing class to keep the refactor incremental.
"""

from dspilot_app.ui.presentation.base_chat_bubble import ChatBubble as _ChatBubble  # type: ignore

ChatBubble = _ChatBubble  # re-export

__all__: list[str] = ["ChatBubble"]
