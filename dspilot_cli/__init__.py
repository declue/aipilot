#!/usr/bin/env python3
"""
DSPilot CLI 패키지
=================

본 패키지는 DSPilot **Command-Line Interface** 구현체로, 터미널 환경에서
DSPilot 에이전트를 호출하고 다양한 MCP 도구를 실행할 수 있는 풍부한 UX를
제공합니다.

패키지 구조
-----------
- `cli_application.py` : 전체 *Facade* 역할을 하는 상위 애플리케이션.
- `cli_main.py`        : 인자 파싱, 앱 인스턴스화 등의 부트스트랩.
- `output_manager.py`  : 리치 텍스트, 컬러 출력, 로그 레벨 관리.
- 기타 하위 모듈       : 계획 수립(Planning), 단계 실행(StepExecutor),
  사용자 상호작용(InteractionManager) 등 SRP에 따라 분리.

핵심 개념
---------
1. **MCP (Multi-Capability Plugin) 아키텍처**
   모든 외부 기능은 *도구* 로 캡슐화되며 메타데이터 기반으로 동적으로 로드.
2. **TDD / SOLID**
   높은 테스트 커버리지와 단일 책임 원칙을 유지하여 확장성과 유지보수성 확보.
3. **풀-오토 vs 인터랙티브**
   플래그 하나(`--full-auto`)로 사용자가 직접 승인할지 여부를 제어.

`__all__` 에는 사용자 편의를 위해 최상위 진입점인 `main` 만 노출합니다.
"""

__version__ = "0.1.0"
__author__ = "JHL"

# 메인 진입점
from dspilot_cli.cli_main import main

__all__ = ["main"]

# ---------------------------------------------------------------------------
# 전역 JSON 직렬화 패치 – dataclass 객체를 안전하게 직렬화하기 위해 default=str
# ---------------------------------------------------------------------------

import dataclasses as _dataclasses  # pylint: disable=wrong-import-position, wrong-import-order
import json as _json  # pylint: disable=wrong-import-position, wrong-import-order

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
