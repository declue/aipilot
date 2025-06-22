"""
재사용 가능한 설정 관리 라이브러리

이 패키지는 독립적으로 사용 가능한 설정 관리 컴포넌트들을 포함합니다.
최소한의 의존성으로 다른 프로젝트에서도 재사용할 수 있도록 설계되었습니다.
"""

# 기본 구현체
from application.config.libs.base_config_manager import BaseConfigManager

# 설정 변경 감지
from application.config.libs.config_change_notifier import (
    ConfigChangeNotifier,
    get_config_change_notifier,
)
from application.config.libs.generic_config_manager import GenericConfigManager

# 핵심 인터페이스
from application.config.libs.interfaces import (
    ConfigChangeCallback,
    ConfigDict,
    ConfigType,
    ConfigValue,
    IConfigFactory,
    IConfigManager,
    IConfigRegistry,
    IConfigSerializer,
    IConfigValidator,
    IConfigWatcher,
    ValidationResult,
)

# 레지스트리 및 팩토리
from application.config.libs.registry import (
    ConfigFactory,
    ConfigRegistry,
    create_config_manager,
    create_minimal_manager,
    get_config_factory,
    get_config_manager,
    get_config_registry,
    initialize_config_system,
    quick_setup,
    register_config_manager,
)

# 직렬화기
from application.config.libs.serializers import (
    INIConfigSerializer,
    JSONConfigSerializer,
    SerializerFactory,
    TOMLConfigSerializer,
    YAMLConfigSerializer,
)

# 유틸리티
from application.config.libs.utils import (
    backup_config_file,
    detect_config_type,
    ensure_config_dir,
    get_nested_value,
    has_nested_key,
    merge_configs,
    remove_nested_key,
    set_nested_value,
)

# 검증기
from application.config.libs.validators import (
    CompositeValidator,
    GitHubConfigValidator,
    LLMConfigValidator,
    MCPConfigValidator,
    SchemaValidator,
    create_schema_validator,
)

__all__ = [
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
]
