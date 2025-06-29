from dspilot_cli.constants import ExecutionPlan, ExecutionStep
from dspilot_cli.plan_refiner import PlanRefiner


def _plan_with_duplicates():
    return ExecutionPlan(
        description="dup plan",
        steps=[
            ExecutionStep(step=1, description="do", tool_name="shell", arguments={"cmd": "ls"}, confirm_message="ok"),
            ExecutionStep(step=2, description="again", tool_name="shell", arguments={"cmd": "ls"}, confirm_message="ok"),
            ExecutionStep(step=3, description="different", tool_name="shell", arguments={"cmd": "pwd"}, confirm_message="ok"),
        ],
    )


def test_plan_refiner_removes_duplicates():
    refiner = PlanRefiner()
    plan, changed = refiner.refine(_plan_with_duplicates())

    assert changed is True
    assert len(plan.steps) == 2  # ls, pwd
    assert plan.steps[0].step == 1
    assert plan.steps[1].step == 2 