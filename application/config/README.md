# 확장 가능한 설정 관리 시스템

DSPilot의 새로운 설정 관리 시스템은 확장성과 재사용성을 중시하여 설계된 독립적인 라이브러리입니다. 이 시스템은 다양한 설정 파일 형식을 지원하고, 플러그인 방식으로 새로운 기능을 쉽게 추가할 수 있습니다.

## 주요 특징

### 🔧 확장성 (Extensibility)
- **플러그인 아키텍처**: 새로운 설정 타입과 검증기를 쉽게 추가
- **팩토리 패턴**: 동적 설정 관리자 생성
- **인터페이스 기반**: 모든 컴포넌트가 인터페이스로 정의됨

### 🔄 재사용성 (Reusability)
- **독립 라이브러리**: 최소 의존성으로 다른 프로젝트에서 사용 가능
- **범용 설정 관리자**: 특별한 비즈니스 로직 없는 기본 관리자
- **유틸리티 함수**: 점 표기법, 설정 병합 등 범용 기능

### 🛡️ 안정성 (Reliability)
- **스키마 기반 검증**: JSON Schema를 활용한 설정 검증
- **자동 백업**: 설정 변경 시 자동 백업 생성
- **파일 변경 감지**: 실시간 설정 파일 변경 감지 및 리로드

### 🎯 유연성 (Flexibility)
- **다중 형식 지원**: JSON, YAML, TOML, INI 등 다양한 형식
- **점 표기법**: `app.database.host`와 같은 직관적인 키 접근
- **중앙화된 레지스트리**: 모든 설정 관리자를 중앙에서 관리

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                    사용자 애플리케이션                        │
└─────────────────────┬───────────────────────────────────────┘
                     │
┌─────────────────────┴───────────────────────────────────────┐
│                 공개 API (Public API)                      │
├─────────────────────────────────────────────────────────────┤
│  from application.config import (...)                      │
│  - 재사용 가능한 컴포넌트들 (libs)                           │
│  - 애플리케이션별 구현체들 (apps)                            │
└─────────────────────┬───────────────────────────────────────┘
                     │
┌─────────────────────┴───────────────────────────────────────┐
│                    모듈 구조                                │
├─────────────────────────────────────────────────────────────┤
│  application.config.libs/     │  application.config.apps/   │
│  ├── interfaces.py            │  ├── managers/              │
│  ├── base_config_manager.py   │  │   ├── migrated_managers.py│
│  ├── generic_config_manager.py│  │   ├── app_config_manager.py│
│  ├── serializers.py           │  │   ├── llm_profile_manager.py│
│  ├── validators.py            │  │   └── mcp_config_manager.py│
│  ├── utils.py                 │  └── defaults/             │
│  ├── registry.py              │      ├── default_app_config.py│
│  └── config_change_notifier.py│      └── default_llm_profiles.py│
│                               │                             │
│  재사용 가능한 라이브러리        │  DSPilot 애플리케이션별 구현  │
│  (독립적으로 사용 가능)         │  (애플리케이션에 특화)        │
└─────────────────────┬───────────────────────────────────────┘
                     │
┌─────────────────────┴───────────────────────────────────────┐
│                     지원 서비스 계층                         │
├─────────────────────────────────────────────────────────────┤
│  직렬화기           │  검증기           │  유틸리티           │
│  - JSON            │  - Schema         │  - 점 표기법        │
│  - YAML            │  - LLM Config     │  - 설정 병합        │
│  - TOML            │  - MCP Config     │  - 파일 감지        │
│  - INI             │  - Composite      │  - 백업 관리        │
└─────────────────────────────────────────────────────────────┘
```

## 모듈 구조

### 1. `application.config.libs` - 재사용 가능한 라이브러리

독립적으로 사용 가능한 설정 관리 컴포넌트들:

- **`interfaces.py`**: 핵심 인터페이스 정의
- **`base_config_manager.py`**: 기본 설정 관리자 추상 클래스
- **`generic_config_manager.py`**: 범용 설정 관리자
- **`serializers.py`**: 다양한 형식의 직렬화기
- **`validators.py`**: 설정 검증기들
- **`utils.py`**: 유틸리티 함수들
- **`registry.py`**: 레지스트리 및 팩토리
- **`config_change_notifier.py`**: 파일 변경 감지

### 2. `application.config.apps` - 애플리케이션별 구현

DSPilot에 특화된 설정 관리자들:

- **`managers/`**: 애플리케이션별 관리자들
  - `migrated_managers.py`: 현대적인 관리자들 (Modern*)
  - `app_config_manager.py`: 기존 앱 설정 관리자
  - `llm_profile_manager.py`: 기존 LLM 프로필 관리자
  - `mcp_config_manager.py`: 기존 MCP 설정 관리자

- **`defaults/`**: 기본 설정값들
  - `default_app_config.py`: 앱 기본 설정
  - `default_llm_profiles.py`: LLM 기본 프로필

## 핵심 컴포넌트

### 1. 인터페이스 (libs/interfaces.py)

시스템의 모든 컴포넌트는 명확한 인터페이스로 정의됩니다:

```python
from application.config import ConfigType, IConfigManager, ValidationResult

# 설정 관리자 인터페이스
class IConfigManager(ABC):
    def get_value(self, key: str, fallback=None) -> ConfigValue
    def set_value(self, key: str, value: ConfigValue) -> None
    def validate_config(self) -> ValidationResult
    # ... 기타 메소드들
```

### 2. 직렬화기 (libs/serializers.py)

다양한 설정 파일 형식을 지원하는 직렬화기들:

```python
from application.config import SerializerFactory, ConfigType

# 직렬화기 팩토리
factory = SerializerFactory()
json_serializer = factory.create_serializer(ConfigType.JSON)
yaml_serializer = factory.create_serializer(ConfigType.YAML)
```

### 3. 검증기 (libs/validators.py)

설정 데이터의 유효성을 검증하는 검증기들:

```python
from application.config import SchemaValidator, create_schema_validator

# JSON Schema 기반 검증
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535}
    },
    "required": ["name"]
}

validator = create_schema_validator(schema)
result = validator.validate(config_data)
```

### 4. 레지스트리 & 팩토리 (libs/registry.py)

설정 관리자들을 중앙에서 관리하고 동적으로 생성:

```python
from application.config import register_config_manager, get_config_manager

# 관리자 등록
register_config_manager("app", app_manager)

# 관리자 조회
app_manager = get_config_manager("app")
```

## 사용 예시

### 재사용 가능한 라이브러리 사용

```python
from application.config import create_config_manager, ConfigType

# 1. 설정 관리자 생성
manager = create_config_manager("config.json", ConfigType.JSON)

# 2. 설정값 조작
manager.set_value("app.name", "MyApp")
manager.set_value("database.host", "localhost")
manager.set_value("database.port", 5432)

# 3. 설정값 조회 (점 표기법 지원)
app_name = manager.get_value("app.name")
db_config = manager.get_section("database")

# 4. 설정 저장
manager.save_config()
```

### 애플리케이션별 관리자 사용

```python
from application.config import ModernAppConfigManager, ModernLLMProfileManager

# DSPilot 앱 설정 관리자
app_manager = ModernAppConfigManager("app.config")
ui_config = app_manager.get_ui_config()

# LLM 프로필 관리자
llm_manager = ModernLLMProfileManager("llm_profiles.json")
current_profile = llm_manager.get_current_profile()
```

### 스키마 검증 사용

```python
from application.config import create_schema_validator, GenericConfigManager

# 1. 스키마 정의
schema = {
    "type": "object",
    "properties": {
        "app": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535}
            },
            "required": ["name", "version"]
        }
    },
    "required": ["app"]
}

# 2. 검증기 생성
validator = create_schema_validator(schema)

# 3. 검증 적용된 관리자 생성
manager = GenericConfigManager(
    config_file="app.json",
    validator=validator
)

# 4. 설정 검증
result = manager.validate_config()
if not result.is_valid:
    print("설정 오류:", result.errors)
```

## 고급 기능

### 1. 커스텀 설정 관리자 생성

```python
from application.config import BaseConfigManager

class MyCustomConfigManager(BaseConfigManager):
    def get_default_config(self) -> dict:
        return {
            "my_app": {
                "name": "Custom App",
                "version": "1.0.0"
            }
        }
    
    def on_config_changed(self, key: str, old_value, new_value):
        # 설정 변경 시 호출되는 후크
        print(f"설정 변경: {key} = {new_value}")
        
    def validate_custom_rules(self, config_data: dict) -> bool:
        # 커스텀 검증 로직
        return config_data.get("my_app", {}).get("name") is not None
```

### 2. 커스텀 검증기 생성

```python
from application.config import IConfigValidator, ValidationResult

class MyCustomValidator(IConfigValidator):
    def validate(self, config_data: dict) -> ValidationResult:
        result = ValidationResult()
        
        # 커스텀 검증 로직
        if "required_field" not in config_data:
            result.add_error("required_field is missing")
            
        return result
```

### 3. 설정 파일 변경 감지

```python
from application.config import BaseConfigManager

class WatchedConfigManager(BaseConfigManager):
    def __init__(self, config_file: str):
        super().__init__(config_file, enable_file_watching=True)
    
    def on_file_changed(self, file_path: str, change_type: str):
        print(f"설정 파일 변경 감지: {file_path} ({change_type})")
        self.force_reload()
```

## 마이그레이션 가이드

### 기존 코드에서 새 시스템으로 마이그레이션

```python
# 기존 코드
from application.config.app_config_manager import AppConfigManager
old_manager = AppConfigManager("app.config")

# 새로운 코드
from application.config import ModernAppConfigManager
new_manager = ModernAppConfigManager("app.json")

# API는 동일하게 유지됨
app_name = new_manager.get_value("application.name")
```

### 점진적 마이그레이션

1. **1단계**: 기존 관리자를 새로운 관리자로 교체
2. **2단계**: 설정 파일 형식을 JSON/YAML로 변경
3. **3단계**: 스키마 검증 추가
4. **4단계**: 레지스트리 시스템 도입

## 확장 가이드

### 새로운 설정 타입 추가

```python
# 1. 새로운 설정 타입 정의
class ConfigType(Enum):
    XML = "xml"  # 새로운 타입 추가

# 2. 직렬화기 구현
class XMLConfigSerializer(IConfigSerializer):
    def serialize(self, config_data: dict) -> str:
        # XML 직렬화 로직
        pass
    
    def deserialize(self, config_text: str) -> dict:
        # XML 역직렬화 로직
        pass

# 3. 팩토리에 등록
SerializerFactory.register_serializer(ConfigType.XML, XMLConfigSerializer)
```

### 새로운 도메인별 관리자 추가

```python
class DatabaseConfigManager(BaseConfigManager):
    def get_default_config(self) -> dict:
        return {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "mydb"
            }
        }
    
    def get_connection_string(self) -> str:
        db_config = self.get_section("database")
        return f"postgresql://{db_config['host']}:{db_config['port']}/{db_config['name']}"
```

## 독립 라이브러리로 사용

이 설정 시스템은 DSPilot 외부에서도 독립적으로 사용할 수 있습니다:

```python
# 최소 설정으로 사용
from application.config import create_minimal_manager

manager = create_minimal_manager(
    config_file="my_config.json",
    default_config={"app": {"name": "My App"}}
)

# 또는 전체 시스템 사용
from application.config import initialize_config_system, create_config_manager

initialize_config_system()
manager = create_config_manager("config.json")
```

## 성능 고려사항

### 메모리 효율성
- 지연 로딩: 필요한 시점에만 설정 로드
- 약한 참조: 사용하지 않는 관리자 자동 정리
- 캐싱: 자주 사용하는 설정값 캐싱

### 파일 I/O 최적화
- 변경 감지: 파일 수정 시에만 리로드
- 배치 저장: 여러 변경사항을 한번에 저장
- 비동기 저장: 백그라운드에서 저장 처리

## 테스트 가이드

### 단위 테스트

```python
import pytest
from application.config import GenericConfigManager

def test_config_manager():
    manager = GenericConfigManager("test_config.json")
    manager.set_value("test.key", "value")
    assert manager.get_value("test.key") == "value"
```

### 통합 테스트

```python
def test_config_system_integration():
    from application.config import initialize_config_system, quick_setup
    
    initialize_config_system()
    managers = quick_setup({"app": "app.json", "db": "db.json"})
    
    assert "app" in managers
    assert "db" in managers
```

## 트러블슈팅

### 일반적인 문제들

1. **파일 권한 오류**
   ```python
   # 해결: 파일 권한 확인
   import os
   if not os.access(config_file, os.R_OK | os.W_OK):
       raise PermissionError(f"설정 파일 접근 권한 없음: {config_file}")
   ```

2. **스키마 검증 실패**
   ```python
   # 해결: 상세한 오류 메시지 확인
   result = manager.validate_config()
   if not result.is_valid:
       for error in result.errors:
           print(f"검증 오류: {error}")
   ```

3. **파일 변경 감지 실패**
   ```python
   # 해결: 수동 리로드
   manager.force_reload()
   ```

## 기여 가이드

새로운 기능 추가나 버그 수정 시 다음 단계를 따라주세요:

1. **인터페이스 정의**: 새로운 기능에 대한 인터페이스 정의
2. **구현**: 인터페이스를 구현하는 클래스 작성
3. **테스트**: 포괄적인 단위 테스트 및 통합 테스트
4. **문서**: 사용법과 예시 문서 작성

## 로드맵

### v2.1 (예정)
- [ ] 비동기 설정 관리 지원
- [ ] 설정 히스토리 및 롤백 기능
- [ ] 클라우드 기반 설정 동기화

### v2.2 (예정)
- [ ] 설정 암호화 지원
- [ ] 환경별 설정 프로파일
- [ ] 설정 템플릿 시스템

### v3.0 (예정)
- [ ] 분산 설정 관리
- [ ] 실시간 설정 동기화
- [ ] 설정 변경 감사 로그 