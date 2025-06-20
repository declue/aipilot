from __future__ import annotations

"""Deprecated location for ReasoningParser – stub wrapper.

실제 구현은 `application.ui.domain.reasoning_parser` 로 이동했습니다.
이 모듈은 하위 호환성을 위해 클래스를 재-익스포트만 합니다.
"""

import logging
import re

from application.util.logger import setup_logger

__all__: list[str] = ["ReasoningParser"]


logger: logging.Logger = setup_logger("reasoning_parser") or logging.getLogger(
    "reasoning_parsewr"
)


class ReasoningParser:
    """추론 과정을 파싱하는 클래스"""

    @staticmethod
    def parse_reasoning_content(content: str) -> tuple[bool, str, str]:
        """
        추론 과정과 최종 답변 분리
        Returns: (is_reasoning_model, reasoning_content, final_answer)
        """
        # <reasoning_content> 태그 검사
        reasoning_pattern = r"<reasoning_content>(.*?)</reasoning_content>"
        match = re.search(reasoning_pattern, content, re.DOTALL)

        if match:
            return (
                True,
                match.group(1).strip(),
                re.sub(reasoning_pattern, "", content, flags=re.DOTALL).strip(),
            )

        # 끝에만 </think> 태그가 있는 패턴 확인
        if "</think>" in content:
            think_end_match = re.search(r"(.*?)</think>(.*)", content, re.DOTALL)
            if think_end_match:
                reasoning_content = think_end_match.group(1).strip()
                final_answer = think_end_match.group(2).strip()
                logger.debug(
                    f"🧠 </think> 태그 감지 - 추론: {len(reasoning_content)}자, 답변: {len(final_answer)}자"
                )
                return True, reasoning_content, final_answer

        # <think> 시작 태그가 있는지 확인
        elif "<think>" in content:
            if "</think>" in content:
                # 완전한 think 블록
                think_match = re.search(r"<think>(.*?)</think>(.*)", content, re.DOTALL)
                if think_match:
                    reasoning_content = think_match.group(1).strip()
                    final_answer = think_match.group(2).strip()
                    return True, reasoning_content, final_answer
                else:
                    return True, content.strip(), ""
            else:
                # 진행 중인 think 블록
                think_start_match = re.search(r"<think>(.*)", content, re.DOTALL)
                if think_start_match:
                    reasoning_content = think_start_match.group(1).strip()
                    return True, reasoning_content, ""
                else:
                    return True, content.strip(), ""

        # 기존 완전한 태그 패턴들 확인
        thinking_patterns = [
            r"<thinking>(.*?)(?:</thinking>|$)",
            r"<thought>(.*?)(?:</thought>|$)",
        ]

        for pattern in thinking_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                reasoning_content = match.group(1).strip()
                remaining_content = re.sub(
                    pattern.replace("(?:</thinking>|$)", "").replace(
                        "(?:</thought>|$)", ""
                    ),
                    "",
                    content,
                    flags=re.DOTALL | re.IGNORECASE,
                ).strip()
                logger.debug(f"🧠 {pattern} 패턴 감지")
                return True, reasoning_content, remaining_content

        return False, "", content
