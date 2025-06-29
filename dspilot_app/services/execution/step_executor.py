"""Step Executor for executing a single step of an execution plan."""
import logging
from typing import Any, Callable, Dict, Optional

from dspilot_app.services.execution.argument_processor import ArgumentProcessor
from dspilot_app.services.execution.success_evaluator import SuccessEvaluator
from dspilot_app.services.models.execution_plan import ExecutionStep
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager

logger = logging.getLogger(__name__)


class StepExecutor:
    """Executes a single step of an execution plan."""

    def __init__(
        self,
        llm_agent: BaseAgent,
        mcp_tool_manager: MCPToolManager,
        argument_processor: Optional[ArgumentProcessor] = None,
        success_evaluator: Optional[SuccessEvaluator] = None,
    ) -> None:
        self.llm_agent = llm_agent
        self.mcp_tool_manager = mcp_tool_manager
        self.argument_processor = argument_processor or ArgumentProcessor()
        self.success_evaluator = success_evaluator or SuccessEvaluator()

    async def execute_step(
        self,
        step: ExecutionStep,
        step_results: Dict[int, Any],
        get_user_confirmation: Callable[..., bool],
    ) -> tuple[bool, Any]:
        """
        Executes a single step.

        Args:
            step: The execution step to perform.
            step_results: Dictionary of results from previous steps.
            get_user_confirmation: An awaitable function to get user confirmation.

        Returns:
            A tuple of (success, result).
        """
        logger.info(f"Executing step {step.step}: {step.description}")
        processed_args = self.argument_processor.process(step.arguments, step_results)

        # In a GUI app, confirmation is handled by the ExecutionManager via signals
        # We rely on the passed-in async callable `get_user_confirmation`.
        if not get_user_confirmation(step.description, step.tool_name, processed_args):
            logger.warning(f"Step {step.step} cancelled by user.")
            return False, "Step cancelled by user"

        try:
            result = await self.mcp_tool_manager.execute_tool(step.tool_name, **processed_args)
            logger.info(f"Step {step.step} raw result: {str(result)[:200]}...")

            is_successful = self.success_evaluator.is_successful(result, step.tool_name)
            if is_successful:
                logger.info(f"Step {step.step} completed successfully.")
                return True, result
            else:
                logger.warning(f"Step {step.step} execution was not successful. Result: {result}")
                return False, result
        except Exception as e:
            logger.error(f"Error executing step {step.step}: {e}", exc_info=True)
            return False, str(e) 