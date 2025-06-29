import json

from dspilot_cli.constants import ExecutionPlan, ExecutionStep
from dspilot_cli.plan_evaluator import PlanEvaluator


def _sample_plan() -> ExecutionPlan:
    return ExecutionPlan(
        description="Sample plan",
        steps=[
            ExecutionStep(
                step=1,
                description="echo hello",
                tool_name="shell",
                arguments={"cmd": "echo hello"},
                confirm_message="ok?",
            )
        ],
    )


def test_duplicate_detection():
    evaluator = PlanEvaluator()
    plan = _sample_plan()

    # First registration should not be duplicate
    res1 = evaluator.evaluate(plan, {})
    assert res1["plan_duplicate"] is False

    # Second evaluate with same plan should flag duplicate
    res2 = evaluator.evaluate(plan, {})
    assert res2["plan_duplicate"] is True


def test_error_detection():
    evaluator = PlanEvaluator()
    plan = _sample_plan()

    step_results = {1: json.dumps({"result": "fail", "error": "Something went wrong"})}
    res = evaluator.evaluate(plan, step_results)
    assert res["has_errors"] is True
    assert "Something went wrong" in res["errors"][0] 