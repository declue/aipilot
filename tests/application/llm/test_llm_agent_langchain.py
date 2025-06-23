"""
Langchain 기반 LLM 에이전트 테스트
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from application.llm.llm_agent import LLMAgent
from application.llm.models.llm_config import LLMConfig


class MockConfigManager:
    """테스트용 설정 관리자"""
    
    def __init__(self, llm_config=None, mode="basic", workflow=None):
        self._llm_config = llm_config or {
            "api_key": "test_key",
            "model": "gpt-3.5-turbo",
            "max_tokens": 1000,
            "temperature": 0.7
        }
        self._mode = mode
        self._workflow = workflow
    
    def get_llm_config(self):
        return self._llm_config
    
    def get_config_value(self, section, key, default=None):
        if section == "LLM" and key == "mode":
            return self._mode
        elif section == "LLM" and key == "workflow":
            return self._workflow
        return default


class TestLLMAgent:
    """LLM 에이전트 테스트"""
    
    @pytest.fixture
    def config_manager(self):
        """테스트용 설정 관리자"""
        return MockConfigManager()
    
    @pytest.fixture
    def llm_agent(self, config_manager):
        """테스트용 LLM 에이전트"""
        with patch('application.llm.services.llm_service.ChatOpenAI'):
            agent = LLMAgent(config_manager)
            return agent
    
    def test_initialization(self, llm_agent):
        """초기화 테스트"""
        assert llm_agent.config_manager is not None
        assert llm_agent.llm_service is not None
        assert llm_agent.conversation_service is not None
        assert llm_agent.history == []
        assert isinstance(llm_agent.llm_config, LLMConfig)
    
    def test_add_user_message(self, llm_agent):
        """사용자 메시지 추가 테스트"""
        message = "안녕하세요"
        llm_agent.add_user_message(message)
        
        # 대화 서비스에 추가 확인
        messages = llm_agent.conversation_service.get_messages()
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == message
        
        # 하위 호환성 확인
        assert len(llm_agent.history) == 1
        assert llm_agent.history[0]["role"] == "user"
        assert llm_agent.history[0]["content"] == message
    
    def test_add_assistant_message(self, llm_agent):
        """어시스턴트 메시지 추가 테스트"""
        message = "안녕하세요! 도움이 필요하시나요?"
        llm_agent.add_assistant_message(message)
        
        # 대화 서비스에 추가 확인
        messages = llm_agent.conversation_service.get_messages()
        assert len(messages) == 1
        assert messages[0].role == "assistant"
        assert messages[0].content == message
        
        # 하위 호환성 확인
        assert len(llm_agent.history) == 1
        assert llm_agent.history[0]["role"] == "assistant"
        assert llm_agent.history[0]["content"] == message
    
    def test_clear_conversation(self, llm_agent):
        """대화 초기화 테스트"""
        llm_agent.add_user_message("테스트 1")
        llm_agent.add_assistant_message("테스트 2")
        
        assert len(llm_agent.conversation_service.get_messages()) == 2
        assert len(llm_agent.history) == 2
        
        llm_agent.clear_conversation()
        
        assert len(llm_agent.conversation_service.get_messages()) == 0
        assert len(llm_agent.history) == 0
    
    def test_get_llm_mode(self):
        """LLM 모드 반환 테스트"""
        # 기본 모드
        config_manager = MockConfigManager(mode="basic")
        with patch('application.llm.services.llm_service.ChatOpenAI'):
            agent = LLMAgent(config_manager)
            assert agent._get_llm_mode() == "basic"
        
        # 워크플로우 모드
        config_manager = MockConfigManager(mode="workflow")
        with patch('application.llm.services.llm_service.ChatOpenAI'):
            agent = LLMAgent(config_manager)
            assert agent._get_llm_mode() == "workflow"
        
        # 대소문자 처리
        config_manager = MockConfigManager(mode="BASIC")
        with patch('application.llm.services.llm_service.ChatOpenAI'):
            agent = LLMAgent(config_manager)
            assert agent._get_llm_mode() == "basic"
    
    @pytest.mark.asyncio
    async def test_handle_basic_mode(self, llm_agent):
        """기본 모드 처리 테스트"""
        # LLM 서비스 모킹
        mock_response = Mock()
        mock_response.response = "테스트 응답"
        
        llm_agent.llm_service.generate_response = AsyncMock(return_value=mock_response)
        
        result = await llm_agent._handle_basic_mode("테스트 메시지")
        
        assert result["response"] == "테스트 응답"
        assert result["reasoning"] == ""
        assert result["used_tools"] == []
    
    @pytest.mark.asyncio
    async def test_handle_workflow_mode(self):
        """워크플로우 모드 처리 테스트"""
        config_manager = MockConfigManager(mode="workflow", workflow="basic_chat")
        
        with patch('application.llm.services.llm_service.ChatOpenAI'):
            agent = LLMAgent(config_manager)
        
        # 워크플로우 모킹
        mock_workflow = Mock()
        mock_workflow.run = AsyncMock(return_value="워크플로우 응답")
        
        with patch('application.llm.workflow.workflow_utils.get_workflow') as mock_get_workflow:
            mock_get_workflow.return_value = Mock(return_value=mock_workflow)
            
            result = await agent._handle_workflow_mode("테스트 메시지")
            
            assert result["response"] == "워크플로우 응답"
            assert result["workflow"] == "basic_chat"
            assert result["reasoning"] == ""
            assert result["used_tools"] == []
    
    @pytest.mark.asyncio
    async def test_generate_response_basic_mode(self, llm_agent):
        """기본 모드 응답 생성 테스트"""
        # LLM 서비스 모킹
        mock_response = Mock()
        mock_response.response = "테스트 응답"
        
        llm_agent.llm_service.generate_response = AsyncMock(return_value=mock_response)
        
        result = await llm_agent.generate_response("안녕하세요")
        
        assert result["response"] == "테스트 응답"
        assert result["reasoning"] == ""
        assert result["used_tools"] == []
        
        # 메시지가 추가되었는지 확인
        messages = llm_agent.conversation_service.get_messages()
        assert len(messages) == 2  # user + assistant
        assert messages[0].role == "user"
        assert messages[0].content == "안녕하세요"
        assert messages[1].role == "assistant"
        assert messages[1].content == "테스트 응답"
    
    @pytest.mark.asyncio
    async def test_generate_response_error_handling(self, llm_agent):
        """응답 생성 오류 처리 테스트"""
        # LLM 서비스에서 예외 발생
        llm_agent.llm_service.generate_response = AsyncMock(side_effect=Exception("테스트 오류"))
        
        result = await llm_agent.generate_response("테스트 메시지")
        
        assert "응답 생성 중 오류가 발생했습니다" in result["response"]
        assert result["reasoning"] == "테스트 오류"
        assert result["used_tools"] == []
    
    @pytest.mark.asyncio
    async def test_cleanup(self, llm_agent):
        """리소스 정리 테스트"""
        llm_agent.llm_service.cleanup = AsyncMock()
        
        await llm_agent.cleanup()
        
        llm_agent.llm_service.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_manager(self, llm_agent):
        """컨텍스트 매니저 테스트"""
        llm_agent.llm_service.cleanup = AsyncMock()
        
        async with llm_agent as agent:
            assert agent is llm_agent
        
        llm_agent.llm_service.cleanup.assert_called_once()


class TestLLMAgentMCPMode:
    """MCP 모드 테스트"""
    
    @pytest.fixture
    def config_manager(self):
        """MCP 모드 설정 관리자"""
        return MockConfigManager(mode="mcp_tools")
    
    @pytest.fixture
    def mock_mcp_tool_manager(self):
        """모킹된 MCP 도구 관리자"""
        mock = Mock()
        mock.run_agent_with_tools = AsyncMock(return_value={
            "response": "MCP 도구 응답",
            "reasoning": "MCP 추론",
            "used_tools": ["test_tool"]
        })
        return mock
    
    @pytest.mark.asyncio
    async def test_handle_mcp_tools_mode(self, config_manager, mock_mcp_tool_manager):
        """MCP 도구 모드 처리 테스트"""
        with patch('application.llm.services.llm_service.ChatOpenAI'):
            agent = LLMAgent(config_manager, mock_mcp_tool_manager)
        
        result = await agent._handle_mcp_tools_mode("테스트 메시지")
        
        assert result["response"] == "MCP 도구 응답"
        assert result["reasoning"] == "MCP 추론"
        assert result["used_tools"] == ["test_tool"]
        
        mock_mcp_tool_manager.run_agent_with_tools.assert_called_once_with("테스트 메시지")
    
    @pytest.mark.asyncio
    async def test_handle_mcp_tools_mode_no_manager(self, config_manager):
        """MCP 도구 관리자가 없는 경우 테스트"""
        with patch('application.llm.services.llm_service.ChatOpenAI'):
            agent = LLMAgent(config_manager, None)
        
        result = await agent._handle_mcp_tools_mode("테스트 메시지")
        
        assert "MCP 도구 관리자가 설정되지 않았습니다" in result["response"]
        assert result["used_tools"] == [] 