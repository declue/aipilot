import tempfile
from pathlib import Path

from dspilot_cli.constants import ExecutionPlan, ExecutionStep
from dspilot_cli.plan_evaluator import PlanEvaluator
from dspilot_cli.plan_history_manager import PlanHistoryManager


def _temp_history_manager() -> PlanHistoryManager:
    tmp_file = Path(tempfile.gettempdir()) / "test_cli_history.json"
    if tmp_file.exists():
        tmp_file.unlink()
    return PlanHistoryManager(tmp_file)


def _sample_plan() -> ExecutionPlan:
    return ExecutionPlan(
        description="hist plan",
        steps=[
            ExecutionStep(step=1, description="ls", tool_name="shell", arguments={"cmd": "ls"}, confirm_message="ok"),
        ],
    )


def test_history_persistence():
    hist_mgr = _temp_history_manager()
    evaluator = PlanEvaluator(hist_mgr)
    plan = _sample_plan()

    assert evaluator.is_duplicate(plan) is False
    evaluator.register_plan(plan)
    assert evaluator.is_duplicate(plan) is True

    # Reload manager to verify persistence
    hist_mgr2 = PlanHistoryManager(hist_mgr.store_path)
    evaluator2 = PlanEvaluator(hist_mgr2)
    assert evaluator2.is_duplicate(plan) is True 