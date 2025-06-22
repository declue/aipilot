"""
새로운 설정 관리 시스템 테스트

확장 가능한 설정 시스템의 핵심 기능들을 테스트합니다.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch

# Optional imports
try:
    import yaml
except ImportError:
    yaml = None

try:
    import tomli
except ImportError:
    tomli = None

from application.config import (
    # 핵심 인터페이스
    ConfigType,
    ValidationResult,
    
    # 기본 구현체
    BaseConfigManager,
    GenericConfigManager,
    
    # 직렬화기
    JSONConfigSerializer,
    YAMLConfigSerializer,
    TOMLConfigSerializer,
    SerializerFactory,
    
    # 검증기
    SchemaValidator,
    CompositeValidator,
    create_schema_validator,
    
    # 유틸리티
    get_nested_value,
    set_nested_value,
    has_nested_key,
    remove_nested_key,
    merge_configs,
    detect_config_type,
    
    # 레지스트리 및 팩토리
    ConfigRegistry,
    ConfigFactory,
    get_config_registry,
    get_config_factory,
    register_config_manager,
    get_config_manager,
    create_config_manager,
    
    # 애플리케이션별 관리자들
    ModernAppConfigManager,
    ModernLLMProfileManager,
    ModernMCPConfigManager,
    
    # 시스템 초기화
    initialize_config_system,
    quick_setup,
    create_minimal_manager,
)


class TestConfigInterfaces:
    """핵심 인터페이스 테스트"""
    
    def test_config_type_enum(self):
        """ConfigType enum 테스트"""
        assert ConfigType.JSON.value == "json"
        assert ConfigType.YAML.value == "yaml"
        assert ConfigType.TOML.value == "toml"
        assert ConfigType.INI.value == "ini"
    
    def test_validation_result(self):
        """ValidationResult 테스트"""
        # 성공 케이스
        result = ValidationResult(True)
        assert result.is_valid is True
        assert bool(result) is True
        assert len(result.errors) == 0
        
        # 실패 케이스 
        result = ValidationResult(False, ["error1", "error2"])
        assert result.is_valid is False
        assert bool(result) is False
        assert len(result.errors) == 2
        
        # 에러 추가
        result = ValidationResult()
        result.add_error("test error")
        assert result.is_valid is False
        assert len(result.errors) == 1


class TestConfigSerializers:
    """설정 직렬화기 테스트"""
    
    def test_json_serializer(self):
        """JSON 직렬화기 테스트"""
        serializer = JSONConfigSerializer()
        config_data = {"name": "test", "values": [1, 2, 3], "nested": {"key": "value"}}
        
        # 직렬화
        serialized = serializer.serialize(config_data)
        assert isinstance(serialized, str)
        
        # 역직렬화
        deserialized = serializer.deserialize(serialized)
        assert deserialized == config_data
    
    def test_yaml_serializer(self):
        """YAML 직렬화기 테스트"""
        serializer = YAMLConfigSerializer()
        config_data = {"name": "test", "values": [1, 2, 3]}
        
        serialized = serializer.serialize(config_data)
        deserialized = serializer.deserialize(serialized)
        assert deserialized == config_data
    
    def test_toml_serializer(self):
        """TOML 직렬화기 테스트"""
        serializer = TOMLConfigSerializer()
        config_data = {"name": "test", "section": {"key": "value"}}
        
        serialized = serializer.serialize(config_data)
        deserialized = serializer.deserialize(serialized)
        assert deserialized == config_data
    
    def test_serializer_factory(self):
        """직렬화기 팩토리 테스트"""
        factory = SerializerFactory()
        
        # JSON 직렬화기 생성
        json_serializer = factory.create_serializer(ConfigType.JSON)
        assert isinstance(json_serializer, JSONConfigSerializer)
        
        # YAML 직렬화기 생성 (옵션)
        if yaml is not None:
            yaml_serializer = factory.create_serializer(ConfigType.YAML)
            assert isinstance(yaml_serializer, YAMLConfigSerializer)
        
        # 지원되는 타입 확인
        supported_types = factory.get_supported_types()
        assert ConfigType.JSON in supported_types


class TestConfigValidators:
    """설정 검증기 테스트"""
    
    def test_schema_validator(self):
        """스키마 검증기 테스트"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "number"}
            },
            "required": ["name"]
        }
        
        validator = SchemaValidator(schema)
        
        # 유효한 설정
        valid_config = {"name": "test", "version": 1.0}
        result = validator.validate(valid_config)
        assert result.is_valid is True
        
        # 무효한 설정 (필수 필드 누락)
        invalid_config = {"version": 1.0}
        result = validator.validate(invalid_config)
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_composite_validator(self):
        """복합 검증기 테스트"""
        schema1 = {"type": "object", "properties": {"name": {"type": "string"}}}
        schema2 = {"type": "object", "properties": {"version": {"type": "number"}}}
        
        validator1 = SchemaValidator(schema1)
        validator2 = SchemaValidator(schema2)
        composite = CompositeValidator([validator1, validator2])
        
        # 모든 검증 통과
        valid_config = {"name": "test", "version": 1.0}
        result = composite.validate(valid_config)
        assert result.is_valid is True
        
        # 일부 검증 실패
        invalid_config = {"name": "test", "version": "invalid"}
        result = composite.validate(invalid_config)
        assert result.is_valid is False


class TestConfigUtils:
    """설정 유틸리티 테스트"""
    
    def test_nested_value_operations(self):
        """중첩 값 조작 테스트"""
        config = {"app": {"name": "test", "database": {"host": "localhost"}}}
        
        # 값 가져오기
        assert get_nested_value(config, "app.name") == "test"
        assert get_nested_value(config, "app.database.host") == "localhost"
        assert get_nested_value(config, "app.missing", "default") == "default"
        
        # 값 설정
        set_nested_value(config, "app.port", 8080)
        assert config["app"]["port"] == 8080
        
        set_nested_value(config, "new.section.key", "value")
        assert config["new"]["section"]["key"] == "value"
        
        # 키 존재 확인
        assert has_nested_key(config, "app.name") is True
        assert has_nested_key(config, "app.missing") is False
        
        # 키 제거
        assert remove_nested_key(config, "app.port") is True
        assert "port" not in config["app"]
        assert remove_nested_key(config, "app.missing") is False
    
    def test_config_merging(self):
        """설정 병합 테스트"""
        config1 = {"app": {"name": "test1", "port": 8080}}
        config2 = {"app": {"name": "test2", "host": "localhost"}, "db": {"host": "db"}}
        
        merged = merge_configs(config1, config2)
        
        # config2의 값이 우선
        assert merged["app"]["name"] == "test2"
        # config1의 고유 값 유지
        assert merged["app"]["port"] == 8080
        # config2의 고유 값 추가
        assert merged["app"]["host"] == "localhost"
        assert merged["db"]["host"] == "db"
    
    def test_config_type_detection(self):
        """설정 파일 타입 감지 테스트"""
        assert detect_config_type("config.json") == ConfigType.JSON
        assert detect_config_type("config.yml") == ConfigType.YAML
        assert detect_config_type("config.yaml") == ConfigType.YAML
        assert detect_config_type("config.toml") == ConfigType.TOML
        assert detect_config_type("config.ini") == ConfigType.INI


class TestGenericConfigManager:
    """범용 설정 관리자 테스트"""
    
    def test_manager_creation_and_basic_operations(self):
        """관리자 생성 및 기본 연산 테스트"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"app": {"name": "test"}}, f)
            config_file = f.name
        
        try:
            manager = GenericConfigManager(config_file)
            
            # 설정 로드 확인
            assert manager.get_value("app.name") == "test"
            
            # 값 설정
            manager.set_value("app.version", "1.0")
            assert manager.get_value("app.version") == "1.0"
            
            # 섹션 조작
            section = manager.get_section("app")
            assert section["name"] == "test"
            assert section["version"] == "1.0"
            
            # 키 존재 확인
            assert manager.has_key("app.name") is True
            assert manager.has_key("app.missing") is False
            
            # 키 제거
            assert manager.remove_key("app.version") is True
            assert manager.has_key("app.version") is False
            
        finally:
            os.unlink(config_file)


class TestConfigRegistry:
    """설정 레지스트리 테스트"""
    
    def test_registry_operations(self):
        """레지스트리 기본 연산 테스트"""
        registry = ConfigRegistry()
        
        # Mock 관리자 생성
        mock_manager = Mock()
        mock_manager.force_reload = Mock()
        mock_manager.cleanup = Mock()
        
        # 등록
        registry.register_manager("test", mock_manager)
        assert "test" in registry.list_managers()
        
        # 조회
        retrieved = registry.get_manager("test")
        assert retrieved is mock_manager
        
        # 리로드
        registry.reload_all()
        mock_manager.force_reload.assert_called_once()
        
        # 해제
        registry.unregister_manager("test")
        assert "test" not in registry.list_managers()
        mock_manager.cleanup.assert_called_once()
    
    def test_global_registry_functions(self):
        """전역 레지스트리 함수 테스트"""
        # Mock 관리자 생성
        mock_manager = Mock()
        
        # 등록
        register_config_manager("global_test", mock_manager)
        
        # 조회
        retrieved = get_config_manager("global_test")
        assert retrieved is mock_manager
        
        # 정리
        get_config_registry().unregister_manager("global_test")


class TestConfigFactory:
    """설정 팩토리 테스트"""
    
    def test_factory_creation(self):
        """팩토리를 통한 관리자 생성 테스트"""
        factory = ConfigFactory()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "value"}, f)
            config_file = f.name
        
        try:
            # 관리자 생성
            manager = factory.create_manager(config_file, ConfigType.JSON)
            assert isinstance(manager, GenericConfigManager)
            
            # 설정 확인
            assert manager.get_value("test") == "value"
            
        finally:
            os.unlink(config_file)
    
    def test_global_factory_function(self):
        """전역 팩토리 함수 테스트"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "value"}, f)
            config_file = f.name
        
        try:
            # 관리자 생성
            manager = create_config_manager(config_file, ConfigType.JSON)
            assert manager.get_value("test") == "value"
            
        finally:
            os.unlink(config_file)


class TestModernManagers:
    """마이그레이션된 관리자들 테스트"""
    
    def test_modern_app_config_manager(self):
        """ModernAppConfigManager 테스트"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            default_config = {
                "application": {
                    "name": "DSPilot",
                    "version": "1.0.0"
                }
            }
            json.dump(default_config, f)
            config_file = f.name
        
        try:
            manager = ModernAppConfigManager(config_file)
            assert manager.get_value("application.name") == "DSPilot"
            
        finally:
            os.unlink(config_file)
    
    def test_modern_llm_profile_manager(self):
        """ModernLLMProfileManager 테스트"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            profiles = {
                "profiles": {
                    "default": {
                        "provider": "openai",
                        "model": "gpt-4"
                    }
                }
            }
            json.dump(profiles, f)
            config_file = f.name
        
        try:
            manager = ModernLLMProfileManager(config_file)
            assert manager.get_value("profiles.default.provider") == "openai"
            
        finally:
            os.unlink(config_file)


class TestSystemIntegration:
    """시스템 통합 테스트"""
    
    def test_system_initialization(self):
        """시스템 초기화 테스트"""
        # 시스템 초기화 (예외 발생하지 않아야 함)
        initialize_config_system()
        
        # 전역 인스턴스 확인
        registry = get_config_registry()
        factory = get_config_factory()
        
        assert registry is not None
        assert factory is not None
    
    def test_quick_setup(self):
        """빠른 설정 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_files = {
                "app": os.path.join(temp_dir, "app.json"),
                "llm": os.path.join(temp_dir, "llm.json")
            }
            
            # 설정 파일 생성
            with open(config_files["app"], 'w') as f:
                json.dump({"name": "test"}, f)
            
            with open(config_files["llm"], 'w') as f:
                json.dump({"default_model": "gpt-4"}, f)
            
            # 빠른 설정
            managers = quick_setup(config_files)
            
            assert "app" in managers
            assert "llm" in managers
            assert managers["app"].get_value("name") == "test"
            assert managers["llm"].get_value("default_model") == "gpt-4"
    
    def test_create_minimal_manager(self):
        """최소 관리자 생성 테스트"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = f.name
        
        try:
            # 기본 설정으로 관리자 생성
            manager = create_minimal_manager(config_file, {"test": "value"})
            assert manager.get_value("test") == "value"
            
        finally:
            if os.path.exists(config_file):
                os.unlink(config_file)


if __name__ == "__main__":
    pytest.main([__file__]) 