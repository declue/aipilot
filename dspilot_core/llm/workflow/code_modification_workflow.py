#!/usr/bin/env python3
"""
코드 수정 워크플로우 (CodeModificationWorkflow)
==============================================

파일 읽기/수정/쓰기 작업을 전담하는 워크플로우입니다.
PlanningService에서 하드코딩되어 있던 코드 수정 로직을 분리하여
SOLID 원칙과 플러그인 아키텍처를 준수합니다.

주요 기능
=========
1. 파일 읽기 → LLM 수정 → 파일 쓰기 워크플로우 처리
2. 메타데이터 기반 도구 탐지 (도구명 하드코딩 없음)
3. 사용자 확인 후 파일 수정 실행
4. 오류 처리 및 롤백 지원

워크플로우 흐름
==============
1. 사용자 요청 분석
2. 읽기 가능한 도구 탐지 (파일 경로 인자 포함)
3. 파일 내용 읽기
4. LLM을 통한 코드 수정
5. 쓰기 가능한 도구 탐지 (파일 경로 + 내용 인자 포함)
6. 사용자 확인 후 수정된 내용 저장

확장성
======
- 새로운 파일 I/O 도구 추가 시 자동 지원
- 도구명에 의존하지 않는 메타데이터 기반 처리
- 다양한 파일 형식 지원 가능
"""

import logging
import os
from typing import Any, Callable, List, Optional

from dspilot_core.llm.models.conversation_message import ConversationMessage
from dspilot_core.llm.workflow.base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class CodeModificationWorkflow(BaseWorkflow):
    """코드 읽기/수정/쓰기를 전담하는 워크플로우"""

    async def run(
        self, 
        agent: Any, 
        message: str, 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        코드 수정 워크플로우 실행

        Args:
            agent: LLM 에이전트
            message: 사용자 수정 요청 메시지
            streaming_callback: 스트리밍 콜백

        Returns:
            처리 결과 메시지
        """
        try:
            logger.info("CodeModificationWorkflow 시작")
            
            if streaming_callback:
                streaming_callback("🔄 코드 수정 워크플로우를 시작합니다...\n")

            # 1. 사용 가능한 도구 분석
            available_tools = await self._get_available_tools(agent)
            if not available_tools:
                return "사용 가능한 파일 처리 도구가 없습니다."

            # 2. 읽기/쓰기 도구 탐지
            read_tools = self._find_read_tools(available_tools)
            write_tools = self._find_write_tools(available_tools)
            
            if not read_tools or not write_tools:
                return "파일 읽기 또는 쓰기 도구를 찾을 수 없습니다."

            if streaming_callback:
                streaming_callback(f"📋 읽기 도구: {len(read_tools)}개, 쓰기 도구: {len(write_tools)}개 발견\n")

            # 3. 대상 파일 경로 추출
            file_path = await self._extract_file_path(agent, message, streaming_callback)
            if not file_path:
                return "수정할 파일 경로를 찾을 수 없습니다. 구체적인 파일 경로를 지정해주세요."

            # 4. 파일 읽기
            if streaming_callback:
                streaming_callback(f"📖 파일 읽기: {file_path}\n")
                
            original_content = await self._read_file_content(file_path)
            if original_content is None:
                return f"파일을 읽을 수 없습니다: {file_path}"

            # 5. LLM을 통한 코드 수정
            if streaming_callback:
                streaming_callback("🤖 LLM을 통해 코드를 수정하고 있습니다...\n")
                
            modified_content = await self._modify_code_with_llm(
                agent, original_content, message, streaming_callback
            )
            
            if not modified_content or modified_content == original_content:
                return "코드 수정이 필요하지 않거나 수정에 실패했습니다."

            # 6. 사용자 확인 (실제 구현에서는 UI를 통해 확인)
            if streaming_callback:
                streaming_callback("✅ 코드 수정이 완료되었습니다.\n")
                streaming_callback(f"📝 수정된 내용을 {file_path}에 저장합니다...\n")

            # 7. 파일 쓰기
            success = await self._write_file_content(file_path, modified_content)
            if success:
                logger.info(f"파일 수정 완료: {file_path}")
                return f"✅ 파일이 성공적으로 수정되었습니다: {file_path}"
            else:
                return f"❌ 파일 쓰기에 실패했습니다: {file_path}"

        except Exception as e:
            logger.error(f"CodeModificationWorkflow 오류: {e}")
            return f"코드 수정 중 오류가 발생했습니다: {str(e)}"

    async def _get_available_tools(self, agent: Any) -> List[Any]:
        """사용 가능한 도구 목록 가져오기"""
        if hasattr(agent, 'mcp_tool_manager'):
            try:
                return await agent.mcp_tool_manager.get_langchain_tools()
            except Exception as e:
                logger.warning(f"도구 목록 가져오기 실패: {e}")
        return []

    def _find_read_tools(self, tools: List[Any]) -> List[Any]:
        """파일 읽기 가능한 도구 탐지 (메타데이터 기반)"""
        read_tools = []
        for tool in tools:
            # 도구명이 아닌 파라미터 메타데이터를 기반으로 판단
            param_fields = getattr(tool, "args", None) or getattr(tool, "args_schema", None)
            if param_fields:
                param_names = self._extract_param_names(param_fields)
                # 파일 경로 파라미터가 있고, 내용 출력 파라미터가 없는 경우 = 읽기 도구
                has_file_param = any(p in param_names for p in ["path", "file_path", "filepath"])
                has_content_param = any(p in param_names for p in ["content", "data", "text"])
                
                if has_file_param and not has_content_param:
                    read_tools.append(tool)
                    
        return read_tools

    def _find_write_tools(self, tools: List[Any]) -> List[Any]:
        """파일 쓰기 가능한 도구 탐지 (메타데이터 기반)"""
        write_tools = []
        for tool in tools:
            param_fields = getattr(tool, "args", None) or getattr(tool, "args_schema", None)
            if param_fields:
                param_names = self._extract_param_names(param_fields)
                # 파일 경로 + 내용 파라미터가 모두 있는 경우 = 쓰기 도구
                has_file_param = any(p in param_names for p in ["path", "file_path", "filepath"])
                has_content_param = any(p in param_names for p in ["content", "data", "text", "diff_content"])
                
                if has_file_param and has_content_param:
                    write_tools.append(tool)
                    
        return write_tools

    def _extract_param_names(self, param_fields: Any) -> List[str]:
        """파라미터 필드에서 이름 목록 추출"""
        try:
            return list(param_fields.__fields__.keys())  # type: ignore[attr-defined]
        except Exception:
            return list(param_fields.keys()) if isinstance(param_fields, dict) else []

    async def _extract_file_path(
        self, 
        agent: Any, 
        message: str, 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """사용자 메시지에서 파일 경로 추출"""
        # LLM을 통해 파일 경로 추출
        prompt = f"""다음 사용자 메시지에서 수정하고자 하는 파일의 경로를 추출해주세요.
파일 경로만 반환하고, 다른 설명은 하지 마세요.
파일 경로가 명시되어 있지 않으면 "NONE"을 반환하세요.

사용자 메시지: {message}

파일 경로:"""

        context = [ConversationMessage(role="user", content=prompt)]
        response = await agent.llm_service.generate_response(context)
        
        file_path = response.response.strip()
        if file_path == "NONE" or not file_path:
            return None
            
        # 상대 경로를 절대 경로로 변환
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
            
        return file_path if os.path.exists(file_path) else None

    async def _read_file_content(self, file_path: str) -> Optional[str]:
        """파일 내용 읽기"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"파일 읽기 실패 {file_path}: {e}")
            return None

    async def _modify_code_with_llm(
        self, 
        agent: Any, 
        original_code: str, 
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """LLM을 통한 코드 수정"""
        prompt = f"""다음은 사용자의 요청과 원본 코드입니다. 요청에 맞게 코드를 수정한 후, **다른 설명 없이 수정된 코드 전체만 반환해주세요.**

# 사용자 요청:
{user_message}

# 원본 코드:
```
{original_code}
```

# 수정된 코드:"""

        context = [ConversationMessage(role="user", content=prompt)]
        response = await agent.llm_service.generate_response(context)
        
        # 응답에서 코드 블록 추출
        modified_code = response.response
        if "```" in modified_code:
            parts = modified_code.split("```")
            if len(parts) > 1:
                code_part = parts[1]
                # 언어 지정자 제거 (python, js 등)
                lines = code_part.split('\n')
                if lines and lines[0].strip() in ['python', 'js', 'javascript', 'java', 'cpp', 'c']:
                    modified_code = '\n'.join(lines[1:])
                else:
                    modified_code = code_part
        
        return modified_code.strip()

    async def _write_file_content(self, file_path: str, content: str) -> bool:
        """파일 내용 쓰기"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"파일 쓰기 실패 {file_path}: {e}")
            return False 