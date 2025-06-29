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

    async def _get_modified_code_from_llm(self, original_code: str, user_message: str) -> str:
        """
        LLM을 호출하여 코드를 수정합니다.
        
        Args:
            original_code: 수정할 원본 코드
            user_message: 사용자의 수정 요청 메시지
            
        Returns:
            수정된 코드 문자열
        """
        self.output_manager.log_if_debug("LLM을 통해 코드 수정을 요청합니다...")
        
        # 코드 수정을 위한 별도의 프롬프트
        prompt = f"""다음은 사용자의 요청과 원본 코드입니다. 요청에 맞게 코드를 수정한 후, **다른 설명 없이 수정된 코드 전체만 반환해주세요.**

# 사용자 요청:
{user_message}

# 원본 코드:
```python
{original_code}
```

# 수정된 코드:"""

        context = [ConversationMessage(role="user", content=prompt)]
        response = await self.llm_agent.llm_service.generate_response(context)
        
        # 응답에서 코드 블록만 추출
        modified_code = response.response
        if "```" in modified_code:
            parts = modified_code.split("```")
            if len(parts) > 1:
                # ```python ... ``` 또는 ``` ... ``` 형식의 코드 블록 추출
                code_part = parts[1]
                if code_part.lower().startswith('python\n'):
                    modified_code = code_part[len('python\n'):]
                else:
                    modified_code = code_part
        
        self.output_manager.log_if_debug(f"LLM으로부터 수정된 코드 수신:\n{modified_code[:300]}...")
        return modified_code.strip()
        
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

            # 도구 목록 생성 (이름 + 설명 + 파라미터 목록 포함)
            tool_lines = []
            for tool in available_tools:
                param_fields = getattr(tool, "args", None) or getattr(tool, "args_schema", None)
                param_names: List[str] = []
                if param_fields:
                    try:
                        param_names = list(param_fields.__fields__.keys())  # type: ignore[attr-defined]
                    except Exception:
                        param_names = list(param_fields.keys()) if isinstance(param_fields, dict) else []

                params_str = f"({', '.join(param_names)})" if param_names else ""
                tool_lines.append(f"- {tool.name}{params_str}: {tool.description}")

            tools_desc = "\n".join(tool_lines)

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

            # 디버그 모드에서는 LLM 응답 원문 일부 로그
            self.output_manager.log_if_debug(
                f"[LLM-RAW-PLAN] {response.response[:500].replace('\n', ' ') if isinstance(response.response, str) else str(response)[:500]}"
            )

            # JSON 파싱
            plan_data = self._parse_plan_response(response.response)
            if plan_data and plan_data.get("need_tools", False):
                # LLM 이 목록에 없는 도구를 참조하는 경우 필터링
                valid_tool_names = {tool.name for tool in available_tools}

                raw_plan = plan_data.get("plan", {})
                if not raw_plan or not raw_plan.get("steps"):
                    return None
                    
                filtered_steps = [
                    s for s in raw_plan.get("steps", []) if s.get("tool_name") in valid_tool_names
                ]

                # 스텝이 모두 제거되면 도구 실행 불필요
                if not filtered_steps:
                    return None

                # --------------------------------------------------------------
                # 후처리: '읽기 -> 쓰기' 패턴을 감지하고, 중간에 LLM을 통해
                # 코드를 수정하는 로직을 수행합니다.
                # --------------------------------------------------------------
                if len(filtered_steps) == 2 and \
                   filtered_steps[0].get("tool_name") == "read_file" and \
                   "write" in filtered_steps[1].get("tool_name", ""):
                    
                    read_step_args = filtered_steps[0].get("arguments", {})
                    write_step_args = filtered_steps[1].get("arguments", {})
                    
                    read_path = read_step_args.get("path") or read_step_args.get("file_path")
                    write_path = write_step_args.get("path") or write_step_args.get("file_path")

                    if read_path and read_path == write_path:
                        self.output_manager.log_if_debug(f"'{read_path}' 파일 수정 패턴 감지. LLM 수정 로직을 실행합니다.")
                        
                        # 1. 파일 읽기 (동기적으로 실행)
                        try:
                            with open(read_path, 'r', encoding='utf-8') as f:
                                original_code = f.read()
                            self.output_manager.log_if_debug("파일 읽기 성공.")
                        except Exception as e:
                            self.output_manager.log_if_debug(f"파일 읽기 실패: {e}", "error")
                            return None # 파일을 읽지 못하면 계획을 진행할 수 없음

                        # 2. LLM을 통해 코드 수정
                        modified_code = await self._get_modified_code_from_llm(original_code, user_message)

                        if not modified_code or modified_code == original_code:
                            self.output_manager.log_if_debug("코드 수정이 없거나 실패했습니다.", "warning")
                            return None

                        # 3. 쓰기 단계의 'content' 인자를 수정된 코드로 교체
                        # write_file, write_file_with_content 등 content를 받는 키를 찾습니다.
                        content_key = next((k for k in write_step_args if "content" in k), "content")
                        filtered_steps[1]["arguments"][content_key] = modified_code
                        self.output_manager.log_if_debug("실행 계획의 쓰기 단계를 수정된 코드로 업데이트했습니다.")

                # --------------------------------------------------------------
                # 구조적 검사: 읽기 단계만 있고 쓰기/패치 단계가 없는 경우 보강
                # --------------------------------------------------------------
                read_step = next((s for s in filtered_steps if s.get("tool_name") == "read_file"), None)
                has_write_step = any(
                    any(k in st.get("arguments", {}) for k in ("content", "diff_content"))
                    for st in filtered_steps if st is not read_step
                )

                if read_step and not has_write_step:
                    # 읽기 스텝의 파일 경로 키 추출
                    file_arg_key = None
                    for k in ["path", "file_path"]:
                        if k in read_step.get("arguments", {}):
                            file_arg_key = k
                            break

                    target_file_path = read_step["arguments"].get(file_arg_key) if file_arg_key else None

                    if target_file_path:
                        # 쓰기 가능한 도구 탐색 (file_path + content/diff_content)
                        write_tool_name = None
                        content_key = "content"
                        for tool in available_tools:
                            param_fields = getattr(tool, "args", None) or getattr(tool, "args_schema", None)
                            param_names.clear()
                            if param_fields:
                                try:
                                    param_names = list(param_fields.__fields__.keys())  # type: ignore[attr-defined]
                                except Exception:
                                    param_names = list(param_fields.keys()) if isinstance(param_fields, dict) else []

                            if {"file_path", "content"}.issubset(param_names):
                                write_tool_name = tool.name
                                content_key = "content"
                                break
                            if {"file_path", "diff_content"}.issubset(param_names):
                                write_tool_name = tool.name
                                content_key = "diff_content"
                                break

                        if write_tool_name:
                            new_step_num = max(s["step"] for s in filtered_steps) + 1
                            filtered_steps.append(
                                {
                                    "step": new_step_num,
                                    "description": "읽어온 내용을 수정하여 파일에 반영합니다.",
                                    "tool_name": write_tool_name,
                                    "arguments": {
                                        "file_path": target_file_path,
                                        content_key: f"$step_{read_step['step']}.content"
                                    },
                                    "confirm_message": "수정된 코드를 저장할까요?"
                                }
                            )

                # 최종 스텝 배열 재정렬 (step 키 기준)
                filtered_steps.sort(key=lambda s: s.get("step", 0))
                raw_plan["steps"] = filtered_steps

                execution_plan = self._create_execution_plan(raw_plan)
                # 실행 단계가 없는 경우는 도구 실행이 불필요한 것과 동일하게 간주하여 None 반환
                if execution_plan and execution_plan.steps:
                    return execution_plan
                return None

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
                result: Dict[str, Any] = json.loads(json_str)
                return result
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
