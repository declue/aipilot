"""Success Evaluator for execution steps"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SuccessEvaluator:
    """Evaluates if a step execution was successful based on its result."""

    def is_successful(self, result: Any, tool_name: str | None = None) -> bool:  # noqa: D401
        """
        Check if the result indicates a successful execution.
        This is a basic implementation and can be expanded.
        """
        if result is None:
            return False
        if isinstance(result, bool):
            return result
        if isinstance(result, dict):
            return self._evaluate_dict(result)
        if isinstance(result, str):
            return self._analyze_text(result)
        # For other types, assume success if they are not "empty"
        return bool(result)

    def _evaluate_dict(self, data: Dict[str, Any]) -> bool:
        """Evaluate a dictionary result."""
        if "error" in data or "failed" in data.get("status", ""):
            return False
        if "success" in data.get("status", ""):
            return True
        # Assume success if no explicit error/failure indicators are present
        return True

    def _analyze_text(self, text: str) -> bool:
        """Analyze a string result for success/failure keywords."""
        text_lower = text.lower()
        failure_keywords = ["error", "failed", "unable to", "could not", "not found"]
        if any(keyword in text_lower for keyword in failure_keywords):
            return False
        return True 