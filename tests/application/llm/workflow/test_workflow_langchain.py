"""
Langchain 기반 워크플로우 테스트
"""

from unittest.mock import AsyncMock, Mock

import pytest

from dspilot_core.llm.workflow.basic_chat_workflow import BasicChatWorkflow
from dspilot_core.llm.workflow.workflow_utils import (
    get_available_workflows,
    get_workflow,
    register_workflow,
)


class TestBasicChatWorkflow:
    """기본 채팅 워크플로우 테스트"""
    
    @pytest.fixture
    def workflow(self):
        """테스트용 워크플로우"""
        return BasicChatWorkflow()
    
    @pytest.fixture
    def mock_agent(self):
        """모킹된 에이전트"""
        agent = Mock()
        agent._generate_basic_response = AsyncMock(return_value="테스트 응답")
        return agent
    
    @pytest.mark.asyncio
    async def test_run_success(self, workflow, mock_agent):
        """워크플로우 실행 성공 테스트"""
        result = await workflow.run(mock_agent, "안녕하세요")
        
        assert result == "테스트 응답"
        mock_agent._generate_basic_response.assert_called_once_with("안녕하세요", None)
    
    @pytest.mark.asyncio
    async def test_run_with_streaming_callback(self, workflow, mock_agent):
        """스트리밍 콜백과 함께 워크플로우 실행 테스트"""
        streaming_callback = Mock()
        
        result = await workflow.run(mock_agent, "안녕하세요", streaming_callback)
        
        assert result == "테스트 응답"
        mock_agent._generate_basic_response.assert_called_once_with("안녕하세요", streaming_callback)
    
    @pytest.mark.asyncio
    async def test_run_agent_without_method(self, workflow):
        """에이전트에 메서드가 없는 경우 테스트"""
        agent_without_method = Mock()
        # _generate_basic_response 메서드가 없는 에이전트
        del agent_without_method._generate_basic_response
        
        result = await workflow.run(agent_without_method, "테스트")
        
        assert "에이전트 설정에 문제가 있습니다" in result
    
    @pytest.mark.asyncio
    async def test_run_with_exception(self, workflow, mock_agent):
        """예외 발생 시 테스트"""
        mock_agent._generate_basic_response.side_effect = Exception("테스트 예외")
        
        result = await workflow.run(mock_agent, "테스트")
        
        assert "워크플로우 실행 중 오류가 발생했습니다" in result
        assert "테스트 예외" in result


class TestWorkflowUtils:
    """워크플로우 유틸리티 테스트"""
    
    def test_get_workflow_basic_chat(self):
        """기본 채팅 워크플로우 가져오기 테스트"""
        workflow_class = get_workflow("basic_chat")
        assert workflow_class == BasicChatWorkflow
    
    def test_get_workflow_case_insensitive(self):
        """대소문자 무관 워크플로우 가져오기 테스트"""
        workflow_class = get_workflow("BASIC_CHAT")
        assert workflow_class == BasicChatWorkflow
    
    def test_get_workflow_not_found(self):
        """존재하지 않는 워크플로우 테스트"""
        with pytest.raises(ValueError) as exc_info:
            get_workflow("non_existent")
        
        assert "지원하지 않는 워크플로우: non_existent" in str(exc_info.value)
        assert "사용 가능한 워크플로우:" in str(exc_info.value)
    
    def test_register_workflow(self):
        """워크플로우 등록 테스트"""
        from dspilot_core.llm.workflow.base_workflow import BaseWorkflow
        
        class TestWorkflow(BaseWorkflow):
            async def run(self, agent, message, streaming_callback=None):
                return "test"
        
        # 새 워크플로우 등록
        register_workflow("test_workflow", TestWorkflow)
        
        # 등록된 워크플로우 가져오기
        workflow_class = get_workflow("test_workflow")
        assert workflow_class == TestWorkflow
        
        # 사용 가능한 워크플로우 목록에 포함되는지 확인
        available = get_available_workflows()
        assert "test_workflow" in available
    
    def test_get_available_workflows(self):
        """사용 가능한 워크플로우 목록 테스트"""
        workflows = get_available_workflows()
        assert isinstance(workflows, list)
        assert "basic_chat" in workflows
        assert len(workflows) >= 1 