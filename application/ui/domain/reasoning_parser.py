from __future__ import annotations

"""ReasoningParser – Domain Layer"""

import logging
import re

from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("reasoning_parser") or logging.getLogger(
    "reasoning_parser"
)


class ReasoningParser:
    """추론 과정을 파싱하는 클래스"""

    @staticmethod
    def parse_reasoning_content(content: str) -> tuple[bool, str, str]:
        """
        추론 과정과 최종 답변 분리
        Returns: (is_reasoning_model, reasoning_content, final_answer)
        """
        reasoning_pattern = r"<reasoning_content>(.*?)</reasoning_content>"
        match = re.search(reasoning_pattern, content, re.DOTALL)

        if match:
            return (
                True,
                match.group(1).strip(),
                re.sub(reasoning_pattern, "", content, flags=re.DOTALL).strip(),
            )

        # 태그 기반 분리 로직 (동일)
        if "</think>" in content:
            think_end_match = re.search(r"(.*?)</think>(.*)", content, re.DOTALL)
            if think_end_match:
                return (
                    True,
                    think_end_match.group(1).strip(),
                    think_end_match.group(2).strip(),
                )

        elif "<think>" in content:
            if "</think>" in content:
                think_match = re.search(r"<think>(.*?)</think>(.*)", content, re.DOTALL)
                if think_match:
                    return (
                        True,
                        think_match.group(1).strip(),
                        think_match.group(2).strip(),
                    )
                return True, content.strip(), ""
            think_start_match = re.search(r"<think>(.*)", content, re.DOTALL)
            if think_start_match:
                return True, think_start_match.group(1).strip(), ""
            return True, content.strip(), ""

        thinking_patterns = [
            r"<thinking>(.*?)(?:</thinking>|$)",
            r"<thought>(.*?)(?:</thought>|$)",
        ]
        for pattern in thinking_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                remaining = re.sub(
                    pattern.replace("(?:</thinking>|$)", "").replace(
                        "(?:</thought>|$)", ""
                    ),
                    "",
                    content,
                    flags=re.DOTALL | re.IGNORECASE,
                ).strip()
                return True, match.group(1).strip(), remaining

        return False, "", content 