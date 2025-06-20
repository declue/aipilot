from __future__ import annotations

# pylint: disable=wrong-import-position

"""Deprecated location for StyleManager.

실제 구현은 `application.ui.common.style_manager` 로 이동했습니다.
이 모듈은 하위 호환성을 위해 남겨둔 레거시 래퍼입니다.
"""

from application.ui.common.style_manager import StyleManager  # type: ignore

__all__: list[str] = ["StyleManager"]
