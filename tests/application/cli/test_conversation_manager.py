#!/usr/bin/env python3
"""
ConversationManager 단위 테스트
"""

from unittest.mock import patch

import pytest

from application.cli.conversation_manager import ConversationManager


class TestConversationManager:
    """ConversationManager 테스트 클래스"""

    def setup_method(self) -> None:
        """각 테스트 메서드 실행 전 초기화"""
        self.manager = ConversationManager(max_context_turns=3)

    def test_initialization(self) -> None:
        """초기화 테스트"""
        manager = ConversationManager(max_context_turns=5)
        assert manager.max_context_turns == 5
        assert len(manager.conversation_history) == 0
        assert len(manager.pending_actions) == 0

    def test_add_to_history(self) -> None:
        """대화 히스토리 추가 테스트"""
        with patch('application.cli.conversation_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T12:00:00"
            
            self.manager.add_to_history("user", "안녕하세요", {"test": "data"})
            
            assert len(self.manager.conversation_history) == 1
            entry = self.manager.conversation_history[0]
            assert entry.role == "user"
            assert entry.content == "안녕하세요"
            assert entry.metadata == {"test": "data"}
            assert entry.timestamp == "2023-01-01T12:00:00"

    def test_add_to_history_without_metadata(self) -> None:
        """메타데이터 없이 히스토리 추가 테스트"""
        self.manager.add_to_history("assistant", "안녕하세요!")
        
        assert len(self.manager.conversation_history) == 1
        entry = self.manager.conversation_history[0]
        assert entry.role == "assistant"
        assert entry.content == "안녕하세요!"
        assert entry.metadata == {}

    def test_get_recent_context_empty(self) -> None:
        """빈 히스토리에서 컨텍스트 가져오기 테스트"""
        context = self.manager.get_recent_context()
        assert context == ""

    def test_get_recent_context_with_messages(self) -> None:
        """메시지가 있는 경우 컨텍스트 가져오기 테스트"""
        self.manager.add_to_history("user", "첫 번째 질문")
        self.manager.add_to_history("assistant", "첫 번째 답변", {"used_tools": ["tool1"]})
        self.manager.add_to_history("user", "두 번째 질문")
        
        context = self.manager.get_recent_context()
        
        assert "👤 User: 첫 번째 질문" in context
        assert "🤖 Assistant: 첫 번째 답변" in context
        assert "[사용된 도구: tool1]" in context
        assert "👤 User: 두 번째 질문" in context

    def test_get_recent_context_with_max_turns(self) -> None:
        """최대 턴 수 제한 테스트"""
        # 6개 메시지 추가 (3턴)
        for i in range(6):
            role = "user" if i % 2 == 0 else "assistant"
            self.manager.add_to_history(role, f"메시지 {i+1}")
        
        # max_context_turns=3이므로 최대 6개 메시지 (3턴)
        context = self.manager.get_recent_context()
        lines = context.split('\n')
        # 빈 줄 제외하고 실제 메시지 줄만 카운트
        message_lines = [line for line in lines if line.strip()]
        assert len(message_lines) == 6

    def test_build_enhanced_prompt_empty_context(self) -> None:
        """빈 컨텍스트에서 향상된 프롬프트 생성 테스트"""
        user_input = "테스트 질문"
        prompt = self.manager.build_enhanced_prompt(user_input)
        assert prompt == user_input

    def test_build_enhanced_prompt_with_context(self) -> None:
        """컨텍스트가 있는 경우 향상된 프롬프트 생성 테스트"""
        self.manager.add_to_history("user", "이전 질문")
        self.manager.add_to_history("assistant", "이전 답변")
        self.manager.pending_actions.append("테스트 작업")
        
        user_input = "새로운 질문"
        prompt = self.manager.build_enhanced_prompt(user_input)
        
        assert "이전 대화 맥락:" in prompt
        assert "이전 질문" in prompt
        assert "이전 답변" in prompt
        assert "보류 중인 작업들" in prompt
        assert "테스트 작업" in prompt
        assert "현재 사용자 요청: 새로운 질문" in prompt

    def test_extract_pending_actions_with_code_keywords(self) -> None:
        """코드 관련 키워드가 있는 경우 보류 작업 추출 테스트"""
        response_data = {
            "response": "파일을 수정하겠습니다. ```python\nprint('hello')\n```"
        }
        
        self.manager.extract_pending_actions(response_data)
        assert len(self.manager.pending_actions) == 1
        assert self.manager.pending_actions[0] == "파일 수정/생성 작업"

    def test_extract_pending_actions_with_file_extension(self) -> None:
        """파일 확장자가 있는 경우 보류 작업 추출 테스트"""
        response_data = {
            "response": "test.py 파일을 변경하겠습니다."
        }
        
        self.manager.extract_pending_actions(response_data)
        assert len(self.manager.pending_actions) == 1

    def test_extract_pending_actions_without_keywords(self) -> None:
        """관련 키워드가 없는 경우 보류 작업 추출 테스트"""
        response_data = {
            "response": "일반적인 답변입니다."
        }
        
        self.manager.extract_pending_actions(response_data)
        assert len(self.manager.pending_actions) == 0

    def test_extract_pending_actions_max_limit(self) -> None:
        """보류 작업 최대 개수 제한 테스트"""
        # 최대 개수를 초과하는 작업들 추가
        for i in range(5):
            response_data = {
                "response": f"파일{i}.py를 수정하겠습니다."
            }
            self.manager.extract_pending_actions(response_data)
        
        # 최대 3개까지만 유지되어야 함
        assert len(self.manager.pending_actions) == 3
        # 최근 3개가 유지되어야 함
        assert "파일 수정/생성 작업" in self.manager.pending_actions

    def test_clear_pending_actions(self) -> None:
        """보류 작업 초기화 테스트"""
        self.manager.pending_actions = ["작업1", "작업2", "작업3"]
        self.manager.clear_pending_actions()
        assert len(self.manager.pending_actions) == 0

    def test_clear_conversation(self) -> None:
        """대화 초기화 테스트"""
        self.manager.add_to_history("user", "테스트")
        self.manager.pending_actions.append("작업")
        
        self.manager.clear_conversation()
        
        assert len(self.manager.conversation_history) == 0
        assert len(self.manager.pending_actions) == 0

    def test_get_conversation_count(self) -> None:
        """대화 개수 반환 테스트"""
        assert self.manager.get_conversation_count() == 0
        
        self.manager.add_to_history("user", "테스트1")
        self.manager.add_to_history("assistant", "테스트2")
        
        assert self.manager.get_conversation_count() == 2

    def test_get_pending_actions(self) -> None:
        """보류 작업 목록 반환 테스트"""
        self.manager.pending_actions = ["작업1", "작업2"]
        actions = self.manager.get_pending_actions()
        
        assert actions == ["작업1", "작업2"]
        # 복사본을 반환하므로 원본 수정되지 않음
        actions.append("작업3")
        assert len(self.manager.pending_actions) == 2

    def test_has_pending_actions(self) -> None:
        """보류 작업 존재 여부 확인 테스트"""
        assert not self.manager.has_pending_actions()
        
        self.manager.pending_actions.append("작업")
        assert self.manager.has_pending_actions()
        
        self.manager.clear_pending_actions()
        assert not self.manager.has_pending_actions()

    def test_get_recent_context_custom_max_turns(self) -> None:
        """사용자 지정 최대 턴 수로 컨텍스트 가져오기 테스트"""
        # 4개 메시지 추가 (2턴)
        for i in range(4):
            role = "user" if i % 2 == 0 else "assistant"
            self.manager.add_to_history(role, f"메시지 {i+1}")
        
        # 1턴만 가져오기
        context = self.manager.get_recent_context(max_turns=1)
        lines = context.split('\n')
        message_lines = [line for line in lines if line.strip()]
        # 1턴 = 2개 메시지
        assert len(message_lines) == 2
        assert "메시지 3" in context
        assert "메시지 4" in context
        assert "메시지 1" not in context


if __name__ == "__main__":
    pytest.main([__file__]) 