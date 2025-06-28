import json
import logging
from typing import Any, Dict

from dspilot_core.llm.models.conversation_message import ConversationMessage
from dspilot_core.llm.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class GenericResultValidator:
    """LLM-기반 범용 도구 결과 검증기

    특정 MCP Tool 스키마에 의존하지 않고, LLM 자체 평가에 기반해 결과의 그럴듯함/완전성/오류 가능성을 확률로 반환한다.
    """

    def __init__(self, llm_service: LLMService,
                 plausible_cutoff: float = 0.4,
                 error_cutoff: float = 0.6,
                 mode: str = "auto") -> None:
        self.llm_service = llm_service
        self.plausible_cutoff = plausible_cutoff
        self.error_cutoff = error_cutoff
        self.mode = mode.lower()

    async def evaluate(self, user_prompt: str, tool_name: str, tool_args: Dict[str, Any], raw_result: str) -> Dict[str, Any]:
        """LLM 에게 결과 평가를 요청하고 파싱된 dict 반환"""
        if self.mode == "off":
            return {
                "plausible": 1.0,
                "complete": 1.0,
                "error_like": 0.0,
                "note": "validation disabled"
            }

        system_prompt = (
            "당신은 외부 도구 결과의 정확성과 완전성을 빠르게 진단하는 AI입니다."
            " 입력으로 사용자 요청, 사용된 도구 설명 및 실행 결과가 주어집니다."
            " 0~1 사이 확률로만 평가해 JSON으로 답하십시오."
            " 예시 형식: {\"plausible\":0.8,\"complete\":0.6,\"error_like\":0.1,\"note\":\"코멘트\"}."
            " 불필요한 텍스트는 절대 포함하지 마십시오." )

        def _safe_dumps(obj: Any) -> str:
            """JSON 직렬화 실패 시 문자열 변환으로 대체"""
            try:
                return json.dumps(obj, ensure_ascii=False)
            except TypeError:
                # dataclass 등 기본 직렬화 불가 객체는 str()로 변환
                return json.dumps(obj, default=str, ensure_ascii=False)

        analysis_prompt = f"""
사용자 요청:
{user_prompt}

사용된 도구: {tool_name}
입력 파라미터: {_safe_dumps(tool_args)}

도구 원시 결과:
{raw_result}
"""
        messages = [
            ConversationMessage(role="system", content=system_prompt),
            ConversationMessage(role="user", content=analysis_prompt)
        ]
        try:
            resp = await self.llm_service.generate_response(messages)
            txt = resp.response if hasattr(resp, "response") else str(resp)
            start = txt.find("{")
            end = txt.rfind("}") + 1
            data = json.loads(txt[start:end]) if start != -1 else {}
        except Exception as exc:  # noqa: broad-except
            logger.warning("Validator parsing 실패: %s", exc)
            data = {"plausible": 0.0, "complete": 0.0, "error_like": 1.0, "note": "parse_error"}
        # 필드 보정
        for key in ["plausible", "complete", "error_like"]:
            data[key] = float(data.get(key, 0.0))
        return data

    def needs_retry(self, eval_result: Dict[str, Any]) -> bool:
        if self.mode == "off":
            return False
        if self.mode == "strict":
            plausible_ok = eval_result["plausible"] >= 0.6 and eval_result["complete"] >= 0.6
            return not plausible_ok
        # auto
        return (eval_result["plausible"] < self.plausible_cutoff) or (eval_result["error_like"] > self.error_cutoff) 