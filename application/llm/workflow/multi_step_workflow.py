"""
다단계 처리 워크플로우
복잡한 요청을 여러 단계로 나누어 처리
"""

import logging
from typing import Any, Callable, Dict, Optional

from application.llm.workflow.base_workflow import BaseWorkflow
from application.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class MultiStepWorkflow(BaseWorkflow):
    """다단계 처리 워크플로우"""

    def __init__(self):
        self.steps = []
        self.step_results = {}

    async def run(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        다단계 워크플로우 실행

        Args:
            agent: LLM 에이전트
            message: 처리할 메시지
            streaming_callback: 스트리밍 콜백

        Returns:
            str: 처리 결과
        """
        try:
            logger.info(f"다단계 워크플로우 시작: {message[:50]}...")

            # 1단계: 작업 분해
            task_breakdown = await self._break_down_task(agent, message, streaming_callback)
            
            # 2단계: 각 하위 작업 실행
            results = await self._execute_subtasks(agent, task_breakdown, streaming_callback)
            
            # 3단계: 결과 통합
            final_result = await self._integrate_results(agent, message, results, streaming_callback)

            logger.info("다단계 워크플로우 완료")
            return final_result

        except Exception as e:
            logger.error(f"다단계 워크플로우 실행 중 오류: {e}")
            return f"다단계 워크플로우 실행 중 오류가 발생했습니다: {str(e)}"

    async def _break_down_task(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, str]:
        """작업을 하위 작업들로 분해"""
        breakdown_prompt = f"""
        다음 복잡한 요청을 논리적인 단계들로 분해해주세요:

        요청: {message}

        다음 JSON 형식으로 응답해주세요:
        {{
            "step_1": "첫 번째 단계 설명",
            "step_2": "두 번째 단계 설명",
            "step_3": "세 번째 단계 설명",
            ...
        }}

        각 단계는:
        - 독립적으로 실행 가능해야 함
        - 명확한 목적을 가져야 함
        - 순서대로 실행되어야 함
        - 3-7개 단계로 분해해주세요

        JSON 형식으로만 응답해주세요.
        """

        if streaming_callback:
            streaming_callback("🔄 작업 분해 중...\n\n")

        if hasattr(agent, "_generate_basic_response"):
            response = await agent._generate_basic_response(breakdown_prompt, streaming_callback)
        else:
            response = '{"step_1": "작업 분해 기능을 사용할 수 없습니다"}'

        # JSON 파싱 시도
        try:
            import json

            # JSON 부분만 추출
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                breakdown = json.loads(json_str)
            else:
                breakdown = {"step_1": "작업 분해 파싱에 실패했습니다"}
        except Exception as e:
            logger.warning(f"작업 분해 결과 파싱 실패: {e}")
            breakdown = {"step_1": "작업 분해 결과를 파싱할 수 없습니다"}

        logger.debug(f"작업 분해 완료: {len(breakdown)}개 단계")
        return breakdown

    async def _execute_subtasks(
        self,
        agent: Any,
        task_breakdown: Dict[str, str],
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, str]:
        """각 하위 작업을 순차적으로 실행"""
        results = {}
        
        for step_name, step_description in task_breakdown.items():
            if streaming_callback:
                streaming_callback(f"⚙️ {step_name} 실행 중...\n\n")

            # 이전 단계 결과들을 컨텍스트로 포함
            context = self._build_context(results)
            
            step_prompt = f"""
            다음 단계를 수행해주세요:

            단계: {step_name}
            설명: {step_description}

            이전 단계 결과들:
            {context}

            이 단계에서 수행해야 할 작업을 정확히 수행하고, 
            다음 단계에서 활용할 수 있는 구체적인 결과를 제공해주세요.
            """

            try:
                # MCP 도구 사용 가능한 경우 활용
                if hasattr(agent, "mcp_tool_manager") and agent.mcp_tool_manager:
                    if hasattr(agent, "generate_response"):
                        result = await agent.generate_response(step_prompt, streaming_callback)
                        step_result = result.get("response", f"{step_name} 실행 실패")
                    else:
                        step_result = await self._execute_basic_step(agent, step_prompt, streaming_callback)
                else:
                    step_result = await self._execute_basic_step(agent, step_prompt, streaming_callback)
                
                results[step_name] = step_result
                logger.debug(f"{step_name} 완료")
                
            except Exception as e:
                logger.error(f"{step_name} 실행 중 오류: {e}")
                results[step_name] = f"{step_name} 실행 중 오류 발생: {str(e)}"

        return results

    async def _execute_basic_step(
        self, agent: Any, prompt: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """기본 단계 실행"""
        if hasattr(agent, "_generate_basic_response"):
            return await agent._generate_basic_response(prompt, streaming_callback)
        else:
            return "기본 단계 실행 기능을 사용할 수 없습니다"

    def _build_context(self, results: Dict[str, str]) -> str:
        """이전 단계 결과들로 컨텍스트 구성"""
        if not results:
            return "(이전 단계 결과 없음)"
        
        context_parts = []
        for step_name, result in results.items():
            context_parts.append(f"- {step_name}: {result[:200]}...")
        
        return "\n".join(context_parts)

    async def _integrate_results(
        self,
        agent: Any,
        original_message: str,
        results: Dict[str, str],
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """결과 통합 및 최종 응답 생성"""
        integration_prompt = f"""
        원래 요청: {original_message}

        각 단계별 결과:
        {self._format_results(results)}

        위 단계별 결과들을 종합하여 원래 요청에 대한 완전하고 일관성 있는 최종 답변을 작성해주세요.

        최종 답변은:
        1. 모든 단계의 결과를 통합해야 함
        2. 원래 요청을 완전히 만족해야 함
        3. 논리적이고 일관성 있어야 함
        4. 실용적이고 유용해야 함

        전문적이고 완성도 높은 답변을 제공해주세요.
        """

        if streaming_callback:
            streaming_callback("🔧 결과 통합 중...\n\n")

        if hasattr(agent, "_generate_basic_response"):
            final_result = await agent._generate_basic_response(integration_prompt, streaming_callback)
        else:
            final_result = "결과 통합 기능을 사용할 수 없습니다"

        logger.debug("결과 통합 완료")
        return final_result

    def _format_results(self, results: Dict[str, str]) -> str:
        """결과를 포맷팅"""
        formatted_parts = []
        for step_name, result in results.items():
            formatted_parts.append(f"**{step_name}:**\n{result}\n")
        
        return "\n".join(formatted_parts) 