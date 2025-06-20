from __future__ import annotations

"""application.ui 패키지

리팩토링 단계에서 추가된 presentation / domain / controllers / common
서브패키지를 쉽게 import 할 수 있도록 재노출한다.
"""

from importlib import import_module as _imp

for _sub in ("presentation", "domain", "controllers", "common"):
    try:
        globals()[_sub] = _imp(f"{__name__}.{_sub}")
    except ModuleNotFoundError:  # pragma: no cover - 방어적 처리
        pass

__all__: list[str] = [
    "presentation",
    "domain",
    "controllers",
    "common",
]
