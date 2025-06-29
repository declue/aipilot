
"""PlanRefiner – ExecutionPlan 개선/중복 단계 병합 모듈

간단한 규칙:
1. 같은 tool_name & arguments 의 단계는 하나로 병합 (첫 번째 설명 유지)
2. 순서 보존 – 첫 등장 단계 번호를 유지, 최종적으로 1..N 재번호부여

향후 확장을 위한 Hook 메서드(`_custom_refine`) 준비.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from dspilot_cli.constants import ExecutionPlan, ExecutionStep


class PlanRefiner:  # pylint: disable=too-few-public-methods
    """ExecutionPlan 리파이너"""

    def refine(self, plan: ExecutionPlan) -> Tuple[ExecutionPlan, bool]:
        """중복 단계 제거·병합 후 새로운 ExecutionPlan 반환

        Returns: (refined_plan, changed_flag)
        """
        seen_keys: Dict[Tuple[str, str], ExecutionStep] = {}
        refined_steps: List[ExecutionStep] = []

        for step in plan.steps:
            key = (step.tool_name, str(step.arguments))
            if key in seen_keys:
                continue  # 중복 → 스킵
            seen_keys[key] = step
            refined_steps.append(step)

        # 재번호 부여
        for idx, s in enumerate(refined_steps, start=1):
            s.step = idx  # mutating OK – dataclass

        changed = len(refined_steps) != len(plan.steps)
        if not changed:
            return plan, False

        return ExecutionPlan(description=plan.description, steps=refined_steps), True
