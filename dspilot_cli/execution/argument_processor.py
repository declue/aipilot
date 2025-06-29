"""Argument processing and placeholder substitution for Step execution.

이 모듈은 StepExecutor 의 `_process_step_arguments` 및 관련 헬퍼 메서드를
SRP 에 맞게 분리한 구현체입니다.
"""
from __future__ import annotations

import datetime
import json
import re
from typing import Any, Dict, Optional

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
            elif isinstance(value, str) and self._is_malformed_placeholder(value):
                # LLM이 잘못된 설명문을 사용한 경우 자동 복구 시도
                processed[key] = self._recover_from_malformed_placeholder(
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
        step_pattern = r"\$step_(\d+)(?:\.([A-Za-z0-9_\.]+))?"

        matches_list = list(re.finditer(step_pattern, processed_value))
        for match in reversed(matches_list):
            step_num = int(match.group(1))
            path_suffix = match.group(2)  # e.g. 'result.content'

            if step_num in step_results:
                if path_suffix:
                    replacement = self._extract_by_path(step_results[step_num], path_suffix)
                    if replacement is None:
                        # fallback to generic extraction
                        replacement = self._extract_meaningful_content_from_dict(step_results[step_num])
                else:
                    replacement = self._extract_meaningful_content_from_dict(step_results[step_num])

                processed_value = (
                    processed_value[: match.start()] + str(replacement) + processed_value[match.end():]
                )
        return processed_value

    def _substitute_angle_step(self, raw: str, arg_key: str, step_results: Dict[int, Any]) -> str:
        """Handle `<stepX>` placeholders (범용적 처리)."""
        processed_value = raw
        
        for step_num, step_result in step_results.items():
            # 기본 패턴들
            patterns = [
                f"<step{step_num}>",
                f"<step_{step_num}>",
                f"<step{step_num}_result>",
                f"<step_{step_num}_result>",
            ]
            
            replacement = self._extract_meaningful_content_from_dict(step_result)
            
            for pattern in patterns:
                processed_value = processed_value.replace(pattern, replacement)
        
        return processed_value

    # ------------------------------------------------------------------
    # Malformed placeholder recovery helpers
    # ------------------------------------------------------------------
    def _is_malformed_placeholder(self, value: str) -> bool:
        """LLM이 잘못된 설명문을 사용했는지 감지 (범용적 패턴)"""
        if not isinstance(value, str):
            return False
        
        # 범용적인 설명문 패턴 감지
        malformed_patterns = [
            "이전 단계",
            "앞서",
            "위에서",
            "step_\\d+의",
            "결과를 바탕으로",
            "기준으로",
            "계산된",
            "생성된",
            "요약된"
        ]
        
        import re
        return any(re.search(pattern, value) for pattern in malformed_patterns)

    def _recover_from_malformed_placeholder(self, value: str, key: str, step_results: Dict[int, Any]) -> str:
        """잘못된 설명문을 적절한 step 결과로 복구 (범용적 로직)"""
        import re

        # 1. 단계 번호가 명시적으로 언급된 경우
        step_mentions = re.findall(r'step[_\s]*(\d+)', value.lower())
        if step_mentions:
            step_num = int(step_mentions[-1])  # 마지막에 언급된 단계 사용
            if step_num in step_results:
                return self._extract_meaningful_content_from_dict(step_results[step_num])
        
        # 2. 기본 휴리스틱: 파일명은 첫 번째 단계, 내용은 마지막 단계
        if step_results:
            if key == "path" and 1 in step_results:
                # 파일명의 경우 첫 번째 단계 결과 사용
                result = self._extract_meaningful_content_from_dict(step_results[1])
                # 확장자가 없으면 기본 확장자 추가
                if result and not '.' in result.split('/')[-1]:
                    result += ".txt"
                return result
            else:
                # 내용의 경우 마지막 단계 결과 사용
                last_step = max(step_results.keys())
                return self._extract_meaningful_content_from_dict(step_results[last_step])
        
        # 3. 복구 실패 시 원본 반환
        return value

    # ------------------------------------------------------------------
    # Content extraction helpers (moved from StepExecutor)
    # ------------------------------------------------------------------

    def _summarize_search_results(self, results: Any) -> str:
        """검색 결과를 간단히 요약"""
        if not results:
            return "검색 결과가 없습니다."
        
        summary = []
        for i, result in enumerate(results[:5], 1):
            if isinstance(result, dict):
                title = result.get("title", f"결과 {i}")
                snippet = result.get("snippet", result.get("description", ""))
                url = result.get("url", "")
                
                if snippet:
                    summary.append(f"{i}. {title}\n{snippet[:200]}...\n출처: {url}\n")
                else:
                    summary.append(f"{i}. {title}\n출처: {url}\n")
        
        return "\n".join(summary)

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

    # ------------------------------------------------------------------
    # Nested path extraction helper
    # ------------------------------------------------------------------
    def _extract_by_path(self, data: Any, path: str) -> Optional[str]:
        """점(.) 으로 구분된 경로를 따라 딕셔너리/객체에서 값을 추출한다."""
        try:
            segments = path.split('.') if path else []
            current = data
            for seg in segments:
                if isinstance(current, (str, bytes)):
                    # JSON 문자열이면 파싱 시도
                    try:
                        current = json.loads(current)
                    except Exception:
                        return None

                if isinstance(current, dict):
                    current = current.get(seg)
                else:
                    current = getattr(current, seg, None)

                if current is None:
                    return None

            # 최종 값이 딕셔너리/리스트면 문자열로 변환
            if isinstance(current, (dict, list)):
                return json.dumps(current, ensure_ascii=False)
            return str(current)
        except Exception:
            return None
