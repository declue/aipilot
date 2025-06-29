#!/usr/bin/env python3
"""
DSPilot CLI 응답 생성 서비스 (ResponseGenerator)
==============================================

`ResponseGenerator` 는 **단계별 실행 결과**를 기반으로 LLM 에 **최종 분석 프롬프트**를
보내고 사용자에게 전달할 응답을 생성합니다. 또한 스트리밍 모드를 지원하여
토큰 단위 출력이 가능합니다.

동작 흐름
---------
```mermaid
flowchart TD
    A[StepResults] --> RG(ResponseGenerator)
    RG -->|results_summary| LLM
    LLM -->|analysis| RG
    RG --> OM[OutputManager]
    OM --> User
```

주요 기능
---------
1. _create_results_summary(): 단계 결과를 요약
2. generate_final_response(): LLM 호출 후 응답 출력
   • 스트리밍 모드 지원 (start_streaming_output / finish_streaming_output)
3. 폴백 처리: 프롬프트 로드 실패 또는 LLM 호출 실패 시 최소 결과 출력

사용 예시
---------
```python
rg = ResponseGenerator(output_manager, llm_agent)
await rg.generate_final_response(prompt, step_results)
```

테스트 전략
-----------
- `step_results` 에 다양한 크기의 결과를 넣어 요약 길이 제한을 검증
- LLM 호출을 mock 하여 streaming/non-streaming 두 모드 테스트
- 프롬프트 로드 실패 상황을 simulate 하여 `_output_fallback_response` 호출 확인
"""

from typing import Any, Callable, Dict, Optional

import dspilot_core.instructions.prompt_manager as prompt_manager
from dspilot_cli.constants import Defaults, PromptNames
from dspilot_cli.output_manager import OutputManager
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.models.conversation_message import ConversationMessage


class ResponseGenerator:
    """최종 응답 생성을 담당하는 서비스"""

    def __init__(self, output_manager: OutputManager,
                 llm_agent: BaseAgent) -> None:
        """
        응답 생성자 초기화

        Args:
            output_manager: 출력 관리자
            llm_agent: LLM 에이전트
        """
        self.output_manager = output_manager
        self.llm_agent = llm_agent
        self.prompt_manager = prompt_manager.get_default_prompt_manager()

    async def generate_final_response(self,
                                      original_prompt: str,
                                      step_results: Dict[int, Any],
                                      streaming_callback: Optional[Callable[[str], None]] = None) -> None:
        """
        최종 응답 생성

        Args:
            original_prompt: 원본 프롬프트
            step_results: 단계 실행 결과들
            streaming_callback: 스트리밍 콜백 함수
        """
        if not step_results:
            return

        # 결과 요약
        results_summary = self._create_results_summary(step_results)

        # 최종 분석 프롬프트 (파일에서 로드)
        final_prompt = self.prompt_manager.get_formatted_prompt(
            PromptNames.FINAL_ANALYSIS,
            original_prompt=original_prompt,
            results_summary=results_summary
        )

        if final_prompt is None:
            self.output_manager.log_if_debug("최종 분석 프롬프트 로드 실패", "error")
            final_prompt = self._create_fallback_prompt(original_prompt, results_summary)

        try:
            context = [ConversationMessage(role="user", content=final_prompt)]

            # 스트리밍 모드인 경우 콜백과 함께 응답 생성
            if streaming_callback:
                self.output_manager.start_streaming_output()
                response = await self.llm_agent.llm_service.generate_response(context, streaming_callback)
                self.output_manager.finish_streaming_output()
            else:
                response = await self.llm_agent.llm_service.generate_response(context)

            response_data = {
                "response": response.response,
                "used_tools": list(step_results.keys()),
                "step_results": step_results
            }

            # 스트리밍 모드가 아닌 경우에만 응답 출력 (스트리밍 모드에서는 이미 출력됨)
            if not streaming_callback:
                self.output_manager.print_response(
                    response.response,
                    response_data.get("used_tools", [])
                )

        except Exception as e:
            self.output_manager.log_if_debug(f"최종 응답 생성 실패: {e}", "error")
            # 폴백: 원시 결과 출력
            self._output_fallback_response(results_summary)

    def _create_results_summary(self, step_results: Dict[int, Any]) -> str:
        """단계 결과들을 요약하여 문자열로 생성"""
        return "\n".join([
            f"단계 {step}: {str(result)[:Defaults.RESULT_SUMMARY_MAX_LENGTH]}..."
            if len(str(result)) > Defaults.RESULT_SUMMARY_MAX_LENGTH
            else f"단계 {step}: {result}"
            for step, result in step_results.items()
        ])

    def _create_fallback_prompt(self, original_prompt: str, results_summary: str) -> str:
        """프롬프트 로드 실패 시 사용할 폴백 프롬프트 생성"""
        return (f"원래 요청: {original_prompt}\n\n"
                f"실행 결과:\n{results_summary}\n\n"
                f"위 결과를 바탕으로 최종 답변을 제공해주세요.")

    def _output_fallback_response(self, results_summary: str) -> None:
        """응답 생성 실패 시 폴백 출력"""
        self.output_manager.print_success("작업 완료")
        self.output_manager.print_info(f"결과: {results_summary}")
