"""
DSPilot CLI 계획 수립 서비스 (PlanningService)
============================================

사용자 요청을 분석하여 **ExecutionPlan(JSON)** 으로 변환하는 컴포넌트입니다.
LangChain 호환 MCP Tool 메타데이터를 LLM 에 전달하고, 응답에서 JSON 계획을
추출·검증한 뒤 `ExecutionManager` 로 반환합니다.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import dspilot_core.instructions.prompt_manager as prompt_manager
from dspilot_app.services.models.execution_plan import ExecutionPlan, ExecutionStep
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager
from dspilot_core.llm.models.conversation_message import ConversationMessage
from dspilot_core.llm.workflow import get_workflow

logger = logging.getLogger(__name__)


class PromptNames:
    """프롬프트 파일 이름 상수"""

    ANALYSIS = "analysis_prompts"
    FINAL_ANALYSIS = "final_analysis_prompts"
    ENHANCED = "enhanced_prompts"


class PlanningService:
    """요청 분석 및 실행 계획 수립을 담당하는 서비스"""

    def __init__(self, llm_agent: BaseAgent, mcp_tool_manager: MCPToolManager) -> None:
        """
        계획 수립 서비스 초기화

        Args:
            llm_agent: LLM 에이전트
            mcp_tool_manager: MCP 도구 관리자
        """
        self.llm_agent = llm_agent
        self.mcp_tool_manager = mcp_tool_manager
        self.prompt_manager = prompt_manager.get_default_prompt_manager()

    async def analyze_request_and_plan(self, user_message: str) -> Optional[ExecutionPlan]:
        """
        요청 분석 및 실행 계획 수립

        Args:
            user_message: 사용자 메시지

        Returns:
            실행 계획 (도구가 필요하지 않거나 워크플로우로 처리된 경우 None)
        """
        try:
            # 1. 워크플로우 패턴 감지 및 분기
            workflow_result = await self._detect_and_execute_workflow(user_message)
            if workflow_result is not None:
                # 워크플로우가 직접 처리한 경우, 실행 계획 불필요
                logger.debug("워크플로우가 요청을 직접 처리했습니다.")
                return None

            # 2. 일반적인 도구 실행 계획 수립
            return await self._create_standard_execution_plan(user_message)

        except Exception as e:
            logger.warning(f"계획 수립 실패: {e}")
            return None

    async def _detect_and_execute_workflow(self, user_message: str) -> Optional[str]:
        """
        워크플로우 패턴을 감지하고 해당 워크플로우를 실행합니다.

        Args:
            user_message: 사용자 메시지

        Returns:
            워크플로우 실행 결과 (패턴이 감지되지 않으면 None)
        """
        # 코드 수정 패턴 감지
        # 1. 코드 수정 패턴 감지 및 워크플로우 실행
        if await self._is_code_modification_request(user_message):
            logger.debug("코드 수정 패턴 감지, CodeModificationWorkflow 실행")

            def streaming_callback(content: str) -> None:
                logger.debug(f"[워크플로우] {content.strip()}")

            try:
                workflow_class = get_workflow("code_mod")
                workflow = workflow_class()
                result = await workflow.run(self.llm_agent, user_message, streaming_callback)
                logger.debug(f"워크플로우 실행 완료: {result}")
                return result
            except Exception as e:
                logger.error(f"워크플로우 실행 실패: {e}")
                return None

        # 2. 리서치/검색 패턴 감지 및 워크플로우 실행
        if await self._is_research_request(user_message):
            logger.debug("리서치 패턴 감지, ResearchWorkflow 실행")

            def research_streaming_callback(content: str) -> None:
                logger.debug(f"[워크플로우] {content.strip()}")

            try:
                workflow_class = get_workflow("research")
                workflow = workflow_class()
                result = await workflow.run(self.llm_agent, user_message, research_streaming_callback)
                logger.debug(f"워크플로우 실행 완료: {result}")
                return result
            except Exception as e:
                logger.error(f"워크플로우 실행 실패: {e}")
                return None

        return None

    async def _is_code_modification_request(self, user_message: str) -> bool:
        """
        코드 수정 요청인지 판단합니다.

        Args:
            user_message: 사용자 메시지

        Returns:
            코드 수정 요청 여부
        """
        code_modification_keywords = [
            "수정", "변경", "고치", "바꾸", "개선", "리팩토링", "refactor",
            "modify", "change", "update", "fix", "edit", "파일 수정", "코드 수정",
        ]

        file_extension_keywords = [
            ".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs", ".rb", ".php",
        ]

        message_lower = user_message.lower()
        has_modification_keyword = any(keyword in message_lower for keyword in code_modification_keywords)
        has_file_reference = any(ext in message_lower for ext in file_extension_keywords)

        file_path_pattern = r"[\w\-\.\/\\]+\.\w{2,4}"
        has_file_path = bool(re.search(file_path_pattern, user_message))

        return has_modification_keyword and (has_file_reference or has_file_path)

    async def _is_research_request(self, user_message: str) -> bool:
        """
        리서치/검색 요청인지 판단합니다.

        Args:
            user_message: 사용자 메시지

        Returns:
            리서치 요청 여부
        """
        research_keywords = [
            "검색", "찾아", "알아봐", "조사", "리서치", "research", "search",
            "뉴스", "정보", "동향", "트렌드", "현황", "분석", "요약",
        ]

        comprehensive_keywords = [
            "요약해서", "정리해서", "파일로 저장", "블로그", "보고서",
            "정리된 내용", "종합", "취합",
        ]

        time_keywords = ["최신", "어제", "오늘", "이번주", "최근", "latest", "recent"]

        message_lower = user_message.lower()
        has_research_keyword = any(keyword in message_lower for keyword in research_keywords)
        has_comprehensive_keyword = any(keyword in message_lower for keyword in comprehensive_keywords)
        has_time_keyword = any(keyword in message_lower for keyword in time_keywords)

        return has_research_keyword and (has_comprehensive_keyword or has_time_keyword)

    async def _create_standard_execution_plan(self, user_message: str) -> Optional[ExecutionPlan]:
        """
        표준 실행 계획을 생성합니다.

        Args:
            user_message: 사용자 메시지

        Returns:
            실행 계획 (도구가 필요하지 않으면 None)
        """
        available_tools = await self._get_available_tools()
        if not available_tools:
            return None

        tool_lines = []
        for tool in available_tools:
            param_fields = getattr(tool, "args", None) or getattr(tool, "args_schema", None)
            param_names: List[str] = []
            if param_fields:
                try:
                    param_names = list(param_fields.__fields__.keys())
                except Exception:
                    param_names = list(param_fields.keys()) if isinstance(param_fields, dict) else []

            params_str = f"({', '.join(param_names)})" if param_names else ""
            tool_lines.append(f"- {tool.name}{params_str}: {tool.description}")

        tools_desc = "\n".join(tool_lines)

        analysis_prompt = self.prompt_manager.get_formatted_prompt(
            PromptNames.ANALYSIS, user_message=user_message, tools_desc=tools_desc
        )

        if analysis_prompt is None:
            logger.error("분석 프롬프트 로드 실패")
            return None

        context = [ConversationMessage(role="user", content=analysis_prompt)]
        response = await self.llm_agent.llm_service.generate_response(context)

        logger.debug(
            f"[LLM-RAW-PLAN] {response.response[:500].replace('\n', ' ') if isinstance(response.response, str) else str(response)[:500]}"
        )

        plan_data = self._parse_plan_response(response.response)
        if plan_data and plan_data.get("need_tools", False):
            valid_tool_names = {tool.name for tool in available_tools}
            raw_plan = plan_data.get("plan", {})
            if not raw_plan or not raw_plan.get("steps"):
                return None

            filtered_steps = [
                s for s in raw_plan.get("steps", []) if s.get("tool_name") in valid_tool_names
            ]

            if not filtered_steps:
                return None

            filtered_steps.sort(key=lambda s: s.get("step", 0))

            validated_steps = self._validate_and_fix_plan_steps(filtered_steps)
            raw_plan["steps"] = validated_steps

            execution_plan = self._create_execution_plan(raw_plan)
            if execution_plan and execution_plan.steps:
                return execution_plan

        return None

    async def _get_available_tools(self) -> List[Any]:
        """사용 가능한 도구 목록 가져오기"""
        available_tools = []
        if self.mcp_tool_manager and hasattr(self.mcp_tool_manager, "get_langchain_tools"):
            try:
                available_tools = await self.mcp_tool_manager.get_langchain_tools()
            except Exception as e:
                logger.warning(f"도구 목록 가져오기 실패: {e}")
        return available_tools

    def _parse_plan_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """응답에서 JSON 계획 파싱"""
        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                result: Dict[str, Any] = json.loads(json_str)
                return result
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _create_execution_plan(self, plan_data: Dict[str, Any]) -> ExecutionPlan:
        """
        계획 데이터로부터 ExecutionPlan 객체 생성
        """
        steps = []
        for step_data in plan_data.get("steps", []):
            step = ExecutionStep(
                step=step_data.get("step", 0),
                description=step_data.get("description", ""),
                tool_name=step_data.get("tool_name", ""),
                arguments=step_data.get("arguments", {}),
                confirm_message=step_data.get("confirm_message", ""),
            )
            steps.append(step)

        return ExecutionPlan(
            description=plan_data.get("description", "도구 실행 계획"), steps=steps
        )

    def _validate_and_fix_plan_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        계획 단계들을 검증하고 잘못된 부분을 수정합니다.
        """
        validated_steps = []

        for step in steps:
            validated_step = step.copy()
            arguments = step.get("arguments", {})

            fixed_arguments = {}
            for key, value in arguments.items():
                if isinstance(value, str) and self._is_malformed_argument_value(value):
                    fixed_value = self._fix_malformed_argument_value(value, key, step.get("step", 0))
                    logger.debug(f"🔧 계획 수정: '{value}' -> '{fixed_value}'")
                    fixed_arguments[key] = fixed_value
                else:
                    fixed_arguments[key] = value

            validated_step["arguments"] = fixed_arguments
            validated_steps.append(validated_step)

        return validated_steps

    def _is_malformed_argument_value(self, value: str) -> bool:
        """인수 값이 잘못된 형태인지 검사"""
        malformed_patterns = ["이전 단계", "앞서", "step_\\d+의", "결과를 바탕으로", "기준으로"]
        return any(re.search(pattern, value) for pattern in malformed_patterns)

    def _fix_malformed_argument_value(self, value: str, key: str, step_num: int) -> str:
        """잘못된 인수 값을 올바른 플레이스홀더로 수정"""
        step_mentions = re.findall(r"step[_\s]*(\d+)", value.lower())
        if step_mentions:
            mentioned_step = step_mentions[-1]
            return f"$step_{mentioned_step}"

        prev_step = max(1, step_num - 1)
        return f"$step_{prev_step}"
