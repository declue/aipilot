from __future__ import annotations

"""Deprecated module preserving backward-compatibility.

The real implementation of `AIChatBubble` now lives in
`application.ui.presentation.ai_chat_bubble`.  This thin wrapper only
re-exports the class so that old import paths continue to work.
"""

__all__: list[str] = ["AIChatBubble"]

import importlib
from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from application.ui.presentation.ai_chat_bubble import AIChatBubble  # noqa: F401


def __getattr__(name: str) -> Any:  # pragma: no cover
    """Dynamically import the real implementation on first attribute access.

    This lazy-loading pattern avoids an import cycle between the legacy path
    and the new presentation module.  The first time someone accesses
    ``application.ui.ai_chat_bubble.AIChatBubble`` we import the real module
    and re-export the symbol.
    """

    if name == "AIChatBubble":
        module: ModuleType = importlib.import_module("application.ui.presentation.ai_chat_bubble")
        cls = getattr(module, "AIChatBubble")
        globals()[name] = cls  # cache for future look-ups
        return cls
    raise AttributeError(name)
