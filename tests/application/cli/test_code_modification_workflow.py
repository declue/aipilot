#!/usr/bin/env python3
"""
CodeModificationWorkflow 테스트 케이스
=====================================

CodeModificationWorkflow의 모든 기능을 검증하는 테스트 모듈입니다.
Mock을 사용하여 외부 의존성을 제거하고 독립적인 테스트를 구현합니다.

테스트 범위
-----------
1. 워크플로우 기본 실행 흐름
2. 파일 읽기/쓰기 도구 탐지 로직
3. LLM 코드 수정 기능
4. 파일 경로 추출 기능  
5. 오류 처리 및 예외 상황
6. 메타데이터 기반 도구 탐지
"""

from typing import List
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest

from dspilot_core.llm.workflow.code_modification_workflow import CodeModificationWorkflow


class TestCodeModificationWorkflow:
    """CodeModificationWorkflow 테스트 클래스"""

    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        self.workflow = CodeModificationWorkflow()
        self.mock_agent = Mock()
        self.mock_agent.mcp_tool_manager = Mock()
        self.mock_agent.mcp_tool_manager.get_langchain_tools = AsyncMock()  # AsyncMock으로 설정
        self.mock_agent.llm_service = Mock()
        self.mock_agent.llm_service.generate_response = AsyncMock()  # AsyncMock으로 설정
        self.mock_streaming_callback = Mock()

    @pytest.mark.asyncio
    async def test_run_successful_code_modification(self):
        """코드 수정 워크플로우 정상 실행 테스트"""
        # Given
        user_message = "test.py 파일의 함수를 수정해주세요"
        original_content = "def hello():\n    print('hello')"
        modified_content = "def hello():\n    print('Hello, World!')"
        
        # Mock 도구 설정
        mock_read_tool = self._create_mock_tool("read_file", ["path"])
        mock_write_tool = self._create_mock_tool("write_file", ["path", "content"])
        self.mock_agent.mcp_tool_manager.get_langchain_tools.return_value = [
            mock_read_tool, mock_write_tool
        ]
        
        # Mock 파일 경로 추출
        with patch.object(self.workflow, '_extract_file_path', return_value="/test/test.py"):
            # Mock 파일 읽기
            with patch.object(self.workflow, '_read_file_content', return_value=original_content):
                # Mock LLM 코드 수정
                with patch.object(self.workflow, '_modify_code_with_llm', return_value=modified_content):
                    # Mock 파일 쓰기
                    with patch.object(self.workflow, '_write_file_content', return_value=True):
                        
                        # When
                        result = await self.workflow.run(
                            self.mock_agent, user_message, self.mock_streaming_callback
                        )
                        
                        # Then
                        assert "성공적으로 수정되었습니다" in result
                        assert "/test/test.py" in result
                        
                        # 스트리밍 콜백 호출 확인
                        assert self.mock_streaming_callback.call_count > 0

    @pytest.mark.asyncio
    async def test_run_no_tools_available(self):
        """사용 가능한 도구가 없는 경우 테스트"""
        # Given
        user_message = "test.py 파일을 수정해주세요"
        self.mock_agent.mcp_tool_manager.get_langchain_tools.return_value = []
        
        # When
        result = await self.workflow.run(
            self.mock_agent, user_message, self.mock_streaming_callback
        )
        
        # Then
        assert "사용 가능한 파일 처리 도구가 없습니다" in result

    @pytest.mark.asyncio
    async def test_run_missing_read_or_write_tools(self):
        """읽기 또는 쓰기 도구가 없는 경우 테스트"""
        # Given
        user_message = "test.py 파일을 수정해주세요"
        # 읽기 도구만 있고 쓰기 도구 없음
        mock_read_tool = self._create_mock_tool("read_file", ["path"])
        self.mock_agent.mcp_tool_manager.get_langchain_tools.return_value = [mock_read_tool]
        
        # When
        result = await self.workflow.run(
            self.mock_agent, user_message, self.mock_streaming_callback
        )
        
        # Then
        assert "파일 읽기 또는 쓰기 도구를 찾을 수 없습니다" in result

    @pytest.mark.asyncio
    async def test_run_file_path_not_found(self):
        """파일 경로를 찾을 수 없는 경우 테스트"""
        # Given
        user_message = "코드를 수정해주세요"  # 파일 경로 없음
        mock_read_tool = self._create_mock_tool("read_file", ["path"])
        mock_write_tool = self._create_mock_tool("write_file", ["path", "content"])
        self.mock_agent.mcp_tool_manager.get_langchain_tools.return_value = [
            mock_read_tool, mock_write_tool
        ]
        
        with patch.object(self.workflow, '_extract_file_path', return_value=None):
            # When
            result = await self.workflow.run(
                self.mock_agent, user_message, self.mock_streaming_callback
            )
            
            # Then
            assert "수정할 파일 경로를 찾을 수 없습니다" in result

    @pytest.mark.asyncio
    async def test_run_file_read_failure(self):
        """파일 읽기 실패 테스트"""
        # Given
        user_message = "test.py 파일을 수정해주세요"
        mock_read_tool = self._create_mock_tool("read_file", ["path"])
        mock_write_tool = self._create_mock_tool("write_file", ["path", "content"])
        self.mock_agent.mcp_tool_manager.get_langchain_tools.return_value = [
            mock_read_tool, mock_write_tool
        ]
        
        with patch.object(self.workflow, '_extract_file_path', return_value="/test/test.py"):
            with patch.object(self.workflow, '_read_file_content', return_value=None):
                # When
                result = await self.workflow.run(
                    self.mock_agent, user_message, self.mock_streaming_callback
                )
                
                # Then
                assert "파일을 읽을 수 없습니다" in result

    @pytest.mark.asyncio
    async def test_run_code_modification_failure(self):
        """코드 수정 실패 테스트"""
        # Given
        user_message = "test.py 파일을 수정해주세요"
        original_content = "def hello():\n    print('hello')"
        
        mock_read_tool = self._create_mock_tool("read_file", ["path"])
        mock_write_tool = self._create_mock_tool("write_file", ["path", "content"])
        self.mock_agent.mcp_tool_manager.get_langchain_tools.return_value = [
            mock_read_tool, mock_write_tool
        ]
        
        with patch.object(self.workflow, '_extract_file_path', return_value="/test/test.py"):
            with patch.object(self.workflow, '_read_file_content', return_value=original_content):
                # 수정된 코드가 원본과 동일하거나 없음
                with patch.object(self.workflow, '_modify_code_with_llm', return_value=""):
                    # When
                    result = await self.workflow.run(
                        self.mock_agent, user_message, self.mock_streaming_callback
                    )
                    
                    # Then
                    assert "코드 수정이 필요하지 않거나 수정에 실패했습니다" in result

    @pytest.mark.asyncio
    async def test_run_file_write_failure(self):
        """파일 쓰기 실패 테스트"""
        # Given
        user_message = "test.py 파일을 수정해주세요"
        original_content = "def hello():\n    print('hello')"
        modified_content = "def hello():\n    print('Hello, World!')"
        
        mock_read_tool = self._create_mock_tool("read_file", ["path"])
        mock_write_tool = self._create_mock_tool("write_file", ["path", "content"])
        self.mock_agent.mcp_tool_manager.get_langchain_tools.return_value = [
            mock_read_tool, mock_write_tool
        ]
        
        with patch.object(self.workflow, '_extract_file_path', return_value="/test/test.py"):
            with patch.object(self.workflow, '_read_file_content', return_value=original_content):
                with patch.object(self.workflow, '_modify_code_with_llm', return_value=modified_content):
                    with patch.object(self.workflow, '_write_file_content', return_value=False):
                        # When
                        result = await self.workflow.run(
                            self.mock_agent, user_message, self.mock_streaming_callback
                        )
                        
                        # Then
                        assert "파일 쓰기에 실패했습니다" in result

    def test_find_read_tools(self):
        """읽기 도구 탐지 테스트"""
        # Given
        read_tool = self._create_mock_tool("read_file", ["path"])
        write_tool = self._create_mock_tool("write_file", ["path", "content"])
        mixed_tool = self._create_mock_tool("edit_file", ["path", "content"])
        tools = [read_tool, write_tool, mixed_tool]
        
        # When
        read_tools = self.workflow._find_read_tools(tools)
        
        # Then
        assert len(read_tools) == 1
        assert read_tools[0] == read_tool

    def test_find_write_tools(self):
        """쓰기 도구 탐지 테스트"""
        # Given
        read_tool = self._create_mock_tool("read_file", ["path"])
        write_tool = self._create_mock_tool("write_file", ["path", "content"])
        mixed_tool = self._create_mock_tool("edit_file", ["path", "content"])
        tools = [read_tool, write_tool, mixed_tool]
        
        # When
        write_tools = self.workflow._find_write_tools(tools)
        
        # Then
        assert len(write_tools) == 2
        assert write_tool in write_tools
        assert mixed_tool in write_tools

    def test_extract_param_names_with_pydantic_fields(self):
        """Pydantic 필드를 가진 파라미터 이름 추출 테스트"""
        # Given
        mock_fields = Mock()
        mock_fields.__fields__ = {"path": Mock(), "content": Mock()}
        
        # When
        param_names = self.workflow._extract_param_names(mock_fields)
        
        # Then
        assert param_names == ["path", "content"]

    def test_extract_param_names_with_dict(self):
        """딕셔너리 형태 파라미터 이름 추출 테스트"""
        # Given
        param_dict = {"path": "str", "content": "str"}
        
        # When
        param_names = self.workflow._extract_param_names(param_dict)
        
        # Then
        assert param_names == ["path", "content"]

    @pytest.mark.asyncio
    async def test_extract_file_path_success(self):
        """파일 경로 추출 성공 테스트"""
        # Given
        user_message = "test.py 파일을 수정해주세요"
        mock_response = Mock()
        mock_response.response = "/workspace/test.py"
        self.mock_agent.llm_service.generate_response.return_value = mock_response
        
        with patch('os.path.exists', return_value=True):
            with patch('os.path.isabs', return_value=True):
                # When
                result = await self.workflow._extract_file_path(
                    self.mock_agent, user_message
                )
                
                # Then
                assert result == "/workspace/test.py"

    @pytest.mark.asyncio
    async def test_extract_file_path_none_response(self):
        """파일 경로 추출 시 NONE 응답 테스트"""
        # Given
        user_message = "코드를 개선해주세요"  # 파일 경로 없음
        mock_response = Mock()
        mock_response.response = "NONE"
        self.mock_agent.llm_service.generate_response.return_value = mock_response
        
        # When
        result = await self.workflow._extract_file_path(
            self.mock_agent, user_message
        )
        
        # Then
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_file_path_file_not_exists(self):
        """파일 경로 추출 시 파일이 존재하지 않는 경우 테스트"""
        # Given
        user_message = "nonexistent.py 파일을 수정해주세요"
        mock_response = Mock()
        mock_response.response = "/workspace/nonexistent.py"
        self.mock_agent.llm_service.generate_response.return_value = mock_response
        
        with patch('os.path.exists', return_value=False):
            # When
            result = await self.workflow._extract_file_path(
                self.mock_agent, user_message
            )
            
            # Then
            assert result is None

    @pytest.mark.asyncio
    async def test_read_file_content_success(self):
        """파일 내용 읽기 성공 테스트"""
        # Given
        file_path = "/test/example.py"
        file_content = "def hello():\n    print('hello')"
        
        with patch("builtins.open", mock_open(read_data=file_content)):
            # When
            result = await self.workflow._read_file_content(file_path)
            
            # Then
            assert result == file_content

    @pytest.mark.asyncio
    async def test_read_file_content_failure(self):
        """파일 내용 읽기 실패 테스트"""
        # Given
        file_path = "/test/nonexistent.py"
        
        with patch("builtins.open", side_effect=FileNotFoundError()):
            # When
            result = await self.workflow._read_file_content(file_path)
            
            # Then
            assert result is None

    @pytest.mark.asyncio
    async def test_modify_code_with_llm_success(self):
        """LLM 코드 수정 성공 테스트"""
        # Given
        original_code = "def hello():\n    print('hello')"
        user_message = "인사말을 더 친근하게 바꿔주세요"
        expected_code = "def hello():\n    print('Hello, friend!')"
        
        mock_response = Mock()
        mock_response.response = f"```python\n{expected_code}\n```"
        self.mock_agent.llm_service.generate_response.return_value = mock_response
        
        # When
        result = await self.workflow._modify_code_with_llm(
            self.mock_agent, original_code, user_message
        )
        
        # Then
        assert result == expected_code

    @pytest.mark.asyncio
    async def test_modify_code_with_llm_no_code_blocks(self):
        """LLM 코드 수정 시 코드 블록이 없는 경우 테스트"""
        # Given
        original_code = "def hello():\n    print('hello')"
        user_message = "인사말을 바꿔주세요"
        response_text = "def hello():\n    print('Hello, world!')"
        
        mock_response = Mock()
        mock_response.response = response_text
        self.mock_agent.llm_service.generate_response.return_value = mock_response
        
        # When
        result = await self.workflow._modify_code_with_llm(
            self.mock_agent, original_code, user_message
        )
        
        # Then
        assert result == response_text

    @pytest.mark.asyncio
    async def test_write_file_content_success(self):
        """파일 내용 쓰기 성공 테스트"""
        # Given
        file_path = "/test/example.py"
        content = "def hello():\n    print('Hello, World!')"
        
        with patch("builtins.open", mock_open()) as mock_file:
            # When
            result = await self.workflow._write_file_content(file_path, content)
            
            # Then
            assert result is True
            mock_file.assert_called_once_with(file_path, 'w', encoding='utf-8')
            mock_file().write.assert_called_once_with(content)

    @pytest.mark.asyncio
    async def test_write_file_content_failure(self):
        """파일 내용 쓰기 실패 테스트"""
        # Given
        file_path = "/test/readonly.py"
        content = "def hello():\n    print('Hello, World!')"
        
        with patch("builtins.open", side_effect=PermissionError()):
            # When
            result = await self.workflow._write_file_content(file_path, content)
            
            # Then
            assert result is False

    @pytest.mark.asyncio
    async def test_run_exception_handling(self):
        """워크플로우 실행 중 예외 처리 테스트"""
        # Given
        user_message = "test.py 파일을 수정해주세요"
        # 올바른 Mock 도구 설정
        mock_read_tool = self._create_mock_tool("read_file", ["path"])
        mock_write_tool = self._create_mock_tool("write_file", ["path", "content"])
        self.mock_agent.mcp_tool_manager.get_langchain_tools.return_value = [
            mock_read_tool, mock_write_tool
        ]
        
        # 파일 경로 추출에서 예외 발생
        with patch.object(self.workflow, '_extract_file_path', side_effect=Exception("Test error")):
            # When
            result = await self.workflow.run(
                self.mock_agent, user_message, self.mock_streaming_callback
            )
            
            # Then
            assert "코드 수정 중 오류가 발생했습니다" in result
            assert "Test error" in result

    def _create_mock_tool(self, name: str, param_names: List[str]) -> Mock:
        """Mock 도구 생성 헬퍼 메서드"""
        tool = Mock()
        tool.name = name
        tool.description = f"Mock {name} tool"
        
        # Mock args with __fields__
        mock_args = Mock()
        mock_args.__fields__ = {param: Mock() for param in param_names}
        tool.args = mock_args
        
        return tool


# 커버리지 검증을 위한 추가 테스트
class TestCodeModificationWorkflowEdgeCases:
    """CodeModificationWorkflow 엣지 케이스 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.workflow = CodeModificationWorkflow()

    def test_extract_param_names_with_empty_fields(self):
        """빈 필드를 가진 파라미터 이름 추출 테스트"""
        # Given
        mock_fields = Mock()
        mock_fields.__fields__ = {}
        
        # When
        param_names = self.workflow._extract_param_names(mock_fields)
        
        # Then
        assert param_names == []

    def test_extract_param_names_with_invalid_object(self):
        """잘못된 객체를 가진 파라미터 이름 추출 테스트"""
        # Given
        invalid_fields = "not_a_dict_or_object"
        
        # When
        param_names = self.workflow._extract_param_names(invalid_fields)
        
        # Then
        assert param_names == []

    def test_find_tools_with_no_args(self):
        """args가 없는 도구 탐지 테스트"""
        # Given
        tool_without_args = Mock()
        tool_without_args.name = "no_args_tool"
        tool_without_args.args = None
        tool_without_args.args_schema = None
        
        # When
        read_tools = self.workflow._find_read_tools([tool_without_args])
        write_tools = self.workflow._find_write_tools([tool_without_args])
        
        # Then
        assert len(read_tools) == 0
        assert len(write_tools) == 0 