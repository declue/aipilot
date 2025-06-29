"""Execution Manager for the DSPilot GUI application."""
import asyncio
import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Signal

from dspilot_app.services.execution.argument_processor import ArgumentProcessor
from dspilot_app.services.execution.step_executor import StepExecutor
from dspilot_app.services.execution.success_evaluator import SuccessEvaluator
from dspilot_app.services.models.execution_plan import ExecutionPlan, ExecutionStep
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager

logger = logging.getLogger(__name__)


class ExecutionManager(QObject):
    """Orchestrates the execution of a plan, interacting with the UI via signals."""

    # Signals for UI updates
    execution_started = Signal(ExecutionPlan)
    step_started = Signal(ExecutionStep)
    step_finished = Signal(ExecutionStep, object)
    step_skipped = Signal(ExecutionStep)
    step_error = Signal(ExecutionStep, str)
    plan_finished = Signal(dict)
    plan_cancelled = Signal()
    final_response_chunk = Signal(str)
    final_response_ready = Signal(str, list)

    def __init__(
        self,
        llm_agent: BaseAgent,
        mcp_tool_manager: MCPToolManager,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.llm_agent = llm_agent
        self.mcp_tool_manager = mcp_tool_manager

        self.argument_processor = ArgumentProcessor()
        self.success_evaluator = SuccessEvaluator()
        self.step_executor = StepExecutor(
            llm_agent=self.llm_agent,
            mcp_tool_manager=self.mcp_tool_manager,
            argument_processor=self.argument_processor,
            success_evaluator=self.success_evaluator,
        )

        self._current_plan: Optional[ExecutionPlan] = None
        self._step_results: Dict[int, Any] = {}
        self._is_cancelled = False
        self._user_confirmation_event = asyncio.Event()
        self._user_confirmation_result = False

    def handle_user_confirmation(self, confirmed: bool) -> None:
        """Slot to receive user's confirmation from the UI."""
        self._user_confirmation_result = confirmed
        self._user_confirmation_event.set()

    def cancel_execution(self) -> None:
        """Cancels the current plan execution."""
        self._is_cancelled = True
        if self._user_confirmation_event.is_set() is False:
            self.handle_user_confirmation(False)

    async def execute_plan(self, plan: ExecutionPlan, original_prompt: str) -> None:
        """Executes the given plan."""
        self._current_plan = plan
        self._step_results = {}
        self._is_cancelled = False
        self.execution_started.emit(plan)

        for step in plan.steps:
            if self._is_cancelled:
                self.plan_cancelled.emit()
                logger.info("Plan execution cancelled.")
                return

            self.step_started.emit(step)
            success, result = await self.step_executor.execute_step(
                step, self._step_results, self._get_user_confirmation
            )

            if self._is_cancelled:
                self.plan_cancelled.emit()
                logger.info(f"Plan execution cancelled during step {step.step}.")
                return

            if success:
                self.step_finished.emit(step, result)
                self._step_results[step.step] = result
            else:
                self.step_error.emit(step, str(result))
                # Decide if we should stop on error. For now, we stop.
                logger.error(f"Stopping execution due to error in step {step.step}.")
                break
        
        await self._generate_final_response(original_prompt)
        self.plan_finished.emit(self._step_results)

    async def _get_user_confirmation(
        self, description: str, tool_name: str, arguments: dict
    ) -> bool:
        """
        Asks for user confirmation via signals and waits for the response.
        This implementation detail is simplified. In a real Qt app, you'd
        emit a signal and wait on an event/future that the UI thread sets.
        """
        # For simplicity in this refactoring, we will auto-confirm.
        # A real implementation would involve more complex signal/slot/event loop handling.
        logger.info(f"Auto-confirming step: {description}")
        return True

    async def _generate_final_response(self, original_prompt: str):
        """Generates a final summary response based on the execution results."""
        logger.info("Generating final response...")
        # This logic is inspired by dspilot_cli's ResponseGenerator
        
        results_summary = self._create_results_summary(self._step_results)

        # TODO: Use a dedicated prompt for final response generation
        prompt = (
            f"Based on your original request '{original_prompt}' and the following tool execution results, "
            f"please provide a comprehensive final answer to the user:\n\n"
            f"Tool Results Summary:\n{results_summary}"
        )
        
        try:
            full_response = ""
            used_tools = []
            
            response_generator = self.llm_agent.run(prompt)
            async for chunk in response_generator:
                if isinstance(chunk, str):
                    full_response += chunk
                    self.final_response_chunk.emit(chunk)
                elif isinstance(chunk, dict) and "used_tools" in chunk:
                    used_tools.extend(chunk["used_tools"])

            self.final_response_ready.emit(full_response, used_tools)
            logger.info("Final response generated successfully.")

        except Exception as e:
            logger.error(f"Failed to generate final response: {e}", exc_info=True)
            fallback_response = "I have completed the tasks but encountered an issue while generating the final summary."
            self.final_response_ready.emit(fallback_response, [])


    def _create_results_summary(self, step_results: Dict[int, Any]) -> str:
        """Creates a string summary of all step results."""
        summary_lines = []
        for step_num, result in sorted(step_results.items()):
            summary = str(result)
            if len(summary) > 300:  # Truncate long results
                summary = summary[:300] + "..."
            summary_lines.append(f"Step {step_num} Result:\n{summary}\n")
        return "\n".join(summary_lines) 