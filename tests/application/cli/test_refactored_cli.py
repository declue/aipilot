#!/usr/bin/env python3
"""
리팩토링된 DSPilot CLI 시스템 테스트

SOLID 원칙이 적용된 새로운 구조를 테스트합니다.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dspilot_cli.constants import PromptNames
from dspilot_cli.conversation_manager import ConversationManager
from dspilot_cli.execution_manager import ExecutionManager
from dspilot_cli.interaction_manager import InteractionManager
from dspilot_cli.output_manager import OutputManager
from dspilot_core.instructions.prompt_manager import PromptManager


class TestPromptManager:
    """프롬프트 관리자 테스트"""

    def test_prompt_manager_initialization(self, tmp_path):
        """프롬프트 관리자 초기화 테스트"""
        manager = PromptManager(tmp_path)
        assert manager.instructions_dir == tmp_path
        assert len(manager._prompt_cache) == 0

    def test_get_prompt_file_not_exists(self, tmp_path):
        """존재하지 않는 프롬프트 파일 테스트"""
        manager = PromptManager(tmp_path)
        result = manager.get_prompt("nonexistent")
        assert result is None

    def test_get_prompt_success(self, tmp_path):
        """프롬프트 로드 성공 테스트"""
        # 테스트 프롬프트 파일 생성
        prompt_file = tmp_path / "test_prompt.txt"
        prompt_content = "테스트 프롬프트: {user_input}"
        prompt_file.write_text(prompt_content, encoding='utf-8')

        manager = PromptManager(tmp_path)
        result = manager.get_prompt("test_prompt")
        assert result == prompt_content

    def test_get_formatted_prompt(self, tmp_path):
        """포맷팅된 프롬프트 테스트"""
        prompt_file = tmp_path / "format_test.txt"
        prompt_content = "사용자 입력: {user_input}, 컨텍스트: {context}"
        prompt_file.write_text(prompt_content, encoding='utf-8')

        manager = PromptManager(tmp_path)
        result = manager.get_formatted_prompt(
            "format_test",
            user_input="테스트 입력",
            context="테스트 컨텍스트"
        )
        expected = "사용자 입력: 테스트 입력, 컨텍스트: 테스트 컨텍스트"
        assert result == expected

    def test_add_custom_prompt(self, tmp_path):
        """커스텀 프롬프트 추가 테스트"""
        manager = PromptManager(tmp_path)
        
        custom_content = "커스텀 프롬프트: {message}"
        success = manager.add_custom_prompt("custom_test", custom_content)
        assert success

        # 파일이 생성되었는지 확인
        custom_file = tmp_path / "custom_test.txt"
        assert custom_file.exists()
        assert custom_file.read_text(encoding='utf-8') == custom_content

    def test_list_available_prompts(self, tmp_path):
        """사용 가능한 프롬프트 목록 테스트"""
        # 여러 프롬프트 파일 생성
        (tmp_path / "prompt1.txt").write_text("프롬프트 1", encoding='utf-8')
        (tmp_path / "prompt2.txt").write_text("프롬프트 2", encoding='utf-8')
        (tmp_path / "not_prompt.log").write_text("로그 파일", encoding='utf-8')

        manager = PromptManager(tmp_path)
        prompts = manager.list_available_prompts()
        
        assert "prompt1" in prompts
        assert "prompt2" in prompts
        assert "not_prompt" not in prompts  # .txt 파일만 포함
        assert len(prompts) == 2

    def test_cache_functionality(self, tmp_path):
        """캐시 기능 테스트"""
        prompt_file = tmp_path / "cache_test.txt"
        prompt_content = "캐시 테스트 프롬프트"
        prompt_file.write_text(prompt_content, encoding='utf-8')

        manager = PromptManager(tmp_path)
        
        # 첫 번째 로드 (파일에서)
        result1 = manager.get_prompt("cache_test", use_cache=True)
        assert result1 == prompt_content
        assert "cache_test" in manager._prompt_cache

        # 파일 수정
        prompt_file.write_text("수정된 내용", encoding='utf-8')

        # 두 번째 로드 (캐시에서)
        result2 = manager.get_prompt("cache_test", use_cache=True)
        assert result2 == prompt_content  # 캐시된 내용

        # 캐시 무시하고 로드
        result3 = manager.get_prompt("cache_test", use_cache=False)
        assert result3 == "수정된 내용"


class TestConversationManager:
    """대화 관리자 테스트"""

    def test_conversation_manager_initialization(self):
        """대화 관리자 초기화 테스트"""
        manager = ConversationManager()
        assert len(manager.conversation_history) == 0
        assert len(manager.pending_actions) == 0
        assert manager.prompt_manager is not None

    def test_add_to_history(self):
        """대화 히스토리 추가 테스트"""
        manager = ConversationManager()
        manager.add_to_history("user", "테스트 메시지")
        
        assert len(manager.conversation_history) == 1
        entry = manager.conversation_history[0]
        assert entry.role == "user"
        assert entry.content == "테스트 메시지"

    @patch('dspilot_core.instructions.prompt_manager.get_default_prompt_manager')
    def test_build_enhanced_prompt_with_mock(self, mock_get_manager):
        """향상된 프롬프트 구성 테스트 (모킹)"""
        # 모킹된 프롬프트 관리자 설정
        mock_manager = Mock()
        mock_manager.get_formatted_prompt.return_value = "모킹된 향상된 프롬프트"
        mock_get_manager.return_value = mock_manager

        manager = ConversationManager()
        manager.add_to_history("user", "이전 질문")
        manager.add_to_history("assistant", "이전 답변")

        result = manager.build_enhanced_prompt("새 질문")
        
        # 프롬프트 관리자가 호출되었는지 확인
        mock_manager.get_formatted_prompt.assert_called_once()
        assert result == "모킹된 향상된 프롬프트"


class TestExecutionManager:
    """실행 관리자 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.output_manager = Mock(spec=OutputManager)
        self.interaction_manager = Mock(spec=InteractionManager)
        self.llm_agent = Mock()
        self.mcp_tool_manager = Mock()

    @patch('dspilot_core.instructions.prompt_manager.get_default_prompt_manager')
    def test_execution_manager_initialization(self, mock_get_manager):
        """실행 관리자 초기화 테스트"""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        manager = ExecutionManager(
            self.output_manager,
            self.interaction_manager,
            self.llm_agent,
            self.mcp_tool_manager
        )

        assert manager.output_manager == self.output_manager
        assert manager.interaction_manager == self.interaction_manager
        assert manager.llm_agent == self.llm_agent
        assert manager.mcp_tool_manager == self.mcp_tool_manager
        assert manager.prompt_manager == mock_manager

    @patch('dspilot_core.instructions.prompt_manager.get_default_prompt_manager')
    @pytest.mark.asyncio
    async def test_analyze_request_with_prompt_manager(self, mock_get_manager):
        """프롬프트 관리자를 사용한 요청 분석 테스트"""
        # 모킹 설정
        mock_manager = Mock()
        mock_manager.get_formatted_prompt.return_value = "분석 프롬프트"
        mock_get_manager.return_value = mock_manager

        # MCP 도구 관리자 모킹
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "테스트 도구"
        self.mcp_tool_manager.get_langchain_tools = AsyncMock(return_value=[mock_tool])

        # LLM 응답 모킹
        mock_response = Mock()
        mock_response.response = '{"need_tools": false}'
        self.llm_agent.llm_service.generate_response = AsyncMock(return_value=mock_response)

        manager = ExecutionManager(
            self.output_manager,
            self.interaction_manager,
            self.llm_agent,
            self.mcp_tool_manager
        )

        result = await manager.analyze_request_and_plan("테스트 요청")
        
        # 프롬프트 관리자가 호출되었는지 확인
        mock_manager.get_formatted_prompt.assert_called_once_with(
            PromptNames.ANALYSIS,
            user_message="테스트 요청",
            tools_desc="- test_tool: 테스트 도구"
        )


class TestOutputManager:
    """출력 관리자 테스트"""

    def test_output_manager_initialization(self):
        """출력 관리자 초기화 테스트"""
        manager = OutputManager(quiet_mode=True, debug_mode=False)
        assert manager.quiet_mode is True
        assert manager.debug_mode is False
        assert manager.stream_mode is False
        assert manager.verbose_mode is False

    def test_print_if_not_quiet(self, capsys):
        """조용한 모드 테스트"""
        # 조용한 모드
        quiet_manager = OutputManager(quiet_mode=True)
        quiet_manager.print_if_not_quiet("테스트 메시지")
        captured = capsys.readouterr()
        assert captured.out == ""

        # 일반 모드
        normal_manager = OutputManager(quiet_mode=False)
        normal_manager.print_if_not_quiet("테스트 메시지")
        captured = capsys.readouterr()
        assert "테스트 메시지" in captured.out


class TestInteractionManager:
    """상호작용 관리자 테스트"""

    def test_interaction_manager_initialization(self):
        """상호작용 관리자 초기화 테스트"""
        output_manager = Mock(spec=OutputManager)
        manager = InteractionManager(output_manager, full_auto_mode=True)
        
        assert manager.output_manager == output_manager
        assert manager.full_auto_mode is True

    def test_set_full_auto_mode(self):
        """전체 자동 모드 설정 테스트"""
        output_manager = Mock(spec=OutputManager)
        manager = InteractionManager(output_manager, full_auto_mode=False)
        
        assert manager.full_auto_mode is False
        
        manager.set_full_auto_mode(True)
        assert manager.full_auto_mode is True


if __name__ == "__main__":
    # 개별 테스트 실행을 위한 코드
    import shutil
    import tempfile
    
    def run_prompt_manager_tests():
        """프롬프트 매니저 테스트 실행"""
        print("=== 프롬프트 관리자 테스트 ===")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # 기본 기능 테스트
            manager = PromptManager(tmp_path)
            print(f"✓ 프롬프트 관리자 초기화: {manager.instructions_dir}")
            
            # 프롬프트 추가 테스트
            success = manager.add_custom_prompt("test", "테스트 프롬프트: {input}")
            print(f"✓ 커스텀 프롬프트 추가: {success}")
            
            # 프롬프트 로드 테스트
            result = manager.get_prompt("test")
            print(f"✓ 프롬프트 로드: {result is not None}")
            
            # 포맷팅 테스트
            formatted = manager.get_formatted_prompt("test", input="테스트")
            print(f"✓ 프롬프트 포맷팅: {formatted}")
            
            # 목록 테스트
            prompts = manager.list_available_prompts()
            print(f"✓ 사용 가능한 프롬프트: {prompts}")

    if __name__ == "__main__":
        run_prompt_manager_tests() 