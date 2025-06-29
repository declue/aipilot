#!/usr/bin/env python3
"""
PlanningService 워크플로우 분기 테스트 케이스
===========================================

PlanningService의 워크플로우 패턴 감지 및 분기 로직을 검증하는 테스트 모듈입니다.
리팩토링된 PlanningService가 하드코딩 없이 메타데이터 기반으로 
워크플로우를 올바르게 선택하는지 확인합니다.

테스트 범위
-----------
1. 코드 수정 패턴 감지 및 CodeModificationWorkflow 실행
2. 표준 실행 계획 생성 (일반 도구 실행)
3. 워크플로우 패턴 감지 로직
4. 메타데이터 기반 패턴 매칭
5. 오류 처리 및 예외 상황
6. 워크플로우 실행 결과 처리
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from dspilot_cli.constants import ExecutionPlan, ExecutionStep
from dspilot_cli.output_manager import OutputManager
from dspilot_cli.planning_service import PlanningService
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager


class TestPlanningServiceWorkflow:
    """PlanningService 워크플로우 분기 테스트 클래스"""

    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        self.mock_output_manager = Mock(spec=OutputManager)
        self.mock_llm_agent = Mock(spec=BaseAgent)
        # llm_service 속성을 Mock으로 설정
        self.mock_llm_agent.llm_service = Mock()
        self.mock_llm_agent.llm_service.generate_response = AsyncMock()
        self.mock_mcp_tool_manager = Mock(spec=MCPToolManager)
        
        # PlanningService 인스턴스 생성
        with patch('dspilot_core.instructions.prompt_manager.get_default_prompt_manager'):
            self.planning_service = PlanningService(
                self.mock_output_manager,
                self.mock_llm_agent,
                self.mock_mcp_tool_manager
            )

    @pytest.mark.asyncio
    async def test_analyze_request_code_modification_workflow_executed(self):
        """코드 수정 패턴 감지 시 CodeModificationWorkflow 실행 테스트"""
        # Given
        user_message = "test.py 파일의 함수를 수정해주세요"
        expected_workflow_result = "파일이 성공적으로 수정되었습니다"
        
        # Mock 워크플로우 실행
        with patch.object(self.planning_service, '_detect_and_execute_workflow') as mock_detect:
            mock_detect.return_value = expected_workflow_result
            
            # When
            result = await self.planning_service.analyze_request_and_plan(user_message)
            
            # Then
            assert result is None  # 워크플로우가 직접 처리한 경우 None 반환
            mock_detect.assert_called_once_with(user_message)
            self.mock_output_manager.log_if_debug.assert_called()

    @pytest.mark.asyncio
    async def test_analyze_request_standard_execution_plan_created(self):
        """일반 요청 시 표준 실행 계획 생성 테스트"""
        # Given
        user_message = "파일 목록을 보여주세요"
        expected_execution_plan = ExecutionPlan(
            description="파일 목록 조회",
            steps=[ExecutionStep(
                step=1,
                description="파일 목록 조회",
                tool_name="list_files",
                arguments={"path": "."},
                confirm_message=""
            )]
        )
        
        # Mock 워크플로우 패턴 감지 (감지되지 않음)
        with patch.object(self.planning_service, '_detect_and_execute_workflow', return_value=None):
            # Mock 표준 실행 계획 생성
            with patch.object(self.planning_service, '_create_standard_execution_plan') as mock_create:
                mock_create.return_value = expected_execution_plan
                
                # When
                result = await self.planning_service.analyze_request_and_plan(user_message)
                
                # Then
                assert result == expected_execution_plan
                mock_create.assert_called_once_with(user_message)

    @pytest.mark.asyncio
    async def test_detect_and_execute_workflow_no_pattern_detected(self):
        """워크플로우 패턴이 감지되지 않은 경우 테스트"""
        # Given
        user_message = "안녕하세요"
        
        # Mock 패턴 감지 (모든 패턴 False)
        with patch.object(self.planning_service, '_is_code_modification_request', return_value=False):
            # When
            result = await self.planning_service._detect_and_execute_workflow(user_message)
            
            # Then
            assert result is None

    @pytest.mark.asyncio
    async def test_is_code_modification_request_positive_cases(self):
        """코드 수정 요청 감지 - 긍정적 케이스들"""
        positive_cases = [
            "test.py 파일을 수정해주세요",
            "main.js를 리팩토링해주세요", 
            "config.json 파일의 값을 변경해주세요",
            "src/app.py를 개선해주세요",
            "코드를 수정하고 싶은데 example.py에서 해주세요"
        ]
        
        for user_message in positive_cases:
            # When
            result = await self.planning_service._is_code_modification_request(user_message)
            
            # Then
            assert result is True, f"Failed for message: {user_message}"

    @pytest.mark.asyncio
    async def test_is_code_modification_request_negative_cases(self):
        """코드 수정 요청 감지 - 부정적 케이스들"""
        negative_cases = [
            "안녕하세요",
            "날씨가 어때요?",
            "파일 목록을 보여주세요",
            "현재 디렉터리는 어디인가요?",
            "도움말을 보여주세요",
            "수정이라는 단어가 있지만 파일 확장자가 없어요"
        ]
        
        for user_message in negative_cases:
            # When
            result = await self.planning_service._is_code_modification_request(user_message)
            
            # Then
            assert result is False, f"Failed for message: {user_message}"

    @pytest.mark.asyncio
    async def test_create_standard_execution_plan_success(self):
        """표준 실행 계획 생성 성공 테스트"""
        # Given
        user_message = "파일을 읽어주세요"
        
        # Mock 도구 목록
        mock_tool = Mock()
        mock_tool.name = "read_file"
        mock_tool.description = "파일을 읽습니다"
        mock_args = Mock()
        mock_args.__fields__ = {"path": Mock()}
        mock_tool.args = mock_args
        
        with patch.object(self.planning_service, '_get_available_tools', return_value=[mock_tool]):
            # Mock 프롬프트 매니저
            mock_prompt = "분석 프롬프트"
            self.planning_service.prompt_manager.get_formatted_prompt.return_value = mock_prompt
            
            # Mock LLM 응답
            mock_response = Mock()
            mock_response.response = '''
            {
                "need_tools": true,
                "plan": {
                    "description": "파일 읽기",
                    "steps": [
                        {
                            "step": 1,
                            "description": "파일 읽기",
                            "tool_name": "read_file",
                            "arguments": {"path": "test.txt"},
                            "confirm_message": ""
                        }
                    ]
                }
            }
            '''
            self.mock_llm_agent.llm_service.generate_response.return_value = mock_response
            
            # When
            result = await self.planning_service._create_standard_execution_plan(user_message)
            
            # Then
            assert result is not None
            assert isinstance(result, ExecutionPlan)
            assert len(result.steps) == 1
            assert result.steps[0].tool_name == "read_file"

    @pytest.mark.asyncio
    async def test_create_standard_execution_plan_no_tools_available(self):
        """표준 실행 계획 생성 - 사용 가능한 도구 없음"""
        # Given
        user_message = "무언가를 해주세요"
        
        with patch.object(self.planning_service, '_get_available_tools', return_value=[]):
            # When
            result = await self.planning_service._create_standard_execution_plan(user_message)
            
            # Then
            assert result is None

    @pytest.mark.asyncio
    async def test_create_standard_execution_plan_prompt_load_failure(self):
        """표준 실행 계획 생성 - 프롬프트 로드 실패"""
        # Given
        user_message = "파일을 읽어주세요"
        mock_tool = Mock()
        mock_tool.name = "read_file"
        mock_tool.description = "파일을 읽습니다"
        mock_tool.args = Mock()
        mock_tool.args.__fields__ = {}
        
        with patch.object(self.planning_service, '_get_available_tools', return_value=[mock_tool]):
            # Mock 프롬프트 로드 실패
            self.planning_service.prompt_manager.get_formatted_prompt.return_value = None
            
            # When
            result = await self.planning_service._create_standard_execution_plan(user_message)
            
            # Then
            assert result is None
            self.mock_output_manager.log_if_debug.assert_called()

    @pytest.mark.asyncio
    async def test_create_standard_execution_plan_no_need_tools(self):
        """표준 실행 계획 생성 - 도구가 필요하지 않은 경우"""
        # Given
        user_message = "안녕하세요"
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "테스트 도구"
        mock_tool.args = Mock()
        mock_tool.args.__fields__ = {}
        
        with patch.object(self.planning_service, '_get_available_tools', return_value=[mock_tool]):
            self.planning_service.prompt_manager.get_formatted_prompt.return_value = "프롬프트"
            
            # Mock LLM 응답 (도구 불필요)
            mock_response = Mock()
            mock_response.response = '''
            {
                "need_tools": false,
                "plan": null
            }
            '''
            self.mock_llm_agent.llm_service.generate_response.return_value = mock_response
            
            # When
            result = await self.planning_service._create_standard_execution_plan(user_message)
            
            # Then
            assert result is None

    @pytest.mark.asyncio
    async def test_get_available_tools_success(self):
        """사용 가능한 도구 목록 가져오기 성공 테스트"""
        # Given
        mock_tools = [Mock(), Mock()]
        self.mock_mcp_tool_manager.get_langchain_tools = AsyncMock(return_value=mock_tools)
        
        # When
        result = await self.planning_service._get_available_tools()
        
        # Then
        assert result == mock_tools
        self.mock_mcp_tool_manager.get_langchain_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_tools_failure(self):
        """사용 가능한 도구 목록 가져오기 실패 테스트"""
        # Given
        self.mock_mcp_tool_manager.get_langchain_tools = AsyncMock(side_effect=Exception("도구 로드 오류"))
        
        # When
        result = await self.planning_service._get_available_tools()
        
        # Then
        assert result == []
        self.mock_output_manager.log_if_debug.assert_called()

    def test_parse_plan_response_valid_json(self):
        """계획 응답 JSON 파싱 - 유효한 JSON"""
        # Given
        response_text = '''
        이것은 JSON 응답입니다:
        {
            "need_tools": true,
            "plan": {
                "description": "테스트 계획",
                "steps": []
            }
        }
        추가 텍스트
        '''
        
        # When
        result = self.planning_service._parse_plan_response(response_text)
        
        # Then
        assert result is not None
        assert result["need_tools"] is True
        assert result["plan"]["description"] == "테스트 계획"

    def test_parse_plan_response_invalid_json(self):
        """계획 응답 JSON 파싱 - 유효하지 않은 JSON"""
        # Given
        response_text = "이것은 JSON이 아닙니다."
        
        # When
        result = self.planning_service._parse_plan_response(response_text)
        
        # Then
        assert result is None

    def test_parse_plan_response_no_json(self):
        """계획 응답 JSON 파싱 - JSON 없음"""
        # Given
        response_text = "중괄호가 전혀 없는 텍스트입니다."
        
        # When
        result = self.planning_service._parse_plan_response(response_text)
        
        # Then
        assert result is None

    def test_create_execution_plan_from_data(self):
        """계획 데이터로부터 ExecutionPlan 객체 생성 테스트"""
        # Given
        plan_data = {
            "description": "테스트 실행 계획",
            "steps": [
                {
                    "step": 1,
                    "description": "첫 번째 단계",
                    "tool_name": "test_tool",
                    "arguments": {"param": "value"},
                    "confirm_message": "실행할까요?"
                }
            ]
        }
        
        # When
        result = self.planning_service._create_execution_plan(plan_data)
        
        # Then
        assert isinstance(result, ExecutionPlan)
        assert result.description == "테스트 실행 계획"
        assert len(result.steps) == 1
        assert result.steps[0].step == 1
        assert result.steps[0].description == "첫 번째 단계"
        assert result.steps[0].tool_name == "test_tool"
        assert result.steps[0].arguments == {"param": "value"}
        assert result.steps[0].confirm_message == "실행할까요?"

    @pytest.mark.asyncio
    async def test_analyze_request_and_plan_exception_handling(self):
        """요청 분석 중 예외 처리 테스트"""
        # Given
        user_message = "테스트 요청"
        
        # Mock 예외 발생
        with patch.object(self.planning_service, '_detect_and_execute_workflow', side_effect=Exception("테스트 오류")):
            # When
            result = await self.planning_service.analyze_request_and_plan(user_message)
            
            # Then
            assert result is None
            self.mock_output_manager.log_if_debug.assert_called()


# 추가 엣지 케이스 테스트
class TestPlanningServiceEdgeCases:
    """PlanningService 엣지 케이스 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.mock_output_manager = Mock()
        self.mock_llm_agent = Mock()
        self.mock_llm_agent.llm_service = Mock()
        self.mock_mcp_tool_manager = Mock()
        
        with patch('dspilot_core.instructions.prompt_manager.get_default_prompt_manager'):
            self.planning_service = PlanningService(
                self.mock_output_manager,
                self.mock_llm_agent,
                self.mock_mcp_tool_manager
            )

    @pytest.mark.asyncio
    async def test_is_code_modification_request_edge_cases(self):
        """코드 수정 요청 감지 - 엣지 케이스들"""
        edge_cases = [
            ("", False),  # 빈 문자열
            ("수정", False),  # 키워드만 있고 파일 없음
            ("test.py", False),  # 파일명만 있고 수정 키워드 없음
            ("수정 test", False),  # 키워드 있지만 파일 확장자 없음
        ]
        
        for message, expected in edge_cases:
            # When
            result = await self.planning_service._is_code_modification_request(message)
            
            # Then
            assert result == expected, f"Failed for message: '{message}'"

    def test_create_execution_plan_empty_steps(self):
        """빈 단계 목록으로 ExecutionPlan 생성 테스트"""
        # Given
        plan_data = {
            "description": "빈 계획",
            "steps": []
        }
        
        # When
        result = self.planning_service._create_execution_plan(plan_data)
        
        # Then
        assert isinstance(result, ExecutionPlan)
        assert result.description == "빈 계획"
        assert len(result.steps) == 0

    def test_create_execution_plan_missing_fields(self):
        """필드가 누락된 단계로 ExecutionPlan 생성 테스트"""
        # Given
        plan_data = {
            "description": "테스트 계획",
            "steps": [
                {}  # 모든 필드 누락
            ]
        }
        
        # When
        result = self.planning_service._create_execution_plan(plan_data)
        
        # Then
        assert isinstance(result, ExecutionPlan)
        assert len(result.steps) == 1
        assert result.steps[0].step == 0
        assert result.steps[0].description == ""
        assert result.steps[0].tool_name == ""
        assert result.steps[0].arguments == {}
        assert result.steps[0].confirm_message == "" 