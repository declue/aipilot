import logging
import os
from abc import ABC, abstractmethod
from typing import List, Optional

from dspilot_core.config.libs.config_change_notifier import (
    ConfigChangeCallback,
    get_config_change_notifier,
)
from dspilot_core.config.libs.interfaces import (
    ConfigDict,
    ConfigType,
    ConfigValue,
    IConfigManager,
    IConfigSerializer,
    IConfigValidator,
    ValidationResult,
)
from dspilot_core.config.libs.serializers import SerializerFactory
from dspilot_core.config.libs.utils import (
    backup_config_file,
    detect_config_type,
    ensure_config_dir,
    get_nested_value,
    has_nested_key,
    remove_nested_key,
    set_nested_value,
)

# 로거 설정을 선택적으로 처리
try:
    from dspilot_core.util.logger import setup_logger

    logger: logging.Logger = setup_logger(
        "config") or logging.getLogger("config")
except ImportError:
    logger = logging.getLogger("config")


class BaseConfigManager(IConfigManager, ABC):
    """설정 관리자 기본 클래스

    파일 변경 감지 및 자동 리로드 기능을 제공하는 추상 기본 클래스입니다.
    모든 설정 관리자는 이 클래스를 상속받아 일관된 인터페이스를 제공합니다.
    """

    def __init__(
        self,
        config_file: str,
        serializer: Optional[IConfigSerializer] = None,
        validator: Optional[IConfigValidator] = None,
        auto_create_dir: bool = True,
        enable_file_watching: bool = True,
    ) -> None:
        """BaseConfigManager 생성자

        Args:
            config_file: 설정 파일 경로
            serializer: 설정 직렬화기 (None이면 파일 확장자로 자동 감지)
            validator: 설정 검증기
            auto_create_dir: 디렉토리 자동 생성 여부
            enable_file_watching: 파일 변경 감지 활성화 여부
        """
        self._config_file = config_file
        self._serializer = serializer
        self._validator = validator
        self._auto_create_dir = auto_create_dir
        self._enable_file_watching = enable_file_watching
        self._config_data: ConfigDict = {}

        # 파일 변경 감지 설정
        self._change_notifier = get_config_change_notifier()
        self._change_callback: Optional[ConfigChangeCallback] = None

        # 설정 파일 타입 감지
        try:
            self._config_type = detect_config_type(config_file)
        except ValueError:
            # 기본값으로 JSON 사용
            self._config_type = ConfigType.JSON
            logger.warning("설정 파일 타입을 감지할 수 없어 JSON을 사용합니다: %s", config_file)

        # 초기화
        if auto_create_dir:
            ensure_config_dir(config_file)

        # 설정 파일 로드
        self.load_config()

        if enable_file_watching:
            self._setup_change_detection()

    # ========== IConfigManager 인터페이스 구현 ==========

    @property
    def config_file(self) -> str:
        """설정 파일 경로"""
        return self._config_file

    @property
    def config_type(self) -> ConfigType:
        """설정 파일 타입"""
        return self._config_type

    def get_config_data(self) -> ConfigDict:
        """전체 설정 데이터 반환"""
        return self._config_data.copy()

    def set_config_data(self, config_data: ConfigDict) -> None:
        """전체 설정 데이터 설정"""
        self._config_data = config_data.copy()

    def get_value(self, key: str, fallback: Optional[ConfigValue] = None) -> ConfigValue:
        """설정값 가져오기 (점 표기법 지원)"""
        return get_nested_value(self._config_data, key, fallback)

    def set_value(self, key: str, value: ConfigValue) -> None:
        """설정값 저장 (점 표기법 지원)"""
        set_nested_value(self._config_data, key, value)

    def has_key(self, key: str) -> bool:
        """설정 키 존재 여부 확인"""
        return has_nested_key(self._config_data, key)

    def remove_key(self, key: str) -> bool:
        """설정 키 제거"""
        return remove_nested_key(self._config_data, key)

    def get_section(self, section: str) -> ConfigDict:
        """섹션 전체 반환"""
        return self.get_value(section, {})

    def set_section(self, section: str, data: ConfigDict) -> None:
        """섹션 전체 설정"""
        self.set_value(section, data)

    def list_sections(self) -> List[str]:
        """모든 섹션 이름 반환"""
        return list(self._config_data.keys())

    def validate_config(self) -> ValidationResult:
        """설정 검증"""
        if self._validator:
            return self._validator.validate(self._config_data)
        return ValidationResult(True)

    # ========== 기본 구현 메서드들 ==========

    def load_config(self) -> None:
        """설정 파일 로드 (기본 구현)"""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, "r", encoding="utf-8") as f:
                    content = f.read()

                if self._serializer:
                    self._config_data = self._serializer.deserialize(content)
                else:
                    # 직렬화기가 없으면 파일 타입에 따라 자동 생성
                    serializer = SerializerFactory.create_serializer(
                        self._config_type)
                    self._config_data = serializer.deserialize(content)

                logger.debug("설정 파일 로드 완료: %s", self._config_file)
            else:
                logger.info("설정 파일이 존재하지 않음, 기본 설정 생성: %s", self._config_file)
                self.create_default_config()
        except Exception as exception:
            # 파일이 있지만 파싱에 실패한 경우, 원본 파일을 보존하고 예외를 다시 던집니다
            logger.error("설정 파일 파싱 실패 (원본 파일 보존): %s", exception)
            logger.error("설정 파일 경로: %s", self._config_file)
            raise RuntimeError(
                f"설정 파일 '{self._config_file}' 파싱에 실패했습니다. 원본 파일을 확인하고 수정해주세요.") from exception

    def save_config(self) -> None:
        """설정 파일 저장 (기본 구현)"""
        try:
            # 디렉토리 생성
            if self._auto_create_dir:
                ensure_config_dir(self._config_file)

            # 백업 생성 (기존 파일이 있는 경우)
            if os.path.exists(self._config_file):
                backup_config_file(self._config_file)

            # 직렬화 및 저장
            if self._serializer:
                content = self._serializer.serialize(self._config_data)
            else:
                serializer = SerializerFactory.create_serializer(
                    self._config_type)
                content = serializer.serialize(self._config_data)

            with open(self._config_file, "w", encoding="utf-8") as f:
                f.write(content)

            logger.debug("설정 파일 저장 완료: %s", self._config_file)
        except Exception as exception:
            logger.error("설정 파일 저장 실패: %s", exception)
            raise

    # ========== 파일 변경 감지 ==========

    def _setup_change_detection(self) -> None:
        """파일 변경 감지 설정"""
        try:
            self._change_callback = self._on_config_changed
            self._change_notifier.register_callback(
                self._config_file, self._change_callback)
            logger.debug("파일 변경 감지 설정 완료: %s", self._config_file)
        except Exception as exception:
            logger.error("파일 변경 감지 설정 실패: %s", exception)

    def _on_config_changed(self, file_path: str, change_type: str) -> None:
        """파일 변경 이벤트 핸들러"""
        try:
            logger.info("설정 파일 변경 감지 [%s]: %s", change_type, file_path)

            if change_type == "deleted":
                logger.warning("설정 파일이 삭제됨: %s", file_path)
                # 파일이 삭제된 경우에만 기본 설정 생성
                self.create_default_config()
            else:
                # 파일이 수정되었지만 파싱에 실패하면 기존 설정을 유지
                try:
                    self.load_config()
                except Exception as load_exception:
                    logger.error("변경된 설정 파일 로드 실패 (기존 설정 유지): %s",
                                 load_exception)
                    # 기존 설정을 유지하고 사용자에게 알림
                    return

            # 하위 클래스의 추가 처리
            self.on_config_changed(file_path, change_type)

        except Exception as exception:
            logger.error("설정 파일 변경 처리 중 오류: %s", exception)

    def cleanup(self) -> None:
        """리소스 정리"""
        try:
            if self._change_callback and self._enable_file_watching:
                self._change_notifier.unregister_callback(
                    self._config_file, self._change_callback)
                self._change_callback = None
                logger.debug("파일 변경 감지 해제: %s", self._config_file)
        except Exception as exception:
            logger.error("리소스 정리 실패: %s", exception)

    def force_reload(self) -> None:
        """강제 리로드"""
        try:
            self.load_config()
            logger.info("설정 강제 리로드 완료: %s", self._config_file)
        except Exception as exception:
            logger.error("설정 강제 리로드 실패: %s", exception)

    # ========== 추상 메서드들 ==========

    @abstractmethod
    def create_default_config(self) -> None:
        """기본 설정 생성 (하위 클래스에서 구현)"""
        pass  # pylint: disable=unnecessary-pass

    @abstractmethod
    def get_default_config_data(self) -> ConfigDict:
        """기본 설정 데이터 반환 (하위 클래스에서 구현)"""
        pass  # pylint: disable=unnecessary-pass
    # ========== 후크 메서드들 ==========

    def on_config_changed(self, file_path: str, change_type: str) -> None:
        """설정 변경 후 추가 처리 (하위 클래스에서 오버라이드 가능)"""
        pass  # pylint: disable=unnecessary-pass

    def on_before_save(self) -> None:
        """저장 전 처리 (하위 클래스에서 오버라이드 가능)"""
        pass  # pylint: disable=unnecessary-pass

    def on_after_save(self) -> None:
        """저장 후 처리 (하위 클래스에서 오버라이드 가능)"""
        pass  # pylint: disable=unnecessary-pass

    def on_before_load(self) -> None:
        """로드 전 처리 (하위 클래스에서 오버라이드 가능)"""
        pass  # pylint: disable=unnecessary-pass

    def on_after_load(self) -> None:
        """로드 후 처리 (하위 클래스에서 오버라이드 가능)"""
        pass  # pylint: disable=unnecessary-pass

    def __del__(self) -> None:
        """소멸자"""
        try:
            self.cleanup()
        except Exception:
            pass
