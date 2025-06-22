"""
설정 관리 시스템의 핵심 인터페이스 정의

독립 라이브러리로 분기 가능하도록 최소한의 의존성으로 설계되었습니다.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class ConfigType(Enum):
    """설정 파일 타입"""

    INI = "ini"
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    XML = "xml"


class ValidationResult:
    """설정 검증 결과"""

    def __init__(self, is_valid: bool = True, errors: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []

    def add_error(self, error: str) -> None:
        """오류 추가"""
        self.is_valid = False
        self.errors.append(error)

    def __bool__(self) -> bool:
        return self.is_valid


# 타입 별칭
ConfigValue = Union[str, int, float, bool, List[Any], Dict[str, Any]]
ConfigDict = Dict[str, ConfigValue]
ConfigChangeCallback = Callable[[str, str], None]  # (file_path, change_type)


class IConfigValidator(ABC):
    """설정 검증기 인터페이스"""

    @abstractmethod
    def validate(self, config_data: ConfigDict) -> ValidationResult:
        """설정 데이터 검증

        Args:
            config_data: 검증할 설정 데이터

        Returns:
            검증 결과
        """


class IConfigSerializer(ABC):
    """설정 직렬화기 인터페이스"""

    @abstractmethod
    def serialize(self, config_data: ConfigDict) -> str:
        """설정 데이터를 문자열로 직렬화

        Args:
            config_data: 직렬화할 설정 데이터

        Returns:
            직렬화된 문자열
        """

    @abstractmethod
    def deserialize(self, config_text: str) -> ConfigDict:
        """문자열을 설정 데이터로 역직렬화

        Args:
            config_text: 역직렬화할 문자열

        Returns:
            설정 데이터
        """


class IConfigManager(ABC):
    """설정 관리자 인터페이스"""

    @property
    @abstractmethod
    def config_file(self) -> str:
        """설정 파일 경로"""

    @property
    @abstractmethod
    def config_type(self) -> ConfigType:
        """설정 파일 타입"""

    @abstractmethod
    def load_config(self) -> None:
        """설정 파일 로드"""

    @abstractmethod
    def save_config(self) -> None:
        """설정 파일 저장"""

    @abstractmethod
    def create_default_config(self) -> None:
        """기본 설정 생성"""

    @abstractmethod
    def get_config_data(self) -> ConfigDict:
        """전체 설정 데이터 반환"""

    @abstractmethod
    def set_config_data(self, config_data: ConfigDict) -> None:
        """전체 설정 데이터 설정"""

    @abstractmethod
    def get_value(self, key: str, fallback: Optional[ConfigValue] = None) -> ConfigValue:
        """설정값 가져오기 (점 표기법 지원)

        Args:
            key: 설정 키 (예: 'section.key' 또는 'nested.section.key')
            fallback: 기본값

        Returns:
            설정값
        """

    @abstractmethod
    def set_value(self, key: str, value: ConfigValue) -> None:
        """설정값 저장 (점 표기법 지원)

        Args:
            key: 설정 키 (예: 'section.key' 또는 'nested.section.key')
            value: 설정값
        """

    @abstractmethod
    def has_key(self, key: str) -> bool:
        """설정 키 존재 여부 확인"""

    @abstractmethod
    def remove_key(self, key: str) -> bool:
        """설정 키 제거

        Returns:
            제거 성공 여부
        """

    @abstractmethod
    def get_section(self, section: str) -> ConfigDict:
        """섹션 전체 반환"""

    @abstractmethod
    def set_section(self, section: str, data: ConfigDict) -> None:
        """섹션 전체 설정"""

    @abstractmethod
    def list_sections(self) -> List[str]:
        """모든 섹션 이름 반환"""

    @abstractmethod
    def validate_config(self) -> ValidationResult:
        """설정 검증"""

    def force_reload(self) -> None:
        """강제 리로드 (기본 구현)"""
        self.load_config()

    def cleanup(self) -> None:
        """리소스 정리 (기본 구현)"""


class IConfigWatcher(ABC):
    """설정 파일 감시자 인터페이스"""

    @abstractmethod
    def start_watching(self, file_path: str, callback: ConfigChangeCallback) -> None:
        """파일 감시 시작"""

    @abstractmethod
    def stop_watching(self, file_path: str, callback: ConfigChangeCallback) -> None:
        """파일 감시 중지"""

    @abstractmethod
    def stop_all(self) -> None:
        """모든 감시 중지"""


class IConfigRegistry(ABC):
    """설정 관리자 레지스트리 인터페이스"""

    @abstractmethod
    def register_manager(self, name: str, manager: IConfigManager) -> None:
        """설정 관리자 등록"""

    @abstractmethod
    def unregister_manager(self, name: str) -> None:
        """설정 관리자 해제"""

    @abstractmethod
    def get_manager(self, name: str) -> Optional[IConfigManager]:
        """설정 관리자 반환"""

    @abstractmethod
    def list_managers(self) -> List[str]:
        """등록된 관리자 이름 목록"""

    @abstractmethod
    def reload_all(self) -> None:
        """모든 설정 리로드"""

    @abstractmethod
    def cleanup_all(self) -> None:
        """모든 리소스 정리"""


class IConfigFactory(ABC):
    """설정 관리자 팩토리 인터페이스"""

    @abstractmethod
    def create_manager(
        self,
        config_file: str,
        config_type: ConfigType,
        validator: Optional[IConfigValidator] = None,
        **kwargs,
    ) -> IConfigManager:
        """설정 관리자 생성"""

    @abstractmethod
    def get_supported_types(self) -> List[ConfigType]:
        """지원되는 설정 타입 목록"""
