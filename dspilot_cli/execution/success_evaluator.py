"""Generic success evaluation logic extracted from StepExecutor.

이 모듈은 도구 실행 결과의 성공/실패 여부를 범용적으로 판단합니다.
특정 MCP 도구에 의존하지 않으며, 메타데이터 기반 평가를 제공합니다.
"""
from __future__ import annotations

import json
from typing import Any, Dict

__all__ = ["SuccessEvaluator"]


class SuccessEvaluator:
    """도구 실행 결과의 성공 여부를 평가한다."""

    def is_successful(self, result: Any, tool_name: str | None = None) -> bool:  # noqa: D401
        """Evaluate result object and return True if considered successful."""
        try:
            # 문자열 결과 처리
            if isinstance(result, str):
                try:
                    parsed = json.loads(result)
                    return self._evaluate_dict(parsed)
                except json.JSONDecodeError:
                    return self._analyze_text(result)

            if isinstance(result, dict):
                return self._evaluate_dict(result)

            # 기타 타입(리스트 등)은 None 이 아니면 성공으로 간주
            return result is not None
        except Exception:  # noqa: broad-except
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _evaluate_dict(self, data: Dict[str, Any]) -> bool:
        if "success" in data:
            return bool(data["success"])
        if data.get("error"):
            return False
        if "query" in data and "count" in data:
            return True
        if "path" in data or "message" in data:
            return True
        if any(k in data for k in ["date", "iso_date", "result"]):
            return True
        return bool(data)

    def _analyze_text(self, text: str) -> bool:
        lower = text.lower()
        if any(tok in lower for tok in ["error", "failed", "실패", "오류"]):
            return False
        if any(tok in lower for tok in ["success", "완료", "저장", "생성", "조회"]):
            return True
        return bool(text.strip()) 