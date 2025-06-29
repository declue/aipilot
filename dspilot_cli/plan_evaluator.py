"""PlanEvaluator – 실행 계획 평가 및 중복 감지 모듈

이 모듈은 ExecutionPlan의 해시 관리와 단계 실행 결과 내 오류 탐지를 담당한다.
외부에서는 evaluate() 하나로 `has_errors`·`plan_duplicate` 플래그를 얻을 수 있다.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Set

from dspilot_cli.constants import ExecutionPlan
from dspilot_cli.plan_history_manager import PlanHistoryManager


class PlanEvaluator:
    """ExecutionPlan 평가기

    Responsibilities
    -----------------
    • 계획 해시(내용 기반) 생성 및 중복 여부 결정
    • 단계 실행 결과(step_results)에서 오류 메시지 추출
    """

    def __init__(self, history_manager: Optional[PlanHistoryManager] = None) -> None:
        self._executed_plan_hashes: Set[str] = set()
        self._history_manager = history_manager or PlanHistoryManager()

    # ------------------------------------------------------------------
    # 해시 및 중복
    # ------------------------------------------------------------------

    @staticmethod
    def generate_plan_hash(plan: ExecutionPlan) -> str:
        """ExecutionPlan 객체를 deterministic JSON으로 직렬화 후 SHA256 해시 반환"""

        # dataclasses.asdict 가 아닌 직접 접근 (steps 내부에도 dataclass 포함)
        plan_dict = {
            "description": plan.description,
            "steps": [
                {
                    "step": s.step,
                    "description": s.description,
                    "tool_name": s.tool_name,
                    "arguments": s.arguments,
                }
                for s in plan.steps
            ],
        }
        raw = json.dumps(plan_dict, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def is_duplicate(self, plan: ExecutionPlan) -> bool:
        """이미 실행된 계획인지 확인"""
        plan_hash = self.generate_plan_hash(plan)
        return plan_hash in self._executed_plan_hashes or self._history_manager.has(plan_hash)

    def register_plan(self, plan: ExecutionPlan) -> None:
        """계획 해시를 내부 세트에 등록"""
        plan_hash = self.generate_plan_hash(plan)
        self._executed_plan_hashes.add(plan_hash)
        self._history_manager.add(plan_hash)

    # ------------------------------------------------------------------
    # 오류 탐지
    # ------------------------------------------------------------------

    @staticmethod
    def detect_errors_in_results(step_results: Dict[int, Any]) -> List[str]:
        """step_results dict에서 'error' 키 또는 정규식으로 오류를 탐지"""
        errors: List[str] = []
        for raw in step_results.values():
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and data.get("error"):
                    errors.append(str(data.get("error")))
            except Exception:
                if re.search(r"error", str(raw), re.IGNORECASE):
                    errors.append(str(raw))
        return errors

    # ------------------------------------------------------------------
    # 종합 평가
    # ------------------------------------------------------------------

    def evaluate(self, plan: ExecutionPlan | None, step_results: Dict[int, Any]) -> Dict[str, Any]:
        """계획과 실행 결과를 종합 평가

        Returns:
            dict(has_plan, plan_duplicate, has_errors, errors)
        """
        if plan is None:
            return {
                "has_plan": False,
                "plan_duplicate": False,
                "has_errors": False,
                "errors": [],
            }

        duplicate = self.is_duplicate(plan)
        if not duplicate:
            self.register_plan(plan)

        errors = self.detect_errors_in_results(step_results)
        return {
            "has_plan": True,
            "plan_duplicate": duplicate,
            "has_errors": bool(errors),
            "errors": errors,
        } 