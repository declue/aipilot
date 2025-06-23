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

        # 먼저 스트리밍 중인 부분적 추론 과정 감지
        partial_result = ReasoningParser._parse_partial_reasoning(content)
        if partial_result[0]:  # 부분적 추론 과정이 감지된 경우
            return partial_result

        reasoning_pattern = r"<reasoning_content>(.*?)</reasoning_content>"
        match = re.search(reasoning_pattern, content, re.DOTALL)

        if match:
            reasoning_content = match.group(1).strip()
            final_answer = re.sub(reasoning_pattern, "", content, flags=re.DOTALL).strip()
            logger.debug(
                f"🧠 reasoning_content 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자"
            )
            return (True, reasoning_content, final_answer)

        # 태그 기반 분리 로직 (동일)
        if "</think>" in content:
            think_pattern = r"<think>(.*?)</think>"
            match = re.search(think_pattern, content, re.DOTALL)
            if match:
                reasoning_content = match.group(1).strip()
                final_answer = re.sub(think_pattern, "", content, flags=re.DOTALL).strip()
                logger.debug(
                    f"🧠 think 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자"
                )
                return (True, reasoning_content, final_answer)

        # reasoning 태그
        reasoning_tag_pattern = r"<reasoning>(.*?)</reasoning>"
        match = re.search(reasoning_tag_pattern, content, re.DOTALL)
        if match:
            reasoning_content = match.group(1).strip()
            final_answer = re.sub(reasoning_tag_pattern, "", content, flags=re.DOTALL).strip()
            logger.debug(
                f"🧠 reasoning 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자"
            )
            return (True, reasoning_content, final_answer)

        # <thinking> 태그
        thinking_tag_pattern = r"<thinking>(.*?)</thinking>"
        match = re.search(thinking_tag_pattern, content, re.DOTALL)
        if match:
            reasoning_content = match.group(1).strip()
            final_answer = re.sub(thinking_tag_pattern, "", content, flags=re.DOTALL).strip()
            logger.debug(
                f"🧠 thinking 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자"
            )
            return (True, reasoning_content, final_answer)

        # <thought> 태그
        thought_tag_pattern = r"<thought>(.*?)</thought>"
        match = re.search(thought_tag_pattern, content, re.DOTALL)
        if match:
            reasoning_content = match.group(1).strip()
            final_answer = re.sub(thought_tag_pattern, "", content, flags=re.DOTALL).strip()
            logger.debug(
                f"🧠 thought 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자"
            )
            return (True, reasoning_content, final_answer)

        # <analysis> 태그
        analysis_tag_pattern = r"<analysis>(.*?)</analysis>"
        match = re.search(analysis_tag_pattern, content, re.DOTALL)
        if match:
            reasoning_content = match.group(1).strip()
            final_answer = re.sub(analysis_tag_pattern, "", content, flags=re.DOTALL).strip()
            logger.debug(
                f"🧠 analysis 태그 감지: 추론 {len(reasoning_content)}자, 답변 {len(final_answer)}자"
            )
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
                    logger.debug(
                        "🧠 휴리스틱 마커 감지: 추론 %s자, 답변 %s자",
                        len(reasoning_content),
                        len(final_answer),
                    )
                    return (True, reasoning_content, final_answer)
        except Exception as e:  # pragma: no cover
            logger.debug("휴리스틱 파싱 오류: %s", e)

        logger.debug(f"🧠 추론 과정 없음: 일반 응답 {len(content)}자")
        return (False, "", content)

    @staticmethod
    def _parse_partial_reasoning(content: str) -> tuple[bool, str, str]:
        """
        스트리밍 중 부분적 추론 과정 파싱
        닫히지 않은 태그도 감지하여 실시간 추론 과정 표시
        """
        # 1. 열린 <think> 태그 감지 (아직 닫히지 않음)
        if "<think>" in content and "</think>" not in content:
            think_start = content.find("<think>")
            if think_start != -1:
                reasoning_content = content[think_start + 7 :].strip()  # "<think>" 길이 = 7
                if reasoning_content:  # 추론 내용이 있으면
                    logger.debug(
                        f"🧠 부분적 think 태그 감지: 추론 {len(reasoning_content)}자 (진행중)"
                    )
                    return (True, reasoning_content, "")  # 아직 최종 답변 없음

        # 2. 열린 <thinking> 태그 감지
        if "<thinking>" in content and "</thinking>" not in content:
            thinking_start = content.find("<thinking>")
            if thinking_start != -1:
                reasoning_content = content[thinking_start + 10 :].strip()  # "<thinking>" 길이 = 10
                if reasoning_content:
                    logger.debug(
                        f"🧠 부분적 thinking 태그 감지: 추론 {len(reasoning_content)}자 (진행중)"
                    )
                    return (True, reasoning_content, "")

        # 3. 열린 <reasoning> 태그 감지
        if "<reasoning>" in content and "</reasoning>" not in content:
            reasoning_start = content.find("<reasoning>")
            if reasoning_start != -1:
                reasoning_content = content[
                    reasoning_start + 11 :
                ].strip()  # "<reasoning>" 길이 = 11
                if reasoning_content:
                    logger.debug(
                        f"🧠 부분적 reasoning 태그 감지: 추론 {len(reasoning_content)}자 (진행중)"
                    )
                    return (True, reasoning_content, "")

        # 4. 열린 <thought> 태그 감지
        if "<thought>" in content and "</thought>" not in content:
            thought_start = content.find("<thought>")
            if thought_start != -1:
                reasoning_content = content[thought_start + 9 :].strip()  # "<thought>" 길이 = 9
                if reasoning_content:
                    logger.debug(
                        f"🧠 부분적 thought 태그 감지: 추론 {len(reasoning_content)}자 (진행중)"
                    )
                    return (True, reasoning_content, "")

        # 5. 열린 <analysis> 태그 감지
        if "<analysis>" in content and "</analysis>" not in content:
            analysis_start = content.find("<analysis>")
            if analysis_start != -1:
                reasoning_content = content[analysis_start + 10 :].strip()  # "<analysis>" 길이 = 10
                if reasoning_content:
                    logger.debug(
                        f"🧠 부분적 analysis 태그 감지: 추론 {len(reasoning_content)}자 (진행중)"
                    )
                    return (True, reasoning_content, "")

        # 6. 추론 마커 기반 감지 (태그 없이도)
        reasoning_markers = [
            "let me think",
            "thinking about",
            "i need to consider",
            "분석해보면",
            "생각해보니",
            "추론해보면",
            "고려해야",
            "판단해보면",
        ]

        content_lower = content.lower()
        for marker in reasoning_markers:
            if marker in content_lower:
                # 마커 이후의 내용을 추론 과정으로 간주
                marker_pos = content_lower.find(marker)
                reasoning_content = content[marker_pos:].strip()
                if len(reasoning_content) > 20:  # 충분한 내용이 있을 때만
                    logger.debug(
                        f"🧠 추론 마커 감지: '{marker}', 추론 {len(reasoning_content)}자 (진행중)"
                    )
                    return (True, reasoning_content, "")

        return (False, "", "")
