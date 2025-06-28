"""
DSPilot 프롬프트 관리 모듈

프롬프트 템플릿들을 파일 기반으로 관리하고 동적으로 로드하는 시스템을 제공합니다.
SOLID 원칙을 따라 유연하고 확장 가능한 구조로 설계되었습니다.
"""

from dspilot_core.instructions.prompt_manager import (
    PromptManager,
    get_default_prompt_manager,
    get_prompt,
)

__all__ = [
    "PromptManager",
    "get_default_prompt_manager", 
    "get_prompt"
] 