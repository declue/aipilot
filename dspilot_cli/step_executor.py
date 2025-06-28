#!/usr/bin/env python3
"""
DSPilot CLI 단계 실행 서비스
"""

import json
from typing import Any, Dict

from dspilot_cli.constants import Defaults, ExecutionStep, UserChoiceType
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager


class StepExecutor:
    """단일 단계 실행 및 검증을 담당하는 서비스"""

    def __init__(self, output_manager: OutputManager,
                 interaction_manager: InteractionManager,
                 llm_agent: BaseAgent,
                 mcp_tool_manager: MCPToolManager,
                 max_step_retries: int = Defaults.MAX_STEP_RETRIES,
                 validate_mode: str = Defaults.VALIDATE_MODE) -> None:
        """
        단계 실행자 초기화

        Args:
            output_manager: 출력 관리자
            interaction_manager: 상호작용 관리자
            llm_agent: LLM 에이전트
            mcp_tool_manager: MCP 도구 관리자
            max_step_retries: 최대 단계 재시도 횟수
            validate_mode: 결과 검증 모드
        """
        self.output_manager = output_manager
        self.interaction_manager = interaction_manager
        self.llm_agent = llm_agent
        self.mcp_tool_manager = mcp_tool_manager
        self.max_step_retries = max_step_retries

        # 결과 검증기 초기화
        self._initialize_validators(validate_mode)

    def _initialize_validators(self, validate_mode: str) -> None:
        """검증기 초기화 (Private Method - SRP 준수)"""
        try:
            from dspilot_core.llm.utils.argument_fixer import (
                GenericArgumentFixer,  # pylint: disable=import-error
            )
            from dspilot_core.llm.utils.result_validator import (
                GenericResultValidator,  # pylint: disable=import-error
            )
            self.result_validator = GenericResultValidator(
                llm_service=self.llm_agent.llm_service,
                mode=validate_mode
            )
            self.argument_fixer = GenericArgumentFixer(
                self.llm_agent.llm_service)
        except Exception:  # noqa: broad-except
            self.result_validator = None
            self.argument_fixer = None

    async def execute_step(self, step: ExecutionStep,
                           step_results: Dict[int, Any],
                           original_prompt: str) -> bool:
        """
        단일 단계 실행

        Args:
            step: 실행 단계
            step_results: 이전 단계 결과들
            original_prompt: 원본 프롬프트

        Returns:
            계속 진행 여부
        """
        self.output_manager.print_step_info(step.step, step.description)

        # 사용자 확인 (full-auto 모드가 아닌 경우)
        user_choice = self.interaction_manager.get_user_confirmation(
            step.confirm_message, step.tool_name, step.arguments
        )

        if user_choice == UserChoiceType.SKIP:
            self.output_manager.print_step_skipped(step.step)
            return True
        elif user_choice == UserChoiceType.MODIFY:
            # 사용자가 수정을 원하는 경우
            new_prompt = self.interaction_manager.get_new_request()
            if new_prompt:
                # 새로운 요청으로 처리 (이것은 외부에서 처리해야 함)
                # 여기서는 단순히 실행을 중단
                return False
        elif user_choice == UserChoiceType.CANCEL:
            self.output_manager.print_task_cancelled()
            return False

        # 도구 실행
        try:
            retries = 0
            while retries <= self.max_step_retries:
                self.output_manager.print_step_execution(step.tool_name)

                # 이전 단계 결과 참조 처리
                processed_args = self._process_step_arguments(
                    step.arguments, step_results)

                # 디버깅: 원본 vs 처리된 매개변수 비교
                self.output_manager.log_if_debug(f"🔍 원본 매개변수: {step.arguments}")
                self.output_manager.log_if_debug(f"🔍 처리된 매개변수: {processed_args}")

                # 디버깅: 도구 호출 전 정보
                self.output_manager.log_if_debug(f"🔍 호출할 도구: {step.tool_name}")
                self.output_manager.log_if_debug(f"🔍 도구 매개변수: {processed_args}")

                # 도구 실행
                try:
                    result = await self.mcp_tool_manager.call_mcp_tool(step.tool_name, processed_args)
                    # 디버깅: 결과 타입과 내용 로깅
                    self.output_manager.log_if_debug(f"🔍 도구 실행 결과 타입: {type(result)}")
                    self.output_manager.log_if_debug(f"🔍 도구 실행 결과: {str(result)[:200]}...")
                    exec_error = ""
                except Exception as exec_e:
                    exec_error = str(exec_e)
                    self.output_manager.log_if_debug(f"🔍 도구 실행 예외: {exec_error}")
                    result = json.dumps({"error": exec_error})

                # 결과 검증 (옵션)
                needs_retry = False
                if self.result_validator:
                    eval_res = await self.result_validator.evaluate(
                        user_prompt=original_prompt,
                        tool_name=step.tool_name,
                        tool_args=processed_args,
                        raw_result=result
                    )
                    needs_retry = self.result_validator.needs_retry(eval_res)

                    # ------------------------------------------------------------------
                    # LLM 검증 결과를 해석할 수 없을 때(parse_error 등) -----------------
                    # ------------------------------------------------------------------
                    # LLM 응답 파싱이 실패하면 eval_res["note"] == "parse_error" 로 세팅된다.
                    # 이 경우 결과가 크게 문제 없어 보이고(exec_error 비어 있음) 동일한 재시도는
                    # 의미가 없을 수 있다. 반복을 최소화하기 위해, 파싱 실패이면서 실행 오류가
                    # 없으면 성공으로 간주한다.
                    if eval_res.get("note") == "parse_error" and not exec_error:
                        self.output_manager.print_warning("⚠️ LLM 검증 파싱 실패 → 실행 성공으로 간주")
                        needs_retry = False

                    # ------------------------------------------------------------------
                    # 범용적인 성공 판단 로직 (메타데이터 기반) ---------------------------
                    # ------------------------------------------------------------------
                    # 도구 실행이 성공적으로 완료되었지만 데이터가 비어있는 경우 처리
                    if not exec_error and self._is_tool_execution_successful(result, step.tool_name):
                        self.output_manager.print_success("✅ 도구 실행 완료 → 성공으로 간주")
                        needs_retry = False

                    if needs_retry:
                        self.output_manager.print_warning(
                            f"⚠️ 결과 신뢰도 낮음 → 재시도 {retries + 1}/{self.max_step_retries}")

                # 실행 예외가 있었으면 무조건 retry
                if exec_error:
                    needs_retry = True

                if not needs_retry:
                    step_results[step.step] = result
                    self.output_manager.print_step_completed(step.step)
                    return True

                retries += 1

                # 동일한 오류 메시지가 반복될 경우 조기 중단 ------------------------
                if retries > 1 and exec_error and exec_error == step_results.get(f"_last_error_{step.step}"):
                    self.output_manager.print_warning("⚠️ 동일 오류 반복 → 추가 재시도 중단")
                    return False

                # 오류 메시지 기록
                if exec_error:
                    step_results[f"_last_error_{step.step}"] = exec_error

                # 매개변수 수정 시도
                if self.argument_fixer:
                    fixed = await self.argument_fixer.suggest(
                        user_prompt=original_prompt,
                        tool_name=step.tool_name,
                        original_args=processed_args,
                        error_msg=exec_error or "low_confidence_result"
                    )
                    if fixed:
                        processed_args.update(fixed)
                        self.output_manager.print_info(
                            f"🔧 파라미터 자동 수정 적용: {fixed}")
                        continue

            # 재시도 모두 실패 → 오류 처리
            self.output_manager.print_step_error(step.step, "결과 검증 실패")
            return False
        except Exception as e:
            error_msg = str(e)
            self.output_manager.print_step_error(step.step, error_msg)
            return False

    def _process_step_arguments(self,
                                arguments: Dict[str, Any],
                                step_results: Dict[int, Any]) -> Dict[str, Any]:
        """
        단계 매개변수 처리 (이전 단계 결과 참조)

        Args:
            arguments: 원본 매개변수
            step_results: 이전 단계 결과들

        Returns:
            처리된 매개변수
        """
        processed = {}

        # 미리 문자열 치환용 매핑 생성 -------------------------------------------
        placeholder_map = {}
        for s_num, s_val in step_results.items():
            placeholder_map[f"step_{s_num}"] = s_val
            placeholder_map[f"step{s_num}"] = s_val
            placeholder_map[f"step{s_num}_result"] = s_val
            placeholder_map[f"step_{s_num}_result"] = s_val
            # 더 많은 패턴 지원
            placeholder_map[f"{{step{s_num}}}"] = s_val
            placeholder_map[f"{{step_{s_num}}}"] = s_val
            placeholder_map[f"{{step{s_num}_result}}"] = s_val
            placeholder_map[f"{{step_{s_num}_result}}"] = s_val

        for key, value in arguments.items():
            if isinstance(value, str) and "$step_" in value:
                # 문자열 내부에 $step_N 참조가 포함된 경우 (startswith 조건 제거)
                processed_value = value
                import re

                # $step_N 패턴 찾기 (단어 경계 고려하되 _ 뒤의 다른 문자는 허용)
                step_pattern = r'\$step_(\d+)(?![a-zA-Z0-9])'
                matches = re.finditer(step_pattern, processed_value)

                # 뒤에서부터 치환 (인덱스 변화 방지)
                matches_list = list(matches)
                for match in reversed(matches_list):
                    step_num = int(match.group(1))
                    if step_num in step_results:
                        # 컨텍스트에 따라 적절한 내용 추출
                        if key == "path":
                            # 파일명인 경우: 날짜 형식 우선
                            replacement = self._extract_content_by_context(step_results[step_num], "filename")
                        else:
                            # 내용인 경우: 실제 생성된 콘텐츠 우선
                            replacement = self._extract_content_by_context(step_results[step_num], "content")

                        processed_value = processed_value[:match.start()] + replacement + processed_value[match.end():]

                processed[key] = processed_value
            else:
                # 문자열 내부 {stepX} 플레이스홀더 치환 지원
                if isinstance(value, str) and "{step" in value:
                    def _replace(match):  # noqa: D401
                        return placeholder_map.get(match.group(0), match.group(0))

                    import re

                    # 더 포괄적인 치환
                    processed_value = value
                    for placeholder, replacement in placeholder_map.items():
                        if placeholder in processed_value:
                            processed_value = processed_value.replace(placeholder, str(replacement))
                    processed[key] = processed_value
                elif isinstance(value, str) and ("<" in value and ">" in value):
                    # 의미적 플레이스홀더 치환 (<오늘날짜>, <생성된_뉴스_콘텐츠> 등)
                    import re
                    processed_value = value

                    # 각 단계 결과를 적절히 처리하여 치환
                    for step_num, step_result in step_results.items():
                        if f"<step{step_num}>" in processed_value:
                            context = "filename" if key == "path" else "content"
                            replacement = self._extract_content_by_context(step_result, context)
                            processed_value = processed_value.replace(f"<step{step_num}>", replacement)

                        # 의미적 플레이스홀더들
                        if step_num == 1 and "<오늘날짜>" in processed_value:
                            context = "filename" if key == "path" else "content"
                            replacement = self._extract_content_by_context(step_result, context)
                            processed_value = processed_value.replace("<오늘날짜>", replacement)

                        if step_num == 2 and "<생성된_뉴스_콘텐츠>" in processed_value:
                            context = "filename" if key == "path" else "content"
                            replacement = self._extract_content_by_context(step_result, context)
                            processed_value = processed_value.replace("<생성된_뉴스_콘텐츠>", replacement)

                    # 일반적인 <stepX> 패턴도 지원
                    for step_num, step_result in step_results.items():
                        patterns = [
                            f"<step_{step_num}>",
                            f"<step{step_num}_result>",
                            f"<step_{step_num}_result>"
                        ]
                        for pattern in patterns:
                            if pattern in processed_value:
                                context = "filename" if key == "path" else "content"
                                replacement = self._extract_content_by_context(step_result, context)
                                processed_value = processed_value.replace(pattern, replacement)

                    processed[key] = processed_value
                else:
                    processed[key] = value

        return processed

    def _extract_content_by_context(self, data: Dict[str, Any], context: str) -> str:
        """
        컨텍스트에 따라 적절한 콘텐츠를 추출합니다.
        """
        if context == "filename" or "filename" in context.lower():
            # 파일명 컨텍스트: 날짜 정보 우선
            if "iso_date" in data:
                return data["iso_date"]
            elif "date" in data:
                return data["date"]
            elif "result" in data and self._contains_date_info(str(data["result"])):
                return self._extract_date_from_text(str(data["result"]))

        elif context == "content" or "content" in context.lower():
            # 콘텐츠 컨텍스트: 실제 데이터 우선, 검색 결과가 비어있으면 대체 콘텐츠 생성
            if self._is_empty_or_useless_content(data):
                return self._generate_fallback_content(data)

            # 검색 결과에서 의미있는 콘텐츠 추출
            if "results" in data and isinstance(data["results"], list) and len(data["results"]) > 0:
                # 검색 결과가 있는 경우: 결과 내용 반환
                results_summary = []
                for i, result in enumerate(data["results"][:3], 1):  # 최대 3개
                    if isinstance(result, dict):
                        title = result.get("title", f"뉴스 {i}")
                        snippet = result.get("snippet", result.get("description", ""))
                        url = result.get("url", "")
                        results_summary.append(f"## {title}\n\n{snippet}\n\n출처: {url}")

                if results_summary:
                    return "\n\n".join(results_summary)

            # 다른 유용한 정보가 있는지 확인
            return self._extract_meaningful_content_from_dict(data)

        # 기본 처리
        return self._extract_meaningful_content_from_dict(data)

    def _extract_meaningful_content_from_dict(self, data: Dict[str, Any]) -> str:
        """
        딕셔너리에서 의미 있는 내용을 추출합니다.
        우선순위: content > message > result > data > 기타
        """
        # 직접적인 콘텐츠 필드들
        for field in ["content", "message", "text", "description"]:
            if field in data and data[field]:
                return str(data[field])

        # result 필드 처리
        if "result" in data:
            result_val = data["result"]
            if isinstance(result_val, dict):
                # 중첩된 딕셔너리에서 재귀적으로 추출
                nested_content = self._extract_meaningful_content_from_dict(result_val)
                if nested_content and not self._is_empty_or_useless_content(nested_content, result_val):
                    return nested_content
            elif isinstance(result_val, list) and result_val:
                # 리스트의 첫 번째 요소 처리
                if isinstance(result_val[0], dict):
                    return self._extract_meaningful_content_from_dict(result_val[0])
                else:
                    return str(result_val[0])
            else:
                return str(result_val)

        # data 필드 처리
        if "data" in data:
            data_val = data["data"]
            if isinstance(data_val, dict):
                return self._extract_meaningful_content_from_dict(data_val)
            else:
                return str(data_val)

        # 기타 필드들
        for key, value in data.items():
            if key not in ["count", "total_content_chars", "region", "query"] and value:
                if isinstance(value, (str, int, float)):
                    return str(value)

        # 마지막 수단: 전체 딕셔너리 JSON 변환
        import json
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _is_empty_or_useless_content(self, data: Dict[str, Any]) -> bool:
        """
        콘텐츠가 비어있거나 유용하지 않은지 판단합니다.
        """
        if not data or not data.values():
            return True

        # 검색 결과가 비어있는 경우 감지
        if isinstance(data, dict):
            # 검색 관련 메타데이터 확인
            if "count" in data and data["count"] == 0:
                return True
            if "results" in data and not data["results"]:
                return True
            if "total_content_chars" in data and data["total_content_chars"] == 0:
                return True

        # 의미없는 콘텐츠 패턴
        useless_patterns = [
            "{}",
            "[]",
            "null",
            "none",
            "empty",
            "no results",
            "검색 결과가 없습니다"
        ]

        content_lower = str(data).lower().strip()
        return any(pattern in content_lower for pattern in useless_patterns)

    def _generate_fallback_content(self, data: Dict[str, Any]) -> str:
        """
        검색 결과가 비어있을 때 대체 콘텐츠를 생성합니다.
        """
        # 검색 쿼리 추출
        query = data.get("query", "정보")

        # 현재 날짜 정보 추출 (다른 단계에서 가져올 수 있음)
        import datetime
        today = datetime.date.today()
        date_str = today.strftime("%Y년 %m월 %d일")

        # 검색 범위 확장 제안
        time_period = data.get("time_period", "day")
        expanded_period = self._suggest_expanded_time_period(time_period)

        # 대체 콘텐츠 생성
        fallback_content = f"""# {date_str} IT 뉴스 요약

## 검색 결과 안내

안타깝게도 '{query}' 관련하여 **{time_period}** 범위에서 최신 뉴스를 찾을 수 없었습니다.

이는 다음과 같은 이유일 수 있습니다:
- 검색 시점에 새로운 뉴스가 아직 발행되지 않았을 수 있습니다
- 검색 조건이 너무 구체적이어서 결과가 제한되었을 수 있습니다
- IT 전문 미디어의 업데이트 주기와 맞지 않을 수 있습니다

## 제안사항

1. **검색 범위 확장**: 검색 기간을 '{time_period}'에서 '{expanded_period}'로 확장
2. **키워드 조정**: 더 일반적인 IT 관련 키워드로 재검색
3. **다른 소스 활용**: 다양한 IT 전문 미디어 소스 활용

더 나은 결과를 위해 검색 조건을 조정하여 다시 시도해보시기 바랍니다.

## 추천 검색 키워드

다음 키워드들로 재검색을 시도해보세요:
- "인공지능 AI 최신 동향"
- "클라우드 컴퓨팅 기술 뉴스"
- "사이버보안 보안 기술"
- "메타버스 VR AR 기술"
- "블록체인 암호화폐 동향"

---
*이 문서는 {date_str}에 자동 생성되었습니다.*
"""

        return fallback_content

    def _suggest_expanded_time_period(self, current_period: str) -> str:
        """
        현재 검색 기간을 기반으로 확장된 검색 기간을 제안합니다.
        """
        period_expansion = {
            "day": "week",
            "week": "month",
            "month": "3months",
            "3months": "year"
        }

        return period_expansion.get(current_period, "week")

    def _contains_date_info(self, text: str) -> bool:
        """텍스트에 날짜 정보가 포함되어 있는지 확인합니다."""
        if not isinstance(text, str):
            return False
        return "2025" in text or "년" in text or "월" in text or "일" in text

    def _extract_date_from_text(self, text: str) -> str:
        """텍스트에서 날짜 정보를 추출합니다."""
        import re

        # "2025년 6월 29일" 형식 추출
        date_match = re.search(r'2025년\s*(\d+)월\s*(\d+)일', text)
        if date_match:
            month = date_match.group(1).zfill(2)
            day = date_match.group(2).zfill(2)
            return f"2025-{month}-{day}"

        # ISO 날짜 형식 추출
        iso_match = re.search(r'2025-\d{2}-\d{2}', text)
        if iso_match:
            return iso_match.group(0)

        # 기본값 반환
        return text

    def _is_tool_execution_successful(self, result: Any, tool_name: str) -> bool:
        """
        도구 실행이 성공적으로 완료되었는지 범용적으로 판단합니다.
        메타데이터 기반으로 성공 여부를 결정하며, 특정 도구에 의존하지 않습니다.
        
        Args:
            result: 도구 실행 결과
            tool_name: 도구 이름 (참고용)

        Returns:
            도구 실행이 성공적으로 완료되었는지 여부
        """
        try:
            # 문자열 결과 처리
            if isinstance(result, str):
                # JSON 파싱 시도
                try:
                    import json
                    parsed_result = json.loads(result)
                    return self._evaluate_result_success(parsed_result)
                except json.JSONDecodeError:
                    # JSON이 아닌 경우 텍스트 분석
                    return self._analyze_text_result(result)

            # 딕셔너리 결과 처리
            elif isinstance(result, dict):
                return self._evaluate_result_success(result)

            # 기타 타입은 존재하면 성공으로 간주
            else:
                return result is not None

        except Exception:
            # 예외 발생 시 실패로 간주
            return False

    def _evaluate_result_success(self, data: Dict[str, Any]) -> bool:
        """
        딕셔너리 형태의 결과에서 성공 여부를 판단합니다.
        """
        # 명시적인 성공 플래그 확인
        if "success" in data:
            return bool(data["success"])

        # 오류 필드 확인
        if "error" in data and data["error"]:
            return False

        # 검색 결과의 경우: 검색이 완료되었으면 성공 (결과가 비어있어도)
        if "query" in data and "count" in data:
            # 검색 쿼리가 있고 count 필드가 있으면 검색이 완료된 것으로 간주
            return True

        # 파일 작업 결과의 경우
        if "path" in data or "message" in data:
            return True

        # 날짜/시간 정보가 있으면 성공
        if any(key in data for key in ["date", "iso_date", "result"]):
            return True

        # 기본적으로 데이터가 있으면 성공
        return bool(data)

    def _analyze_text_result(self, text: str) -> bool:
        """
        텍스트 결과를 분석하여 성공 여부를 판단합니다.
        """
        text_lower = text.lower()

        # 성공 패턴
        success_patterns = ["success", "완료", "저장", "생성", "조회"]
        if any(pattern in text_lower for pattern in success_patterns):
            return True

        # 실패 패턴
        failure_patterns = ["error", "failed", "실패", "오류"]
        if any(pattern in text_lower for pattern in failure_patterns):
            return False

        # 텍스트가 있으면 성공으로 간주
        return bool(text.strip())
