"""
설정 관리자 레지스트리 및 팩토리 구현

동적으로 설정 관리자를 등록하고 생성할 수 있는 시스템을 제공합니다.
"""

import logging
import os
from typing import Dict, List, Optional, Type

from .interfaces import (
    IConfigManager, 
    IConfigRegistry, 
    IConfigFactory, 
    IConfigValidator,
    ConfigType,
    ConfigDict
)
from .base_config_manager import BaseConfigManager
from .generic_config_manager import GenericConfigManager

logger = logging.getLogger(__name__)


class ConfigRegistry(IConfigRegistry):
    """설정 관리자 레지스트리
    
    등록된 설정 관리자들을 중앙에서 관리합니다.
    """
    
    def __init__(self):
        self._managers: Dict[str, IConfigManager] = {}
        self._lock = threading.RLock()
    
    def register_manager(self, name: str, manager: IConfigManager) -> None:
        """설정 관리자 등록"""
        with self._lock:
            if name in self._managers:
                logger.warning("기존 설정 관리자를 덮어씁니다: %s", name)
            
            self._managers[name] = manager
            logger.info("설정 관리자 등록: %s (%s)", name, type(manager).__name__)
    
    def unregister_manager(self, name: str) -> None:
        """설정 관리자 해제"""
        with self._lock:
            if name in self._managers:
                manager = self._managers[name]
                manager.cleanup()
                del self._managers[name]
                logger.info("설정 관리자 해제: %s", name)
            else:
                logger.warning("설정 관리자를 찾을 수 없습니다: %s", name)
    
    def get_manager(self, name: str) -> Optional[IConfigManager]:
        """설정 관리자 반환"""
        with self._lock:
            return self._managers.get(name)
    
    def list_managers(self) -> List[str]:
        """등록된 관리자 이름 목록"""
        with self._lock:
            return list(self._managers.keys())
    
    def reload_all(self) -> None:
        """모든 설정 리로드"""
        with self._lock:
            for name, manager in self._managers.items():
                try:
                    manager.force_reload()
                    logger.debug("설정 리로드 완료: %s", name)
                except Exception as e:
                    logger.error("설정 리로드 실패 [%s]: %s", name, e)
    
    def cleanup_all(self) -> None:
        """모든 리소스 정리"""
        with self._lock:
            for name, manager in self._managers.items():
                try:
                    manager.cleanup()
                    logger.debug("리소스 정리 완료: %s", name)
                except Exception as e:
                    logger.error("리소스 정리 실패 [%s]: %s", name, e)
            
            self._managers.clear()
    
    def __del__(self):
        """소멸자"""
        try:
            self.cleanup_all()
        except Exception:
            pass


class ConfigFactory(IConfigFactory):
    """설정 관리자 팩토리
    
    설정 타입에 따라 적절한 관리자를 생성합니다.
    """
    
    def __init__(self):
        self._manager_classes: Dict[str, Type[BaseConfigManager]] = {}
        self._default_validators: Dict[ConfigType, IConfigValidator] = {}
    
    def register_manager_class(self, name: str, manager_class: Type[BaseConfigManager]) -> None:
        """설정 관리자 클래스 등록
        
        Args:
            name: 관리자 이름 (예: 'app', 'llm', 'mcp')
            manager_class: 관리자 클래스
        """
        self._manager_classes[name] = manager_class
        logger.info("설정 관리자 클래스 등록: %s -> %s", name, manager_class.__name__)
    
    def register_default_validator(self, config_type: ConfigType, validator: IConfigValidator) -> None:
        """기본 검증기 등록"""
        self._default_validators[config_type] = validator
        logger.info("기본 검증기 등록: %s -> %s", config_type, type(validator).__name__)
    
    def create_manager(
        self, 
        config_file: str, 
        config_type: ConfigType,
        validator: Optional[IConfigValidator] = None,
        manager_type: Optional[str] = None,
        **kwargs
    ) -> IConfigManager:
        """설정 관리자 생성
        
        Args:
            config_file: 설정 파일 경로
            config_type: 설정 파일 타입
            validator: 설정 검증기
            manager_type: 관리자 타입 (등록된 클래스 이름)
            **kwargs: 추가 생성 옵션
            
        Returns:
            설정 관리자 인스턴스
        """
        try:
            # 검증기 설정
            if validator is None and config_type in self._default_validators:
                validator = self._default_validators[config_type]
            
            # 관리자 클래스 선택
            if manager_type and manager_type in self._manager_classes:
                manager_class = self._manager_classes[manager_type]
            else:
                # 기본 관리자 사용
                manager_class = GenericConfigManager
            
            # 관리자 생성
            manager = manager_class(
                config_file=config_file,
                validator=validator,
                **kwargs
            )
            
            logger.info("설정 관리자 생성: %s (%s)", config_file, manager_class.__name__)
            return manager
            
        except Exception as e:
            logger.error("설정 관리자 생성 실패: %s", e)
            raise
    
    def get_supported_types(self) -> List[ConfigType]:
        """지원되는 설정 타입 목록"""
        from .serializers import SerializerFactory
        return SerializerFactory.get_supported_types()
    
    def get_registered_managers(self) -> List[str]:
        """등록된 관리자 타입 목록"""
        return list(self._manager_classes.keys())


# 전역 인스턴스들
_global_registry: Optional[ConfigRegistry] = None
_global_factory: Optional[ConfigFactory] = None

import threading
_registry_lock = threading.Lock()


def get_config_registry() -> ConfigRegistry:
    """전역 설정 레지스트리 반환"""
    global _global_registry # pylint: disable=global-statement
    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = ConfigRegistry()
    return _global_registry


def get_config_factory() -> ConfigFactory:
    """전역 설정 팩토리 반환"""
    global _global_factory # pylint: disable=global-statement
    if _global_factory is None:
        with _registry_lock:
            if _global_factory is None:
                _global_factory = ConfigFactory()
    return _global_factory


# 편의 함수들
def register_config_manager(name: str, manager: IConfigManager) -> None:
    """설정 관리자 등록 (편의 함수)"""
    registry = get_config_registry()
    registry.register_manager(name, manager)


def get_config_manager(name: str) -> Optional[IConfigManager]:
    """설정 관리자 반환 (편의 함수)"""
    registry = get_config_registry()
    return registry.get_manager(name)


def create_config_manager(
    config_file: str,
    config_type: Optional[ConfigType] = None,
    **kwargs
) -> IConfigManager:
    """설정 관리자 생성 (편의 함수)
    
    Args:
        config_file: 설정 파일 경로
        config_type: 설정 파일 타입 (None이면 자동 감지)
        **kwargs: 추가 생성 옵션
    """
    factory = get_config_factory()
    
    if config_type is None:
        from .utils import detect_config_type
        config_type = detect_config_type(config_file)
    
    return factory.create_manager(config_file, config_type, **kwargs)


def reload_all_configs() -> None:
    """모든 설정 리로드 (편의 함수)"""
    registry = get_config_registry()
    registry.reload_all()


def cleanup_all_configs() -> None:
    """모든 설정 리소스 정리 (편의 함수)"""
    registry = get_config_registry()
    registry.cleanup_all()


def initialize_config_system() -> None:
    """설정 시스템 초기화 (편의 함수)"""
    # 전역 레지스트리와 팩토리 초기화
    get_config_registry()
    get_config_factory()
    logger.info("설정 시스템 초기화 완료")


def quick_setup(config_files: Dict[str, str]) -> Dict[str, IConfigManager]:
    """빠른 설정 (편의 함수)
    
    Args:
        config_files: 관리자 이름과 설정 파일 경로 매핑
        
    Returns:
        생성된 관리자들의 딕셔너리
    """
    managers = {}
    registry = get_config_registry()
    
    for name, config_file in config_files.items():
        try:
            manager = create_config_manager(config_file)
            registry.register_manager(name, manager)
            managers[name] = manager
            logger.info("빠른 설정 완료: %s -> %s", name, config_file)
        except Exception as e:
            logger.error("빠른 설정 실패 [%s]: %s", name, e)
    
    return managers


def create_minimal_manager(
    config_file: str,
    default_config: Optional[ConfigDict] = None
) -> IConfigManager:
    """최소 설정 관리자 생성 (편의 함수)
    
    Args:
        config_file: 설정 파일 경로
        default_config: 기본 설정 데이터
        
    Returns:
        설정 관리자 인스턴스
    """
    from .generic_config_manager import GenericConfigManager
    
    manager = GenericConfigManager(config_file)
    
    if default_config:
        manager.set_config_data(default_config)
        if not os.path.exists(config_file):
            manager.save_config()
    
    return manager 