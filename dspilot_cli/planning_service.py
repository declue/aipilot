#!/usr/bin/env python3
"""
DSPilot CLI 계획 수립 서비스 (PlanningService)
============================================

사용자 요청을 분석하여 **ExecutionPlan(JSON)** 으로 변환하는 컴포넌트입니다.
LangChain 호환 MCP Tool 메타데이터를 LLM 에 전달하고, 응답에서 JSON 계획을
추출·검증한 뒤 `ExecutionManager` 로 반환합니다.

알고리즘 단계
-------------
1. 사용 가능한 MCP 도구 메타정보 수집 (`_get_available_tools`)
2. 분석 프롬프트 렌더링 및 LLM 호출
3. LLM 응답에서 JSON 구조 추출 (`_parse_plan_response`)
4. `need_tools` 플래그가 True 이면 `_create_execution_plan` 수행

데이터 흐름
-----------
```mermaid
sequenceDiagram
    participant EM as ExecutionManager
    participant PS as PlanningService
    participant AG as LLM Agent
    EM->>PS: analyze_request_and_plan(user_message)
    PS->>AG: analysis_prompt
    AG-->>PS: JSON (need_tools, plan)
    PS-->>EM: ExecutionPlan | None
```

확장 가이드
-----------
- 새로운 프롬프트 버전을 추가하려면 `PromptNames` 에 상수를 정의하고, 프롬프트파일을 템플릿 디렉터리에 넣으세요.
- JSON 파싱 규칙이 변경되면 `_parse_plan_response` 를 오버라이드하여 맞춤 처리 가능합니다.

테스트 전략
-----------
- 실패 케이스: LLM 이 비JSON 응답을 반환할 때 None 이 반환되는지 확인
- 성공 케이스: 미리 준비된 샘플 JSON 응답을 주입해 ExecutionPlan 객체 생성 검증
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
