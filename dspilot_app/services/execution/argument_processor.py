"""Argument Processor for execution steps"""
import json
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ArgumentProcessor:
    """Substitutes placeholders in step arguments with actual results from previous steps."""

    def process(self, arguments: Dict[str, Any], step_results: Dict[int, Any]) -> Dict[str, Any]:
        """
        Processes arguments for a step, substituting placeholders.

        Args:
            arguments: The arguments dictionary for the step.
            step_results: A dictionary of results from previous steps.

        Returns:
            A new dictionary with placeholders substituted.
        """
        processed_args = {}
        for key, value in arguments.items():
            if isinstance(value, str):
                try:
                    # Try substituting $step_<N> style placeholders
                    value = self._substitute_dollar_step(value, key, step_results)
                    # Try substituting <step_<N>> style placeholders
                    value = self._substitute_angle_step(value, key, step_results)
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Failed to substitute placeholder for key '{key}'. "
                        f"Original value '{value}' will be used. Error: {e}"
                    )
            processed_args[key] = value
        return processed_args

    def _substitute_dollar_step(self, raw: str, arg_key: str, step_results: Dict[int, Any]) -> str:
        """Substitute $step_<N> placeholders."""
        # This regex finds all occurrences of $step_<number>
        matches = re.findall(r"\$(step_(\d+))", raw)
        substituted_value = raw
        for full_match, step_num_str in matches:
            step_num = int(step_num_str)
            if step_num in step_results:
                # Replace the placeholder with the result from the specified step
                placeholder = f"${full_match}"
                replacement = str(step_results[step_num])
                substituted_value = substituted_value.replace(placeholder, replacement)
            else:
                logger.warning(f"Result for step {step_num} not found for argument '{arg_key}'.")
        return substituted_value

    def _substitute_angle_step(self, raw: str, arg_key: str, step_results: Dict[int, Any]) -> str:
        """Substitute <step_<N>> placeholders."""
        # This regex finds all occurrences of <step_<number>>
        matches = re.findall(r"<(step_(\d+))>", raw)
        substituted_value = raw
        for full_match, step_num_str in matches:
            step_num = int(step_num_str)
            if step_num in step_results:
                # Replace the placeholder with the result from the specified step
                placeholder = f"<{full_match}>"
                replacement = str(step_results[step_num])
                substituted_value = substituted_value.replace(placeholder, replacement)
            else:
                logger.warning(f"Result for step {step_num} not found for argument '{arg_key}'.")
        return substituted_value

    def _is_malformed_placeholder(self, value: str) -> bool:
        """Check for malformed placeholders that are likely but not perfectly formatted."""
        # Example: Looks for "step <number>" or similar patterns not caught by precise regex
        return "step" in value and bool(re.search(r"\d", value)) and not re.fullmatch(r"<\w+>|\$\w+", value)

    def _recover_from_malformed_placeholder(
        self, value: str, key: str, step_results: Dict[int, Any]
    ) -> str:
        """Attempt to recover from a malformed placeholder."""
        # Simple recovery: find the first number and assume it's the step number.
        found_digits = re.findall(r"\d+", value)
        if found_digits:
            step_num = int(found_digits[0])
            if step_num in step_results:
                logger.info(f"Recovered step number {step_num} from malformed placeholder '{value}' for key '{key}'.")
                return str(step_results[step_num])
        logger.warning(f"Could not recover from malformed placeholder '{value}' for key '{key}'.")
        return value

    def _summarize_search_results(self, results: Any) -> str:
        """Summarize search results to a string."""
        if not isinstance(results, list):
            return str(results)

        summary_parts = []
        for i, item in enumerate(results[:3]):  # Summarize first 3 results
            title = item.get("title", "No Title")
            snippet = item.get("snippet", "No Snippet")
            summary_parts.append(f"{i+1}. {title}: {snippet}")
        summary = "\n".join(summary_parts)
        if len(results) > 3:
            summary += f"\n...and {len(results) - 3} more results."
        return summary

    def _extract_meaningful_content_from_dict(self, data: Dict[str, Any]) -> str:
        """Extract meaningful content from a dictionary, guessing at important keys."""
        if self._is_empty_or_useless_content(data):
            return self._generate_fallback_content(data)

        content_keys = ["content", "text", "summary", "description", "message"]
        for key in content_keys:
            if key in data and data[key]:
                return str(data[key])

        # Fallback to a string representation of the whole dictionary
        return json.dumps(data, indent=2)

    def _is_empty_or_useless_content(self, data: Dict[str, Any]) -> bool:
        """Check if the dictionary content is empty or not useful."""
        return not data or all(v is None or v == "" for v in data.values())

    def _generate_fallback_content(self, data: Dict[str, Any]) -> str:
        """Generate a fallback string if no meaningful content is found."""
        return f"Dictionary with keys: {', '.join(data.keys())}"

    def _contains_date_info(self, text: str) -> bool:
        """Check if a string contains date-like information."""
        # A simple regex to find things that look like dates
        return bool(re.search(r"\d{4}-\d{2}-\d{2}|\d{1,2}\s\w+\s\d{4}", text))

    def _extract_date_from_text(self, text: str) -> str:
        """Extract a date from text."""
        match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if match:
            return match.group(1)
        return ""

    def _extract_by_path(self, data: Any, path: str) -> Optional[str]:
        """Extracts a value from a nested dictionary using a dot-separated path."""
        try:
            keys = path.split('.')
            result = data
            for key in keys:
                if isinstance(result, dict):
                    result = result[key]
                elif isinstance(result, list):
                    result = result[int(key)]
                else:
                    return None
            return str(result)
        except (KeyError, IndexError, TypeError):
            return None 