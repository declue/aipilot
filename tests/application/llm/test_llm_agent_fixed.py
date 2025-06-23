"""
LLM Agent 수정된 테스트 - 안정적인 버전
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent.parent.resolve()
sys.path.insert(0, str(project_root))

from application.config.config_manager import ConfigManager
from application.llm.llm_agent import LLMAgent


def test_llm_agent_initialization():
    """LLM Agent 초기화 테스트"""
    config = ConfigManager()
    agent = LLMAgent(config, None)
    
    assert agent.config_manager == config
    assert agent.mcp_tool_manager is None
    assert agent.history == []
    assert agent._client is None
    print("✅ 초기화 테스트 통과")


def test_message_operations():
    """메시지 조작 테스트"""
    config = ConfigManager()
    agent = LLMAgent(config, None)
    
    # 사용자 메시지 추가
    agent.add_user_message("Hello")
    assert len(agent.history) == 1
    assert agent.history[0]["role"] == "user"
    assert agent.history[0]["content"] == "Hello"
    
    # 어시스턴트 메시지 추가
    agent.add_assistant_message("Hi")
    assert len(agent.history) == 2
    assert agent.history[1]["role"] == "assistant"
    assert agent.history[1]["content"] == "Hi"
    
    # 대화 삭제
    agent.clear_conversation()
    assert len(agent.history) == 0
    print("✅ 메시지 조작 테스트 통과")


def test_helper_functions():
    """헬퍼 함수 테스트 - 제거된 함수들로 인해 빈 테스트"""
    # 이전에 테스트하던 헬퍼 함수들이 제거되었습니다
    print("✅ 헬퍼 함수 테스트 통과 (제거된 함수들)")


def test_client_reinitialize():
    """클라이언트 재초기화 테스트"""
    config = ConfigManager()
    agent = LLMAgent(config, None)
    
    # 클라이언트 재초기화
    agent.reinitialize_client()
    assert agent._client is None
    print("✅ 클라이언트 재초기화 테스트 통과")


def test_llm_agent_basic():
    """통합 기본 테스트"""
    config = ConfigManager()
    agent = LLMAgent(config, None)
    
    # 기본 상태 확인
    assert isinstance(agent, LLMAgent)
    assert agent.history == []
    
    # 메시지 추가
    agent.add_user_message("테스트 메시지")
    agent.add_assistant_message("테스트 응답")
    
    # 히스토리 확인
    assert len(agent.history) == 2
    assert agent.history[0]["content"] == "테스트 메시지"
    assert agent.history[1]["content"] == "테스트 응답"
    
    print("✅ 통합 기본 테스트 통과")


if __name__ == "__main__":
    print("🧪 LLM Agent 수정된 테스트 시작...")
    
    test_llm_agent_initialization()
    test_message_operations()
    test_helper_functions()
    test_client_reinitialize()
    test_llm_agent_basic()
    
    print("🎉 모든 테스트 통과! LLM Agent가 정상 작동합니다.") 