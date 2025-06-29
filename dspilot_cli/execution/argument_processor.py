"""Argument processing and placeholder substitution for Step execution.

이 모듈은 StepExecutor 의 `_process_step_arguments` 및 관련 헬퍼 메서드를
SRP 에 맞게 분리한 구현체입니다.
"""
from __future__ import annotations

import datetime
import json
import re
from typing import Any, Dict

__all__ = ["ArgumentProcessor"]


class ArgumentProcessor:
    """매개변수 치환 및 콘텐츠 추출을 담당한다."""

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def process(self, arguments: Dict[str, Any], step_results: Dict[int, Any]) -> Dict[str, Any]:
        """Recursively process arguments replacing placeholders with previous step results."""
        processed: Dict[str, Any] = {}

        # 미리 문자열 치환용 매핑 생성 ---------------------------------------
        placeholder_map: Dict[str, Any] = {}
        for s_num, s_val in step_results.items():
            placeholder_map.update(
                {
                    f"step_{s_num}": s_val,
                    f"step{s_num}": s_val,
                    f"step{s_num}_result": s_val,
                    f"step_{s_num}_result": s_val,
                    # 중괄호 포함 패턴 추가
                    f"{{step{s_num}}}": s_val,
                    f"{{step_{s_num}}}": s_val,
                    f"{{step{s_num}_result}}": s_val,
                    f"{{step_{s_num}_result}}": s_val,
                }
            )

        for key, value in arguments.items():
            if isinstance(value, str) and "$step_" in value:
                processed[key] = self._substitute_dollar_step(
                    value, key, step_results)
            elif isinstance(value, str) and "{step" in value:
                processed_value = value
                for placeholder, replacement in placeholder_map.items():
                    processed_value = processed_value.replace(
                        placeholder, str(replacement))
                processed[key] = processed_value
            elif isinstance(value, str) and ("<" in value and ">" in value):
                processed[key] = self._substitute_angle_step(
                    value, key, step_results)
            else:
                processed[key] = value

        return processed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _substitute_dollar_step(self, raw: str, arg_key: str, step_results: Dict[int, Any]) -> str:
        """Handle `$step_X` style placeholders."""
        processed_value = raw
        step_pattern = r"\\$step_(\\d+)(?![a-zA-Z0-9])"

        matches_list = list(re.finditer(step_pattern, processed_value))
        for match in reversed(matches_list):
            step_num = int(match.group(1))
            if step_num in step_results:
                context = "filename" if arg_key == "path" else "content"
                replacement = self._extract_content_by_context(
                    step_results[step_num], context)
                processed_value = processed_value[: match.start(
                )] + replacement + processed_value[match.end():]
        return processed_value

    def _substitute_angle_step(self, raw: str, arg_key: str, step_results: Dict[int, Any]) -> str:
        """Handle `<stepX>` and semantic placeholders."""
        processed_value = raw
        context = "filename" if arg_key == "path" else "content"
        for step_num, step_result in step_results.items():
            processed_value = processed_value.replace(
                f"<step{step_num}>", self._extract_content_by_context(
                    step_result, context)
            )
            patterns = [
                f"<step_{step_num}>",
                f"<step{step_num}_result>",
                f"<step_{step_num}_result>",
            ]
            for pattern in patterns:
                processed_value = processed_value.replace(
                    pattern, self._extract_content_by_context(
                        step_result, context)
                )

        # 의미적 플레이스홀더 예: <오늘날짜>, <생성된_뉴스_콘텐츠>
        for step_num, step_result in step_results.items():
            if "<오늘날짜>" in processed_value and step_num == 1:
                processed_value = processed_value.replace(
                    "<오늘날짜>", self._extract_content_by_context(
                        step_result, context)
                )
            if "<생성된_뉴스_콘텐츠>" in processed_value and step_num == 2:
                processed_value = processed_value.replace(
                    "<생성된_뉴스_콘텐츠>", self._extract_content_by_context(
                        step_result, context)
                )
        return processed_value

    # ------------------------------------------------------------------
    # Content extraction helpers (moved from StepExecutor)
    # ------------------------------------------------------------------
    def _extract_content_by_context(self, data: Dict[str, Any], context: str) -> str:
        """컨텍스트에 따라 적절한 콘텐츠를 추출합니다."""
        if context.lower().startswith("filename"):
            if "iso_date" in data:
                return data["iso_date"]
            if "date" in data:
                return data["date"]
            if "result" in data and self._contains_date_info(str(data["result"])):
                return self._extract_date_from_text(str(data["result"]))

        # default to content
        if self._is_empty_or_useless_content(data):
            return self._generate_fallback_content(data)

        if "results" in data and isinstance(data["results"], list) and data["results"]:
            return self._summarize_search_results(data["results"])

        return self._extract_meaningful_content_from_dict(data)

    def _summarize_search_results(self, results: Any) -> str:
        summary = []
        for i, result in enumerate(results[:3], 1):
            if isinstance(result, dict):
                title = result.get("title", f"뉴스 {i}")
                snippet = result.get("snippet", result.get("description", ""))
                url = result.get("url", "")
                summary.append(f"## {title}\n\n{snippet}\n\n출처: {url}")
        return "\n\n".join(summary)

    def _extract_meaningful_content_from_dict(self, data: Dict[str, Any]) -> str:
        for field in ["content", "message", "text", "description"]:
            if field in data and data[field]:
                return str(data[field])

        if "result" in data:
            result_val = data["result"]
            if isinstance(result_val, dict):
                return self._extract_meaningful_content_from_dict(result_val)
            if isinstance(result_val, list) and result_val:
                return str(result_val[0]) if not isinstance(result_val[0], dict) else self._extract_meaningful_content_from_dict(result_val[0])
            return str(result_val)

        if "data" in data:
            data_val = data["data"]
            if isinstance(data_val, dict):
                return self._extract_meaningful_content_from_dict(data_val)
            return str(data_val)

        for key, value in data.items():
            if key not in ["count", "total_content_chars", "region", "query"] and value:
                if isinstance(value, (str, int, float)):
                    return str(value)

        return json.dumps(data, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Useless / fallback content helpers
    # ------------------------------------------------------------------
    def _is_empty_or_useless_content(self, data: Dict[str, Any]) -> bool:
        if not data or not data.values():
            return True

        if isinstance(data, dict):
            if data.get("count") == 0:
                return True
            if "results" in data and not data["results"]:
                return True
            if data.get("total_content_chars") == 0:
                return True

        useless_patterns = ["{}", "[]", "null", "none",
                            "empty", "no results", "검색 결과가 없습니다"]
        return any(pattern in str(data).lower() for pattern in useless_patterns)

    def _generate_fallback_content(self, data: Dict[str, Any]) -> str:
        """범용적인 실패 메시지를 생성합니다.

        특정 도구나 도메인(예: IT 뉴스)에 대한 하드코딩된 템플릿을 제거하고,
        모든 도구에서 재사용 가능한 간단한 안내 메시지를 제공합니다.
        """

        query = data.get("query", "요청")
        today = datetime.date.today().strftime("%Y-%m-%d")

        # NOTE: 도구별/도메인별 분기 로직 절대 금지(GUIDELINE.md).
        #       사용자에게 유효한 결과가 없음을 알리는 최소한의 정보를 제공한다.
        return (
            f"[{today}] '{query}' 에 대해 유효한 결과를 찾을 수 없습니다. "
            "검색 조건을 변경하거나 다시 시도해 주세요."
        )

    def _contains_date_info(self, text: str) -> bool:
        if not isinstance(text, str):
            return False
        return any(token in text for token in ["2025", "년", "월", "일"])

    def _extract_date_from_text(self, text: str) -> str:
        date_match = re.search(r"2025년\\s*(\\d+)월\\s*(\\d+)일", text)
        if date_match:
            month, day = date_match.group(1).zfill(
                2), date_match.group(2).zfill(2)
            return f"2025-{month}-{day}"
        iso_match = re.search(r"2025-\\d{2}-\\d{2}", text)
        return iso_match.group(0) if iso_match else text
