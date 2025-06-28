from __future__ import annotations

"""Friendly message builder – 기존 WebhookClient._create_friendly_message 로직을
간접 호출하여 WebhookClient 의존성을 제거한다.

TODO: 향후 이벤트별 Builder 클래스로 세분화하고 직접 구현을 옮길 예정.
"""

from typing import TYPE_CHECKING, Any, Dict, Tuple

from dspilot_core.util.message_builders import get_builder

if TYPE_CHECKING:  # pragma: no cover
    # 순환 참조를 피하기 위해 타입 체크 시에만 가져옴
    from dspilot_core.util.webhook_client import WebhookClient  # noqa: F401


def build_friendly_message(message: Dict[str, Any]) -> Tuple[str, str]:
    """친숙한 제목/내용 쌍을 생성한다.

    현재는 WebhookClient 내부 기존 구현을 재활용한다. 차후 독립 구현으로 대체.
    """
    # 1) 이벤트별 전용 빌더 우선 사용
    event_type = message.get("event_type", "")
    builder = get_builder(event_type)
    if builder is not None:
        return builder.build(message)

    # 2) 아직 분리되지 않은 이벤트는 기존 WebhookClient 메서드 재활용
    

    # 순환 import을 피하기 위해 함수 내부에서 지연 로딩
    from dspilot_core.util.webhook_client import WebhookClient  # type: ignore

    dummy_client = object.__new__(WebhookClient)  # type: ignore[arg-type]
    return WebhookClient._create_friendly_message(dummy_client, message)  # type: ignore[attr-defined]
