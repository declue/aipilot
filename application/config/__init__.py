"""
확장 가능한 설정 관리 시스템

독립 라이브러리로 분기 가능하도록 설계된 설정 관리 시스템입니다.

주요 기능:
- 다양한 설정 파일 형식 지원 (JSON, INI, YAML, TOML)
- 플러그인 방식의 확장 가능한 구조
- 실시간 파일 변경 감지 및 자동 리로드
- 스키마 기반 설정 검증
- 중앙화된 설정 관리 레지스트리

사용 예시:
    >>> from application.config import create_config_manager, register_config_manager
    
    # 새로운 설정 관리자 생성
    >>> manager = create_config_manager("app.json", ConfigType.JSON)
    
    # 설정값 조작
    >>> manager.set_value("app.name", "MyApp")
    >>> manager.set_value("database.host", "localhost")
    >>> print(manager.get_value("app.name"))
    
    # 레지스트리에 등록
    >>> register_config_manager("app", manager)
"""

import logging
# 핵심 인터페이스들
from .libs.interfaces import (
    ConfigType,
    ConfigDict,
    ConfigValue,
    ConfigChangeCallback,
    ValidationResult,
    IConfigManager,
    IConfigValidator,
    IConfigSerializer,
    IConfigWatcher,
    IConfigRegistry,
    IConfigFactory,
)

# 기본 구현체들
from .libs.base_config_manager import BaseConfigManager
from .libs.generic_config_manager import GenericConfigManager

# 직렬화기들
from .libs.serializers import (
    JSONConfigSerializer,
    INIConfigSerializer,
    YAMLConfigSerializer,
    TOMLConfigSerializer,
    SerializerFactory,
    serialize_config,
    deserialize_config,
)

# 검증기들
from .libs.validators import (
    SchemaValidator,
    LLMConfigValidator,
    MCPConfigValidator,
    GitHubConfigValidator,
    CompositeValidator,
    create_llm_validator,
    create_mcp_validator,
    create_github_validator,
    create_schema_validator,
    create_composite_validator,
)

# 유틸리티 함수들
from .libs.utils import (
    get_nested_value,
    set_nested_value,
    has_nested_key,
    remove_nested_key,
    merge_configs,
    flatten_config,
    unflatten_config,
    detect_config_type,
    ensure_config_dir,
    backup_config_file,
    validate_config_structure,
    sanitize_config_value,
    get_config_file_info,
)

# 레지스트리 및 팩토리
from .libs.registry import (
    ConfigRegistry,
    ConfigFactory,
    get_config_registry,
    get_config_factory,
    register_config_manager,
    get_config_manager,
    create_config_manager,
    reload_all_configs,
    cleanup_all_configs,
)

# 마이그레이션된 관리자들
from .libs.migrated_managers import (
    ModernAppConfigManager,
    ModernLLMProfileManager,
    ModernMCPConfigManager,
)

# 파일 변경 감지 (기존)
from .libs.config_change_notifier import (
    get_config_change_notifier,
)

# 기본 설정들
from .apps.defaults.default_app_config import *
from .apps.defaults.default_llm_profiles import *

logger = logging.getLogger(__name__)
logger.info("설정 시스템 초기화 완료")

# 버전 정보
__version__ = "2.0.0"
__author__ = "DSPilot Team"

# 모든 공개 API
__all__ = [
    # 핵심 인터페이스
    "ConfigType",
    "ConfigDict",
    "ConfigValue",
    "ConfigChangeCallback",
    "ValidationResult",
    "IConfigManager",
    "IConfigValidator",
    "IConfigSerializer",
    "IConfigWatcher",
    "IConfigRegistry",
    "IConfigFactory",

    # 기본 구현체
    "BaseConfigManager",
    "GenericConfigManager",

    # 직렬화기
    "JSONConfigSerializer",
    "INIConfigSerializer",
    "YAMLConfigSerializer",
    "TOMLConfigSerializer",
    "SerializerFactory",
    "serialize_config",
    "deserialize_config",

    # 검증기
    "SchemaValidator",
    "LLMConfigValidator",
    "MCPConfigValidator",
    "GitHubConfigValidator",
    "CompositeValidator",
    "create_llm_validator",
    "create_mcp_validator",
    "create_github_validator",
    "create_schema_validator",
    "create_composite_validator",

    # 유틸리티
    "get_nested_value",
    "set_nested_value",
    "has_nested_key",
    "remove_nested_key",
    "merge_configs",
    "flatten_config",
    "unflatten_config",
    "detect_config_type",
    "ensure_config_dir",
    "backup_config_file",
    "validate_config_structure",
    "sanitize_config_value",
    "get_config_file_info",

    # 레지스트리 및 팩토리
    "ConfigRegistry",
    "ConfigFactory",
    "get_config_registry",
    "get_config_factory",
    "register_config_manager",
    "get_config_manager",
    "create_config_manager",
    "reload_all_configs",
    "cleanup_all_configs",

    # 마이그레이션된 관리자들
    "ModernAppConfigManager",
    "ModernLLMProfileManager",
    "ModernMCPConfigManager",

    # 파일 변경 감지
    "get_config_change_notifier",
]


def initialize_config_system() -> None:
    """설정 시스템 초기화

    기본 관리자 클래스들을 팩토리에 등록합니다.
    """
    factory = get_config_factory()

    # 기본 관리자 클래스들 등록
    factory.register_manager_class("app", ModernAppConfigManager)
    factory.register_manager_class("llm", ModernLLMProfileManager)
    factory.register_manager_class("mcp", ModernMCPConfigManager)
    factory.register_manager_class("generic", GenericConfigManager)

    # 기본 검증기들 등록
    factory.register_default_validator(
        ConfigType.JSON, create_composite_validator())




def quick_setup(config_files: dict) -> dict:
    """빠른 설정 시스템 설정

    Args:
        config_files: 설정 파일 매핑 
            {
                'app': 'app.config',
                'llm': 'llm_profiles.json',
                'mcp': 'mcp.json'
            }

    Returns:
        생성된 관리자들의 딕셔너리
    """
    initialize_config_system()

    managers = {}
    factory = get_config_factory()
    registry = get_config_registry()

    for name, config_file in config_files.items():
        try:
            # 설정 타입 감지
            config_type = detect_config_type(config_file)

            # 관리자 생성
            manager = factory.create_manager(
                config_file=config_file,
                config_type=config_type,
                manager_type=name if name in [
                    "app", "llm", "mcp"] else "generic"
            )

            # 레지스트리에 등록
            registry.register_manager(name, manager)
            managers[name] = manager

        except Exception as e:
            logger.error("설정 관리자 '%s' 생성 실패: %s", name, e)

    return managers


def create_minimal_manager(config_file: str, default_config: dict = None) -> IConfigManager:
    """최소한의 설정 관리자 생성 (독립 실행용)

    Args:
        config_file: 설정 파일 경로
        default_config: 기본 설정 딕셔너리

    Returns:
        설정 관리자 인스턴스
    """
    return GenericConfigManager(
        config_file=config_file,
        default_config=default_config or {},
        enable_file_watching=False  # 독립 실행 시에는 감시 비활성화
    )


# 모듈 로드 시 자동 초기화
try:
    initialize_config_system()
except Exception as e:
    logger.warning("설정 시스템 자동 초기화 실패: %s", e)
