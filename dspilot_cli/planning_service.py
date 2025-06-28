#!/usr/bin/env python3
"""
DSPilot CLI 계획 수립 서비스
"""

import json
from typing import Any, Dict, List, Optional

import dspilot_core.instructions.prompt_manager as prompt_manager
from dspilot_cli.constants import ExecutionPlan, ExecutionStep, PromptNames
from dspilot_cli.output_manager import OutputManager
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager
from dspilot_core.llm.models.conversation_message import ConversationMessage


class PlanningService:
    """요청 분석 및 실행 계획 수립을 담당하는 서비스"""

    def __init__(self, output_manager: OutputManager,
                 llm_agent: BaseAgent,
                 mcp_tool_manager: MCPToolManager) -> None:
        """
        계획 수립 서비스 초기화

        Args:
            output_manager: 출력 관리자
            llm_agent: LLM 에이전트
            mcp_tool_manager: MCP 도구 관리자
        """
        self.output_manager = output_manager
        self.llm_agent = llm_agent
        self.mcp_tool_manager = mcp_tool_manager
        self.prompt_manager = prompt_manager.get_default_prompt_manager()

    async def analyze_request_and_plan(self, user_message: str) -> Optional[ExecutionPlan]:
        """
        요청 분석 및 실행 계획 수립

        Args:
            user_message: 사용자 메시지

        Returns:
            실행 계획 (도구가 필요하지 않으면 None)
        """
        try:
            # 사용 가능한 도구 목록 확인
            available_tools = await self._get_available_tools()
            if not available_tools:
                return None

            # 도구 목록 생성
            tools_desc = "\n".join([
                f"- {tool.name}: {tool.description}"
                for tool in available_tools
            ])

            # 계획 수립 프롬프트 (파일에서 로드)
            analysis_prompt = self.prompt_manager.get_formatted_prompt(
                PromptNames.ANALYSIS,
                user_message=user_message,
                tools_desc=tools_desc
            )

            if analysis_prompt is None:
                self.output_manager.log_if_debug("분석 프롬프트 로드 실패", "error")
                return None

            context = [ConversationMessage(
                role="user", content=analysis_prompt)]
            response = await self.llm_agent.llm_service.generate_response(context)

            # JSON 파싱
            plan_data = self._parse_plan_response(response.response)
            if plan_data and plan_data.get("need_tools", False):
                return self._create_execution_plan(plan_data.get("plan", {}))

        except Exception as e:
            self.output_manager.log_if_debug(f"계획 수립 실패: {e}", "warning")

        return None

    async def _get_available_tools(self) -> List[Any]:
        """사용 가능한 도구 목록 가져오기"""
        available_tools = []
        if self.mcp_tool_manager and hasattr(self.mcp_tool_manager, 'get_langchain_tools'):
            try:
                available_tools = await self.mcp_tool_manager.get_langchain_tools()
            except Exception as e:
                self.output_manager.log_if_debug(
                    f"도구 목록 가져오기 실패: {e}", "warning")
        return available_tools

    def _parse_plan_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """응답에서 JSON 계획 파싱"""
        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _create_execution_plan(self, plan_data: Dict[str, Any]) -> ExecutionPlan:
        """계획 데이터로부터 ExecutionPlan 객체 생성"""
        steps = []
        for step_data in plan_data.get("steps", []):
            step = ExecutionStep(
                step=step_data.get("step", 0),
                description=step_data.get("description", ""),
                tool_name=step_data.get("tool_name", ""),
                arguments=step_data.get("arguments", {}),
                confirm_message=step_data.get("confirm_message", "")
            )
            steps.append(step)

        return ExecutionPlan(
            description=plan_data.get("description", "도구 실행 계획"),
            steps=steps
        )
