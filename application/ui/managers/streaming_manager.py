from __future__ import annotations

"""Deprecated location for StreamingManager – stub.

실제 구현은 `application.ui.domain.streaming_manager` 로 이동했습니다.
하위 호환성을 위해 동일 클래스를 재-익스포트합니다.
"""

from application.ui.domain.streaming_manager import StreamingManager  # type: ignore

__all__: list[str] = ["StreamingManager"]
