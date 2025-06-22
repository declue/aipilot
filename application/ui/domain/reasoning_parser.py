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
        logger.debug(f"🧠 추론 파싱 시작: {len(content)}자, 첫 100자: {content[:100]}")
        
        reasoning_pattern = r"<reasoning_content>(.*?)</reasoning_content>"
        match = re.search(reasoning_pattern, content, re.DOTALL)

        if match:
            reasoning_content = match.group(1).strip()
            final_answer = re.sub(reasoning_pattern, "", content, flags=re.DOTALL).strip()
            logger.debug(f"🧠 reasoning_content 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자")
            return (True, reasoning_content, final_answer)

        # 태그 기반 분리 로직 (동일)
        if "</think>" in content:
            think_pattern = r"<think>(.*?)</think>"
            match = re.search(think_pattern, content, re.DOTALL)
            if match:
                reasoning_content = match.group(1).strip()
                final_answer = re.sub(think_pattern, "", content, flags=re.DOTALL).strip()
                logger.debug(f"🧠 think 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자")
                return (True, reasoning_content, final_answer)

        # reasoning 태그
        reasoning_tag_pattern = r"<reasoning>(.*?)</reasoning>"
        match = re.search(reasoning_tag_pattern, content, re.DOTALL)
        if match:
            reasoning_content = match.group(1).strip()
            final_answer = re.sub(reasoning_tag_pattern, "", content, flags=re.DOTALL).strip()
            logger.debug(f"🧠 reasoning 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자")
            return (True, reasoning_content, final_answer)

        logger.debug(f"🧠 추론 과정 없음: 일반 응답 {len(content)}자")
        return (False, "", content) 