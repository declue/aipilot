#!/usr/bin/env python3
"""
OutputManager 단위 테스트
"""

import io
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from application.cli.constants import StyleColors
from application.cli.output_manager import OutputManager


class TestOutputManager:
    """OutputManager 테스트 클래스"""

    def setup_method(self) -> None:
        """각 테스트 메서드 실행 전 초기화"""
        self.quiet_manager = OutputManager(quiet_mode=True, debug_mode=False)
        self.normal_manager = OutputManager(quiet_mode=False, debug_mode=False)
        self.debug_manager = OutputManager(quiet_mode=False, debug_mode=True)

    def test_initialization(self) -> None:
        """초기화 테스트"""
        manager = OutputManager(quiet_mode=True, debug_mode=True)
        assert manager.quiet_mode is True
        assert manager.debug_mode is True
        assert manager.logger is not None

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_if_not_quiet_normal_mode(self, mock_stdout: io.StringIO) -> None:
        """일반 모드에서 출력 테스트"""
        self.normal_manager.print_if_not_quiet("테스트 메시지")
        output = mock_stdout.getvalue()
        assert "테스트 메시지" in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_if_not_quiet_quiet_mode(self, mock_stdout: io.StringIO) -> None:
        """조용한 모드에서 출력 테스트"""
        self.quiet_manager.print_if_not_quiet("테스트 메시지")
        output = mock_stdout.getvalue()
        assert output == ""

    @patch('application.cli.output_manager.logging.getLogger')
    def test_log_if_debug_debug_mode(self, mock_get_logger: Mock) -> None:
        """디버그 모드에서 로그 테스트"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        manager = OutputManager(quiet_mode=False, debug_mode=True)
        manager.logger = mock_logger
        
        manager.log_if_debug("디버그 메시지", "info")
        mock_logger.info.assert_called_once_with("디버그 메시지")
        
        manager.log_if_debug("경고 메시지", "warning")
        mock_logger.warning.assert_called_once_with("경고 메시지")
        
        manager.log_if_debug("에러 메시지", "error")
        mock_logger.error.assert_called_once_with("에러 메시지")

    @patch('application.cli.output_manager.logging.getLogger')
    def test_log_if_debug_normal_mode(self, mock_get_logger: Mock) -> None:
        """일반 모드에서 로그 테스트 (호출되지 않아야 함)"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        manager = OutputManager(quiet_mode=False, debug_mode=False)
        manager.logger = mock_logger
        
        manager.log_if_debug("디버그 메시지")
        mock_logger.info.assert_not_called()

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_banner_normal_mode(self, mock_stdout: io.StringIO) -> None:
        """일반 모드에서 배너 출력 테스트"""
        self.normal_manager.print_banner()
        output = mock_stdout.getvalue()
        assert "DSPilot CLI" in output
        assert StyleColors.HEADER in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_banner_quiet_mode(self, mock_stdout: io.StringIO) -> None:
        """조용한 모드에서 배너 출력 테스트 (출력되지 않아야 함)"""
        self.quiet_manager.print_banner()
        output = mock_stdout.getvalue()
        assert output == ""

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_help(self, mock_stdout: io.StringIO) -> None:
        """도움말 출력 테스트"""
        self.normal_manager.print_help()
        output = mock_stdout.getvalue()
        assert "사용 가능한 명령어" in output
        assert "help" in output
        assert "exit" in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_status(self, mock_stdout: io.StringIO) -> None:
        """상태 출력 테스트"""
        components = [
            ("테스트 구성요소 1", True),
            ("테스트 구성요소 2", None),
        ]
        session_start = datetime.now()
        query_count = 5
        conversation_history = ["msg1", "msg2", "msg3"]
        pending_actions = ["작업1", "작업2"]

        self.normal_manager.print_status(
            components, session_start, query_count, conversation_history, pending_actions
        )
        
        output = mock_stdout.getvalue()
        assert "시스템 상태" in output
        assert "테스트 구성요소 1" in output
        assert "테스트 구성요소 2" in output
        assert "처리된 쿼리: 5개" in output
        assert "대화 히스토리: 3개" in output
        assert "작업1" in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_tools_list_with_tools(self, mock_stdout: io.StringIO) -> None:
        """도구 목록 출력 테스트 (도구가 있는 경우)"""
        mock_tool1 = Mock()
        mock_tool1.name = "테스트_도구_1"
        mock_tool1.description = "테스트 도구 1 설명"
        
        mock_tool2 = Mock()
        mock_tool2.name = "테스트_도구_2"
        mock_tool2.description = "테스트 도구 2 설명"
        
        tools = [mock_tool1, mock_tool2]
        
        self.normal_manager.print_tools_list(tools)
        output = mock_stdout.getvalue()
        
        assert "사용 가능한 MCP 도구" in output
        assert "테스트_도구_1" in output
        assert "테스트_도구_2" in output
        assert "총 2개의 도구" in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_tools_list_empty(self, mock_stdout: io.StringIO) -> None:
        """도구 목록 출력 테스트 (도구가 없는 경우)"""
        self.normal_manager.print_tools_list([])
        output = mock_stdout.getvalue()
        assert "사용 가능한 도구가 없습니다" in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_response_normal_mode(self, mock_stdout: io.StringIO) -> None:
        """일반 모드에서 응답 출력 테스트"""
        response = "테스트 응답"
        used_tools = ["도구1", "도구2"]
        
        self.normal_manager.print_response(response, used_tools)
        output = mock_stdout.getvalue()
        
        assert "테스트 응답" in output
        assert "Assistant:" in output
        assert "사용된 도구" in output
        assert "도구1, 도구2" in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_response_quiet_mode(self, mock_stdout: io.StringIO) -> None:
        """조용한 모드에서 응답 출력 테스트"""
        response = "테스트 응답"
        used_tools = ["도구1"]
        
        self.quiet_manager.print_response(response, used_tools)
        output = mock_stdout.getvalue()
        
        # 조용한 모드에서는 응답만 출력되고 스타일링 없음
        assert "테스트 응답\n" == output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_error_messages(self, mock_stdout: io.StringIO) -> None:
        """다양한 메시지 출력 테스트"""
        self.normal_manager.print_error("에러 메시지")
        self.normal_manager.print_warning("경고 메시지")
        self.normal_manager.print_info("정보 메시지")
        self.normal_manager.print_success("성공 메시지")
        self.normal_manager.print_system("시스템 메시지")
        
        output = mock_stdout.getvalue()
        assert "에러 메시지" in output
        assert "경고 메시지" in output
        assert "정보 메시지" in output
        assert "성공 메시지" in output
        assert "시스템 메시지" in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_print_user_confirmation(self, mock_stdout: io.StringIO) -> None:
        """사용자 확인 메시지 출력 테스트"""
        message = "테스트 확인 메시지"
        tool_name = "테스트_도구"
        arguments = {"arg1": "value1", "arg2": "value2"}
        
        self.normal_manager.print_user_confirmation(message, tool_name, arguments)
        output = mock_stdout.getvalue()
        
        assert message in output
        assert tool_name in output
        assert "arg1" in output
        assert "value1" in output


if __name__ == "__main__":
    pytest.main([__file__]) 