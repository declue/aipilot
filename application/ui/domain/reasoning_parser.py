from __future__ import annotations

import logging
import re

from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("ui") or logging.getLogger("ui")


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

        # <thinking> 태그
        thinking_tag_pattern = r"<thinking>(.*?)</thinking>"
        match = re.search(thinking_tag_pattern, content, re.DOTALL)
        if match:
            reasoning_content = match.group(1).strip()
            final_answer = re.sub(thinking_tag_pattern, "", content, flags=re.DOTALL).strip()
            logger.debug(f"🧠 thinking 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자")
            return (True, reasoning_content, final_answer)

        # <thought> 태그
        thought_tag_pattern = r"<thought>(.*?)</thought>"
        match = re.search(thought_tag_pattern, content, re.DOTALL)
        if match:
            reasoning_content = match.group(1).strip()
            final_answer = re.sub(thought_tag_pattern, "", content, flags=re.DOTALL).strip()
            logger.debug(f"🧠 thought 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자")
            return (True, reasoning_content, final_answer)

        # <analysis> 태그
        analysis_tag_pattern = r"<analysis>(.*?)</analysis>"
        match = re.search(analysis_tag_pattern, content, re.DOTALL)
        if match:
            reasoning_content = match.group(1).strip()
            final_answer = re.sub(analysis_tag_pattern, "", content, flags=re.DOTALL).strip()
            logger.debug(f"🧠 analysis 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자")
            return (True, reasoning_content, final_answer)

        # ------------------------------------------------------------------
        # Heuristic fallback: 자주 쓰이는 마커("Thought", "Reasoning", "🔎") 등 이용
        # 예) "**Thought**:\n...\n**Answer**:" 구조
        # ------------------------------------------------------------------
        try:
            thought_regex = r"(?is)(?:^|\n)(?:thoughts?|reasoning|analysis|🔎)[:：]\s*(.*?)\n{1,2}(?:answer|final|결론)[:：]"
            match = re.search(thought_regex, content, re.DOTALL)
            if match:
                reasoning_content = match.group(1).strip()
                idx_end = match.end()
                final_answer = content[idx_end:].strip()
                if reasoning_content and final_answer:
                    logger.debug("🧠 휴리스틱 마커 감지: 추론 %s자, 답변 %s자", len(reasoning_content), len(final_answer))
                    return (True, reasoning_content, final_answer)
        except Exception as e:  # pragma: no cover
            logger.debug("휴리스틱 파싱 오류: %s", e)

        logger.debug(f"🧠 추론 과정 없음: 일반 응답 {len(content)}자")
        return (False, "", content) 