import json
import logging
import os
from typing import Any, Dict

from application.config.apps.defaults.default_llm_profiles import (
    DEFAULT_LLM_PROFILE,
    DEFAULT_LLM_PROFILES,
    DEFAULT_LLM_PROFILES_JSON,
    PROTECTED_PROFILES,
    REQUIRED_LLM_PROFILE_FIELDS,
)
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("config") or logging.getLogger("config")


class LLMProfileManager:
    """LLM 프로필 관리 클래스

    llm_profiles.json 파일을 통해 LLM 프로필들을 관리합니다.
    단일 책임 원칙에 따라 LLM 프로필 관리만을 담당합니다.
    """

    def __init__(self, profiles_file: str = None) -> None:
        """LLMProfileManager 생성자

        Args:
            profiles_file: LLM 프로필 파일 경로. None인 경우 기본값 사용
        """
        self.llm_profiles_file = profiles_file or DEFAULT_LLM_PROFILES_JSON
        self._llm_profiles: Dict[str, Dict[str, Any]] = {}
        self._current_profile_name = DEFAULT_LLM_PROFILE
        self.load_llm_profiles()

    def load_llm_profiles(self) -> None:
        """LLM 프로필 파일 로드"""
        try:
            if os.path.exists(self.llm_profiles_file):
                with open(self.llm_profiles_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._llm_profiles = data.get("profiles", {})
                    self._current_profile_name = data.get("current_profile", DEFAULT_LLM_PROFILE)
                    logger.debug(f"LLM 프로필 로드 완료: {len(self._llm_profiles)}개 프로필")
            else:
                # 기본 프로필 생성
                self.create_default_llm_profiles()
        except Exception as exception:
            logger.error(f"LLM 프로필 로드 실패: {exception}")
            self.create_default_llm_profiles()

    def create_default_llm_profiles(self) -> None:
        """기본 LLM 프로필 생성"""
        try:
            # 기본 프로필들을 복사하여 사용 (참조 문제 방지)
            self._llm_profiles = {
                profile_name: profile_config.copy()
                for profile_name, profile_config in DEFAULT_LLM_PROFILES.items()
            }
            self._current_profile_name = DEFAULT_LLM_PROFILE
            self.save_llm_profiles()
            logger.debug("기본 LLM 프로필 생성 완료")
        except Exception as exception:
            logger.error(f"기본 LLM 프로필 생성 실패: {exception}")
            raise

    def save_llm_profiles(self) -> None:
        """LLM 프로필 파일 저장"""
        try:
            data = {
                "profiles": self._llm_profiles,
                "current_profile": self._current_profile_name,
            }
            with open(self.llm_profiles_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("LLM 프로필 저장 완료")
        except Exception as exception:
            logger.error(f"LLM 프로필 저장 실패: {exception}")
            raise

    def get_llm_profiles(self) -> Dict[str, Dict[str, Any]]:
        """모든 LLM 프로필 반환"""
        return self._llm_profiles.copy()

    def get_current_profile_name(self) -> str:
        """현재 선택된 프로필 이름 반환"""
        return self._current_profile_name

    def set_current_profile(self, profile_name: str) -> None:
        """현재 프로필 설정

        Args:
            profile_name: 설정할 프로필 이름

        Raises:
            ValueError: 프로필이 존재하지 않는 경우
        """
        if profile_name in self._llm_profiles:
            self._current_profile_name = profile_name
            self.save_llm_profiles()
            logger.info(f"현재 프로필을 '{profile_name}'으로 변경")
        else:
            raise ValueError(f"프로필 '{profile_name}'을 찾을 수 없습니다")

    def get_current_profile(self) -> Dict[str, Any]:
        """현재 선택된 프로필 정보 반환

        Returns:
            현재 프로필 정보. 프로필이 없으면 빈 딕셔너리 반환
        """
        return self._llm_profiles.get(self._current_profile_name, {})

    def create_llm_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """새 LLM 프로필 생성

        Args:
            profile_name: 프로필 이름
            config: 프로필 설정

        Raises:
            ValueError: 프로필이 이미 존재하거나 필수 필드가 없는 경우
        """
        if profile_name in self._llm_profiles:
            raise ValueError(f"프로필 '{profile_name}'이 이미 존재합니다")

        # 필수 필드 검증
        for field in REQUIRED_LLM_PROFILE_FIELDS:
            if field not in config:
                raise ValueError(f"필수 필드 '{field}'가 없습니다")

        self._llm_profiles[profile_name] = config
        self.save_llm_profiles()
        logger.info(f"새 LLM 프로필 '{profile_name}' 생성 완료")

    def update_llm_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """LLM 프로필 업데이트

        Args:
            profile_name: 프로필 이름
            config: 업데이트할 설정

        Raises:
            ValueError: 프로필이 존재하지 않는 경우
        """
        if profile_name not in self._llm_profiles:
            raise ValueError(f"프로필 '{profile_name}'을 찾을 수 없습니다")

        self._llm_profiles[profile_name].update(config)
        self.save_llm_profiles()
        logger.info(f"LLM 프로필 '{profile_name}' 업데이트 완료")

    def delete_llm_profile(self, profile_name: str) -> None:
        """LLM 프로필 삭제

        Args:
            profile_name: 삭제할 프로필 이름

        Raises:
            ValueError: 프로필이 존재하지 않거나 보호된 프로필을 삭제하려는 경우
        """
        if profile_name not in self._llm_profiles:
            raise ValueError(f"프로필 '{profile_name}'을 찾을 수 없습니다")

        if profile_name in PROTECTED_PROFILES:
            raise ValueError(f"'{profile_name}' 프로필은 삭제할 수 없습니다")

        if self._current_profile_name == profile_name:
            self.set_current_profile(DEFAULT_LLM_PROFILE)

        del self._llm_profiles[profile_name]
        self.save_llm_profiles()
        logger.info(f"LLM 프로필 '{profile_name}' 삭제 완료")

    def profile_exists(self, profile_name: str) -> bool:
        """프로필 존재 여부 확인

        Args:
            profile_name: 확인할 프로필 이름

        Returns:
            프로필 존재 여부
        """
        return profile_name in self._llm_profiles
