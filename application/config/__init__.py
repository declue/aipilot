"""
DSPilot 확장 가능한 설정 관리 시스템

이 패키지는 두 부분으로 구성됩니다:
1. libs: 재사용 가능한 설정 관리 라이브러리 (독립적으로 사용 가능)
2. apps: DSPilot 애플리케이션별 설정 관리자들

구조:
- application.config.libs: 재사용 가능한 컴포넌트들
- application.config.apps: 애플리케이션별 구현체들
"""

# ========== 재사용 가능한 라이브러리 컴포넌트들 ==========
from .libs import (
    # 핵심 인터페이스
    ConfigType,
    ValidationResult,
    ConfigValue,
    ConfigDict,
    ConfigChangeCallback,
    IConfigValidator,
    IConfigSerializer,
    IConfigManager,
    IConfigWatcher,
    IConfigRegistry,
    IConfigFactory,
    
    # 기본 구현체
    BaseConfigManager,
    GenericConfigManager,
    
    # 직렬화기
    JSONConfigSerializer,
    YAMLConfigSerializer,
    TOMLConfigSerializer,
    INIConfigSerializer,
    SerializerFactory,
    
    # 검증기
    SchemaValidator,
    CompositeValidator,
    LLMConfigValidator,
    MCPConfigValidator,
    GitHubConfigValidator,
    create_schema_validator,
    
    # 유틸리티
    get_nested_value,
    set_nested_value,
    has_nested_key,
    remove_nested_key,
    merge_configs,
    detect_config_type,
    ensure_config_dir,
    backup_config_file,
    
    # 레지스트리 및 팩토리
    ConfigRegistry,
    ConfigFactory,
    get_config_registry,
    get_config_factory,
    register_config_manager,
    get_config_manager,
    create_config_manager,
    initialize_config_system,
    quick_setup,
    create_minimal_manager,
    
    # 설정 변경 감지
    get_config_change_notifier,
    ConfigChangeNotifier,
)

# ========== 애플리케이션별 구현체들 ==========
from .apps import (
    # 애플리케이션별 관리자들
    ModernAppConfigManager,
    ModernLLMProfileManager, 
    ModernMCPConfigManager,
    
    # 기본 설정값들
    DEFAULT_APP_CONFIG_SECTIONS,
    DEFAULT_UI_VALUES,
    DEFAULT_LLM_PROFILES,
    DEFAULT_LLM_PROFILE,
)

# ========== 하위 호환성을 위한 기존 모듈들 ==========
from .github_notification_config import GitHubNotificationConfig

# 기존 관리자들 (레거시 지원)
try:
    from .apps.managers.app_config_manager import AppConfigManager
    from .apps.managers.llm_profile_manager import LLMProfileManager
    from .apps.managers.mcp_config_manager import MCPConfigManager
except ImportError:
    # 기존 관리자가 없으면 새로운 관리자로 대체
    AppConfigManager = ModernAppConfigManager
    LLMProfileManager = ModernLLMProfileManager
    MCPConfigManager = ModernMCPConfigManager

__all__ = [
    # ========== 재사용 가능한 라이브러리 ==========
    # 핵심 인터페이스
    "ConfigType",
    "ValidationResult",
    "ConfigValue",
    "ConfigDict",
    "ConfigChangeCallback",
    "IConfigValidator",
    "IConfigSerializer",
    "IConfigManager",
    "IConfigWatcher",
    "IConfigRegistry",
    "IConfigFactory",
    
    # 기본 구현체
    "BaseConfigManager",
    "GenericConfigManager",
    
    # 직렬화기
    "JSONConfigSerializer",
    "YAMLConfigSerializer",
    "TOMLConfigSerializer",
    "INIConfigSerializer",
    "SerializerFactory",
    
    # 검증기
    "SchemaValidator",
    "CompositeValidator",
    "LLMConfigValidator",
    "MCPConfigValidator",
    "GitHubConfigValidator",
    "create_schema_validator",
    
    # 유틸리티
    "get_nested_value",
    "set_nested_value",
    "has_nested_key",
    "remove_nested_key",
    "merge_configs",
    "detect_config_type",
    "ensure_config_dir",
    "backup_config_file",
    
    # 레지스트리 및 팩토리
    "ConfigRegistry",
    "ConfigFactory",
    "get_config_registry",
    "get_config_factory",
    "register_config_manager",
    "get_config_manager",
    "create_config_manager",
    "initialize_config_system",
    "quick_setup",
    "create_minimal_manager",
    
    # 설정 변경 감지
    "get_config_change_notifier",
    "ConfigChangeNotifier",
    
    # ========== 애플리케이션별 구현체들 ==========
    # 현대적인 관리자들
    "ModernAppConfigManager",
    "ModernLLMProfileManager", 
    "ModernMCPConfigManager",
    
    # 기존 관리자들 (하위 호환성)
    "AppConfigManager",
    "LLMProfileManager",
    "MCPConfigManager",
    
    # 기본 설정값들
    "DEFAULT_APP_CONFIG_SECTIONS",
    "DEFAULT_UI_VALUES",
    "DEFAULT_LLM_PROFILES",
    "DEFAULT_LLM_PROFILE",
    
    # 기타
    "GitHubNotificationConfig",
]
