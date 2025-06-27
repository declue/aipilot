"""
Base interface for tool result processors
"""

from abc import ABC, abstractmethod
from typing import Dict, List


class ToolResultProcessor(ABC):
    """Base interface for processing tool results"""

    @abstractmethod
    def can_process(self, tool_name: str) -> bool:
        """Check if this processor can handle the given tool"""
        pass

    @abstractmethod
    def process(self, tool_name: str, tool_result: str) -> str:
        """Process tool result and return formatted output"""
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """Return processor priority (higher number = higher priority)"""
        pass


class DefaultToolResultProcessor(ToolResultProcessor):
    """Default processor for generic tool results"""

    def can_process(self, tool_name: str) -> bool:
        """Can process any tool as fallback"""
        return True

    def process(self, tool_name: str, tool_result: str) -> str:
        """Basic processing for generic tools"""
        try:
            import json

            data = json.loads(tool_result)
            result_str = data.get("result", tool_result)
            cleaned = str(result_str).strip()
            if cleaned:
                return f"- {cleaned}"
            return "- 도구 결과를 처리할 수 없습니다."
        except Exception:
            # JSON 파싱 실패 → 그대로 출력
            return f"- {tool_result.strip()}"

    def get_priority(self) -> int:
        """Lowest priority - fallback processor"""
        return 0


class ToolResultProcessorRegistry:
    """Registry for managing tool result processors"""

    def __init__(self):
        self.processors: List[ToolResultProcessor] = []
        # Register default processor
        self.register(DefaultToolResultProcessor())

    def register(self, processor: ToolResultProcessor) -> None:
        """Register a new processor"""
        self.processors.append(processor)
        # Sort by priority (highest first)
        self.processors.sort(key=lambda p: p.get_priority(), reverse=True)

    def get_processor(self, tool_name: str) -> ToolResultProcessor:
        """Get the best processor for the given tool"""
        for processor in self.processors:
            if processor.can_process(tool_name):
                return processor
        # This should never happen since DefaultProcessor accepts all
        return self.processors[-1]

    def process_tool_results(self, used_tools: List[str], tool_results: Dict[str, str]) -> str:
        """Process multiple tool results"""
        if not used_tools or not tool_results:
            return "도구 결과가 없습니다."

        output_lines: List[str] = []
        for tool_name in used_tools:
            raw = tool_results.get(tool_name, "")
            if raw:
                processor = self.get_processor(tool_name)
                formatted = processor.process(tool_name, raw)
                if formatted:
                    output_lines.append(formatted)

        if output_lines:
            return "\n".join(output_lines)
        return "도구 결과를 처리하는 중 문제가 발생했습니다."
