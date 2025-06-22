"""
새로운 설정 시스템 사용 예시

이 파일은 새로운 설정 시스템을 어떻게 사용하는지 보여주는 예시들을 제공합니다.
"""

import logging

from . import (
    ConfigType,
    create_config_manager,
    register_config_manager,
    get_config_manager,
    create_minimal_manager,
    quick_setup,
    ModernAppConfigManager,
    ModernLLMProfileManager,
    ModernMCPConfigManager,
    create_schema_validator,
    GenericConfigManager,
)

logger = logging.getLogger(__name__)


def example_basic_usage():
    """기본 사용 예시"""
    print("\n=== 기본 사용 예시 ===")

    # 1. 간단한 설정 관리자 생성
    manager = create_config_manager("example.json", ConfigType.JSON)

    # 2. 설정값 조작
    manager.set_value("app.name", "MyApp")
    manager.set_value("app.version", "1.0.0")
    manager.set_value("database.host", "localhost")
    manager.set_value("database.port", 5432)

    # 3. 설정값 읽기
    print(f"앱 이름: {manager.get_value('app.name')}")
    print(f"DB 호스트: {manager.get_value('database.host')}")
    print(f"전체 설정: {manager.get_config_data()}")

    # 4. 섹션별 조작
    db_config = manager.get_section("database")
    print(f"데이터베이스 설정: {db_config}")

    manager.set_section("cache", {
        "type": "redis",
        "host": "localhost",
        "port": 6379
    })

    # 5. 설정 저장
    manager.save_config()
    print("설정이 example.json 파일에 저장되었습니다.")


def example_registry_usage():
    """레지스트리 사용 예시"""
    print("\n=== 레지스트리 사용 예시 ===")

    # 1. 여러 설정 관리자 생성 및 등록
    app_manager = ModernAppConfigManager("app.config")
    llm_manager = ModernLLMProfileManager("llm_profiles.json")
    mcp_manager = ModernMCPConfigManager("mcp.json")

    register_config_manager("app", app_manager)
    register_config_manager("llm", llm_manager)
    register_config_manager("mcp", mcp_manager)

    # 2. 레지스트리에서 관리자 가져오기
    app_mgr = get_config_manager("app")
    if app_mgr:
        app_mgr.set_value("UI.theme", "dark")
        print(f"UI 테마: {app_mgr.get_value('UI.theme')}")

    # 3. 모든 설정 리로드
    from . import reload_all_configs
    reload_all_configs()
    print("모든 설정이 리로드되었습니다.")


def example_quick_setup():
    """빠른 설정 예시"""
    print("\n=== 빠른 설정 예시 ===")

    # 한 번에 여러 설정 파일 설정
    config_files = {
        'app': 'app.config',
        'llm': 'llm_profiles.json',
        'mcp': 'mcp.json',
        'user': 'user_settings.json'
    }

    managers = quick_setup(config_files)

    print(f"생성된 관리자: {list(managers.keys())}")

    # 각 관리자 사용
    if 'app' in managers:
        managers['app'].set_value("app.debug", True)
        print(f"디버그 모드: {managers['app'].get_value('app.debug')}")

    if 'user' in managers:
        managers['user'].set_value("preferences.language", "ko")
        print(f"언어 설정: {managers['user'].get_value('preferences.language')}")


def example_custom_validator():
    """커스텀 검증기 예시"""
    print("\n=== 커스텀 검증기 예시 ===")

    # 커스텀 스키마 정의
    user_schema = {
        "required": ["user.name", "user.email"],
        "optional": ["user.age", "preferences.theme"],
        "types": {
            "user.name": str,
            "user.email": str,
            "user.age": int,
            "preferences.theme": str
        },
        "ranges": {
            "user.age": {"min": 0, "max": 150}
        },
        "patterns": {
            "user.email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        }
    }

    # 검증기 생성
    validator = create_schema_validator(user_schema)

    # 검증기를 포함한 관리자 생성
    manager = GenericConfigManager(
        config_file="user.json",
        validator=validator,
        default_config={
            "user": {
                "name": "홍길동",
                "email": "hong@example.com",
                "age": 30
            },
            "preferences": {
                "theme": "light"
            }
        }
    )

    # 올바른 값 설정
    manager.set_value("user.name", "김철수")
    manager.set_value("user.email", "kim@example.com")

    # 검증 실행
    validation_result = manager.validate_config()
    if validation_result.is_valid:
        print("설정이 유효합니다!")
    else:
        print(f"검증 오류: {validation_result.errors}")

    # 잘못된 값으로 테스트
    try:
        manager.set_value("user.email", "잘못된이메일")
        validation_result = manager.validate_config()
        if not validation_result.is_valid:
            print(f"예상된 검증 오류: {validation_result.errors}")
    except Exception as e:
        print(f"설정 오류: {e}")


def example_file_format_support():
    """다양한 파일 형식 지원 예시"""
    print("\n=== 다양한 파일 형식 지원 예시 ===")

    # JSON 형식
    json_manager = create_config_manager("config.json", ConfigType.JSON)
    json_manager.set_value("format", "JSON")
    json_manager.save_config()
    print("JSON 설정 저장됨")

    # INI 형식
    ini_manager = create_config_manager("config.ini", ConfigType.INI)
    ini_manager.set_value("format", "INI")
    ini_manager.save_config()
    print("INI 설정 저장됨")

    # YAML 형식 (PyYAML 설치 필요)
    try:
        yaml_manager = create_config_manager("config.yaml", ConfigType.YAML)
        yaml_manager.set_value("format", "YAML")
        yaml_manager.save_config()
        print("YAML 설정 저장됨")
    except ImportError:
        print("YAML 지원을 위해 PyYAML을 설치하세요: pip install PyYAML")

    # TOML 형식 (tomli, tomli-w 설치 필요)
    try:
        toml_manager = create_config_manager("config.toml", ConfigType.TOML)
        toml_manager.set_value("format", "TOML")
        toml_manager.save_config()
        print("TOML 설정 저장됨")
    except ImportError:
        print("TOML 지원을 위해 tomli, tomli-w을 설치하세요: pip install tomli tomli-w")


def example_minimal_standalone():
    """독립 실행 최소 예시"""
    print("\n=== 독립 실행 최소 예시 ===")

    # 파일 감시 없이 최소한의 관리자 생성
    manager = create_minimal_manager(
        "minimal.json",
        default_config={
            "service": {
                "name": "MinimalService",
                "port": 8080,
                "debug": False
            }
        }
    )

    # 기본 조작
    print(f"서비스 이름: {manager.get_value('service.name')}")
    manager.set_value("service.debug", True)
    print(f"디버그 모드: {manager.get_value('service.debug')}")

    # 설정 저장
    manager.save_config()
    print("최소 설정이 저장되었습니다.")


def example_migration_usage():
    """기존 코드 마이그레이션 예시"""
    print("\n=== 기존 코드 마이그레이션 예시 ===")

    # 새로운 ModernAppConfigManager 사용
    app_manager = ModernAppConfigManager()

    # 기존 방식과 동일한 API 제공
    ui_config = app_manager.get_ui_config()
    print(f"현재 UI 설정: {ui_config}")

    # UI 설정 변경
    app_manager.set_ui_config(
        font_family="Arial",
        font_size=16,
        chat_bubble_max_width=800,
        window_theme="dark"
    )
    print("UI 설정이 업데이트되었습니다.")

    # GitHub 설정
    app_manager.set_github_repositories(["owner/repo1", "owner/repo2"])
    github_config = app_manager.get_github_config()
    print(f"GitHub 설정: {github_config}")


def run_all_examples():
    """모든 예시 실행"""
    print("새로운 설정 시스템 예시 실행")
    print("=" * 50)

    try:
        example_basic_usage()
        example_registry_usage()
        example_quick_setup()
        example_custom_validator()
        example_file_format_support()
        example_minimal_standalone()
        example_migration_usage()

        print("\n" + "=" * 50)
        print("모든 예시가 성공적으로 실행되었습니다!")

    except Exception as e:
        logger.error("예시 실행 중 오류: %s", e)
        print(f"오류: {e}")

    finally:
        # 정리
        from . import cleanup_all_configs
        cleanup_all_configs()
        print("리소스 정리 완료")


if __name__ == "__main__":
    run_all_examples()
