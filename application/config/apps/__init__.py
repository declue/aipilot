"""
DSPilot 애플리케이션별 설정 관리자들

이 패키지는 DSPilot 애플리케이션에 특화된 설정 관리자들을 포함합니다.
libs 패키지의 재사용 가능한 컴포넌트들을 상속하여 구현됩니다.
"""

from .defaults.default_app_config import DEFAULT_APP_CONFIG_SECTIONS, DEFAULT_UI_VALUES
from .defaults.default_llm_profiles import DEFAULT_LLM_PROFILE, DEFAULT_LLM_PROFILES
from .managers.migrated_managers import (
    ModernAppConfigManager,
    ModernLLMProfileManager,
    ModernMCPConfigManager,
)

__all__ = [
    # 애플리케이션별 관리자들
    "ModernAppConfigManager",
    "ModernLLMProfileManager",
    "ModernMCPConfigManager",
    # 기본 설정값들
    "DEFAULT_APP_CONFIG_SECTIONS",
    "DEFAULT_UI_VALUES",
    "DEFAULT_LLM_PROFILES",
    "DEFAULT_LLM_PROFILE",
]
