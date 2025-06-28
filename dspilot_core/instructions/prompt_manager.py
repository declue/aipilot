"""
프롬프트 관리자 모듈

프롬프트 템플릿들을 파일에서 로드하고 관리하는 클래스를 제공합니다.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PromptManager:
    """프롬프트 템플릿 관리 클래스

    - Single Responsibility: 프롬프트 로드 및 관리만 담당
    - Open/Closed: 새로운 프롬프트 타입 추가 시 기존 코드 수정 없이 확장 가능
    - Dependency Inversion: 추상화된 인터페이스에 의존
    """

    def __init__(self, instructions_dir: Optional[Path] = None):
        """프롬프트 관리자 초기화

        Args:
            instructions_dir: 프롬프트 파일이 있는 디렉토리 경로
        """
        if instructions_dir is None:
            instructions_dir = Path(__file__).parent

        self.instructions_dir = Path(instructions_dir)
        self._prompt_cache: Dict[str, str] = {}
        self._ensure_instructions_dir()

    def _ensure_instructions_dir(self) -> None:
        """프롬프트 디렉토리 존재 확인 및 생성"""
        if not self.instructions_dir.exists():
            self.instructions_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"프롬프트 디렉토리 생성: {self.instructions_dir}")

    def get_prompt(self, prompt_name: str, use_cache: bool = True) -> Optional[str]:
        """프롬프트 템플릿 로드

        Args:
            prompt_name: 프롬프트 파일명 (확장자 제외)
            use_cache: 캐시 사용 여부

        Returns:
            프롬프트 템플릿 문자열 또는 None
        """
        if use_cache and prompt_name in self._prompt_cache:
            return self._prompt_cache[prompt_name]

        prompt_file = self.instructions_dir / f"{prompt_name}.txt"

        try:
            if prompt_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_content = f.read().strip()

                if use_cache:
                    self._prompt_cache[prompt_name] = prompt_content

                logger.debug(f"프롬프트 로드 성공: {prompt_name}")
                return prompt_content
            else:
                logger.warning(f"프롬프트 파일 없음: {prompt_file}")
                return None

        except Exception as e:
            logger.error(f"프롬프트 로드 실패 {prompt_name}: {e}")
            return None

    def get_formatted_prompt(self, prompt_name: str, **kwargs) -> Optional[str]:
        """포맷팅된 프롬프트 반환

        Args:
            prompt_name: 프롬프트 파일명
            **kwargs: 템플릿 변수들

        Returns:
            포맷팅된 프롬프트 문자열 또는 None
        """
        template = self.get_prompt(prompt_name)
        if template is None:
            return None

        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"프롬프트 포맷팅 실패 - 누락된 변수 {prompt_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"프롬프트 포맷팅 오류 {prompt_name}: {e}")
            return None

    def list_available_prompts(self) -> list[str]:
        """사용 가능한 프롬프트 목록 반환

        Returns:
            프롬프트 파일명 목록 (확장자 제외)
        """
        prompt_files = []
        try:
            for file_path in self.instructions_dir.glob("*.txt"):
                prompt_files.append(file_path.stem)
        except Exception as e:
            logger.error(f"프롬프트 목록 조회 실패: {e}")

        return sorted(prompt_files)

    def reload_cache(self) -> None:
        """프롬프트 캐시 재로드"""
        logger.info("프롬프트 캐시 재로드 시작")
        cached_prompts = list(self._prompt_cache.keys())
        self._prompt_cache.clear()

        for prompt_name in cached_prompts:
            self.get_prompt(prompt_name, use_cache=True)

        logger.info(f"프롬프트 캐시 재로드 완료: {len(cached_prompts)}개")

    def add_custom_prompt(self, prompt_name: str, prompt_content: str) -> bool:
        """커스텀 프롬프트 추가

        Args:
            prompt_name: 프롬프트 이름
            prompt_content: 프롬프트 내용

        Returns:
            성공 여부
        """
        try:
            prompt_file = self.instructions_dir / f"{prompt_name}.txt"

            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt_content)

            # 캐시에도 추가
            self._prompt_cache[prompt_name] = prompt_content

            logger.info(f"커스텀 프롬프트 추가 성공: {prompt_name}")
            return True

        except Exception as e:
            logger.error(f"커스텀 프롬프트 추가 실패 {prompt_name}: {e}")
            return False

    def get_cache_status(self) -> Dict[str, int]:
        """캐시 상태 정보 반환

        Returns:
            캐시 상태 딕셔너리
        """
        return {
            "cached_prompts": len(self._prompt_cache),
            "available_files": len(self.list_available_prompts())
        }


# 싱글톤 인스턴스 (선택적 사용)
_default_prompt_manager: Optional[PromptManager] = None


def get_default_prompt_manager() -> PromptManager:
    """기본 프롬프트 관리자 인스턴스 반환

    Returns:
        기본 프롬프트 관리자 인스턴스
    """
    global _default_prompt_manager
    if _default_prompt_manager is None:
        _default_prompt_manager = PromptManager()
    return _default_prompt_manager


def get_prompt(prompt_name: str, **kwargs) -> Optional[str]:
    """편의 함수: 기본 관리자를 사용한 프롬프트 로드

    Args:
        prompt_name: 프롬프트 이름
        **kwargs: 템플릿 변수들

    Returns:
        포맷팅된 프롬프트 문자열 또는 None
    """
    manager = get_default_prompt_manager()
    return manager.get_formatted_prompt(prompt_name, **kwargs)
