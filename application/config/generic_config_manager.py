"""
범용 설정 관리자

어떤 형태의 설정 파일도 처리할 수 있는 일반적인 설정 관리자입니다.
"""

import logging
from typing import Optional

from .base_config_manager import BaseConfigManager
from .interfaces import ConfigDict

logger = logging.getLogger(__name__)


class GenericConfigManager(BaseConfigManager):
    """범용 설정 관리자
    
    특별한 비즈니스 로직 없이 일반적인 설정 파일을 관리합니다.
    기본 설정은 빈 딕셔너리로 시작합니다.
    """
    
    def __init__(
        self,
        config_file: str,
        default_config: Optional[ConfigDict] = None,
        **kwargs
    ):
        """GenericConfigManager 생성자
        
        Args:
            config_file: 설정 파일 경로
            default_config: 기본 설정 데이터
            **kwargs: BaseConfigManager 옵션들
        """
        self._default_config = default_config or {}
        super().__init__(config_file, **kwargs)
    
    def create_default_config(self) -> None:
        """기본 설정 생성"""
        try:
            self._config_data = self.get_default_config_data()
            self.save_config()
            logger.info("기본 설정 생성 완료: %s", self.config_file)
        except Exception as e:
            logger.error("기본 설정 생성 실패: %s", e)
            raise
    
    def get_default_config_data(self) -> ConfigDict:
        """기본 설정 데이터 반환"""
        return self._default_config.copy()
    
    def set_default_config(self, default_config: ConfigDict) -> None:
        """기본 설정 데이터 설정
        
        Args:
            default_config: 새로운 기본 설정 데이터
        """
        self._default_config = default_config.copy()
        logger.debug("기본 설정 데이터 업데이트됨") 