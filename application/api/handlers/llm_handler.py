"""LLM 처리 핸들러"""

from typing import Any, Dict

from application.api.handlers.base_handler import BaseHandler
from application.api.models.llm_request import LLMRequest


class LLMHandler(BaseHandler):
    """LLM 관련 API 처리를 담당하는 핸들러"""

    async def send_llm_request(self, request: LLMRequest) -> Dict[str, Any]:
        """
        LLM 요청 API
        POST /llm/request
        {
            "prompt": "사용자의 질문이나 요청"
        }
        """
        try:
            prompt = request.prompt
            self._log_request("send_llm_request", {"prompt": prompt[:50] + "..."})

            # 대화창에 사용자 메시지 추가하고 LLM 응답 요청
            self.notification_signals.trigger_llm_response.emit(prompt)

            return self._create_success_response(
                "LLM 요청이 대화창에 전송되었습니다", {"prompt": prompt}
            )

        except Exception as exception:
            return self._create_error_response("LLM 요청 처리 오류", exception)

    async def send_streaming_request(self, request: LLMRequest) -> Dict[str, Any]:
        """LLM 스트리밍 요청"""
        try:
            self._log_request("send_streaming_request", {"prompt": request.prompt[:50] + "..."})

            # 스트리밍 모드로 LLM 응답 요청
            self.notification_signals.trigger_llm_response.emit(request.prompt)

            return self._create_success_response(
                "LLM 스트리밍 요청이 전송되었습니다",
                {
                    "prompt": request.prompt,
                    "mode": "streaming",
                },
            )
        except Exception as exception:
            return self._create_error_response("LLM 스트리밍 요청 처리 오류", exception)

    # 레거시 호환성을 위한 메서드
    async def send_llm_request_legacy(self, request: LLMRequest) -> Dict[str, Any]:
        """
        [DEPRECATED] 기존 LLM API - 호환성을 위해 유지
        대신 /llm/request 엔드포인트를 사용하세요
        """
        result = await self.send_llm_request(request)
        result["deprecated"] = True
        result["message"] += " (deprecated API 사용)"
        return result
