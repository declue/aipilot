import json
import logging
from typing import Any, Dict, Optional

from dspilot_core.llm.models.conversation_message import ConversationMessage
from dspilot_core.llm.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class GenericArgumentFixer:
    """LLM 기반 도구 파라미터 자동 수정기"""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def suggest(self, user_prompt: str, tool_name: str, original_args: Dict[str, Any], error_msg: str) -> Optional[Dict[str, Any]]:
        """오류 메시지를 바탕으로 수정된 arguments 제안"""
        system_prompt = (
            "당신은 외부 도구 호출 파라미터를 수정해주는 AI 어시스턴트입니다."
            " 사용자가 시도한 파라미터로 오류가 발생했습니다."
            " 오류 내용을 참고해 잘못된 값을 수정하거나 누락된 파라미터를 추가하세요."
            " JSON 객체만 반환하세요. 예: {\"issue_number\":123}."
            " 수정이 불가능하면 빈 객체(\"{}\")를 반환하세요."
        )
        prompt = f"""
사용자 원 요청:
{user_prompt}

도구 이름: {tool_name}
원본 파라미터: {json.dumps(original_args, ensure_ascii=False)}

오류 메시지:
{error_msg}
"""
        messages = [
            ConversationMessage(role="system", content=system_prompt),
            ConversationMessage(role="user", content=prompt)
        ]
        try:
            resp = await self.llm_service.generate_response(messages)
            txt = resp.response if hasattr(resp, "response") else str(resp)
            start = txt.find("{")
            end = txt.rfind("}") + 1
            if start == -1:
                return None
            data = json.loads(txt[start:end])
            if isinstance(data, dict) and data:
                return data
        except Exception as exc:  # noqa: broad-except
            logger.warning("ArgumentFixer parsing 실패: %s", exc)
        return None 