"""summary_utils - 간단한 rule-based 텍스트 압축 유틸리티

ConversationManager가 토큰 초과 시 오래된 컨텍스트를 요약하기 위해 사용한다.
현재 전략:
1. 코드 블록( ``` )은 가능한 한 보존
2. 코드 블록 외 텍스트는 문장 단위 분리 후 처음 3 + 마지막 2문장 유지
3. 최종 라인 수가 max_lines를 초과하면 잘라냄
"""

from __future__ import annotations

import re
from typing import List

__all__ = ["compress_text"]


def _split_sentences(text: str) -> List[str]:
    """아주 단순한 문장 분리 (., !, ? 기준)"""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def compress_text(text: str, max_lines: int = 50) -> str:
    """텍스트를 일정 라인 이하로 압축한다.

    Args:
        text: 원본 텍스트 (줄바꿈 포함)
        max_lines: 최대 라인 수
    """

    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text

    # -------- 코드 블록 감지 --------
    code_ranges: List[tuple[int, int]] = []
    start = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("```"):
            if start is None:
                start = idx
            else:
                code_ranges.append((start, idx))
                start = None

    # 코드 라인 수집
    code_lines: List[str] = []
    for s, e in code_ranges:
        code_lines.extend(lines[s:e + 1])

    # 코드 외 텍스트 추출
    non_code_lines = [l for i, l in enumerate(
        lines) if not any(s <= i <= e for s, e in code_ranges)]
    non_code_text = "\n".join(non_code_lines)

    sentences = _split_sentences(non_code_text)

    head = sentences[:3]
    tail = sentences[-2:] if len(sentences) > 5 else []
    compressed_sentences = head + (["..."] if tail else []) + tail
    compressed_text = " ".join(compressed_sentences)

    # 최종 병합
    merged_lines = code_lines + [compressed_text]
    if len(merged_lines) > max_lines:
        merged_lines = merged_lines[:max_lines]

    return "\n".join(merged_lines)
