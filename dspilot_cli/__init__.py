#!/usr/bin/env python3
"""
DSPilot CLI 패키지
"""

__version__ = "0.1.0"
__author__ = "JHL"

# 메인 진입점
from dspilot_cli.cli_main import main

__all__ = ["main"]

# ---------------------------------------------------------------------------
# 전역 JSON 직렬화 패치 – dataclass 객체를 안전하게 직렬화하기 위해 default=str
# ---------------------------------------------------------------------------

import dataclasses as _dataclasses  # pylint: disable=wrong-import-position
import json as _json  # pylint: disable=wrong-import-position

_original_json_dumps = _json.dumps  # 보존


def _dataclass_safe_default(obj):  # noqa: D401
    """json.dumps default 함수 – dataclass → dict, 기타 객체 → str"""
    if _dataclasses.is_dataclass(obj):
        return _dataclasses.asdict(obj)
    # 집합 → 리스트 등 간단 변환 (테스트 코드 호환)
    if isinstance(obj, set):
        return list(obj)
    return str(obj)


def _patched_dumps(obj, *args, **kwargs):  # noqa: D401 pylint: disable=missing-function-docstring
    if "default" not in kwargs:
        kwargs["default"] = _dataclass_safe_default
    return _original_json_dumps(obj, *args, **kwargs)

# json.dumps 패치 (한 번만 적용)
if not hasattr(_json.dumps, "_dspilot_patched"):
    _json.dumps = _patched_dumps  # type: ignore[assignment]
    _json.dumps._dspilot_patched = True  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
