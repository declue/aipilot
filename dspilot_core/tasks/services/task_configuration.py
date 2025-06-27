"""작업 설정 관리 서비스 구현"""

import logging
import os
from typing import Dict, Optional

from dspilot_core.tasks.exceptions import TaskConfigurationError
from dspilot_core.tasks.interfaces.task_configuration import ITaskConfiguration
from dspilot_core.tasks.models.task_config import TaskConfig, TaskConfigFileManager, TaskSettings
from dspilot_core.util.logger import setup_logger

logger: logging.Logger = setup_logger("task") or logging.getLogger("task")


class TaskConfiguration(ITaskConfiguration):
    """작업 설정 관리 서비스 구현"""

    def __init__(self, config_file: str = "task.json") -> None:
        self.config_file = config_file
        self._settings: Optional[TaskSettings] = None

    def load_settings(self) -> TaskSettings:
        """설정을 로드합니다."""
        try:
            if os.path.exists(self.config_file):
                self._settings = TaskConfigFileManager.load_from_file(self.config_file)
                logger.debug(f"작업 설정 로드 완료: {len(self._settings.tasks or {})}개 작업")
            else:
                logger.debug("작업 설정 파일이 없어 기본 설정으로 초기화")
                self._settings = TaskSettings()
                self.save_settings(self._settings)
            return self._settings
        except Exception as e:
            logger.error(f"작업 설정 로드 실패: {e}")
            raise TaskConfigurationError(f"설정 로드 실패: {e}")

    def save_settings(self, settings: TaskSettings) -> bool:
        """설정을 저장합니다."""
        try:
            TaskConfigFileManager.save_to_file(settings, self.config_file)
            self._settings = settings
            logger.debug("작업 설정 저장 완료")
            return True
        except Exception as e:
            logger.error(f"작업 설정 저장 실패: {e}")
            raise TaskConfigurationError(f"설정 저장 실패: {e}")

    def add_task(self, task: TaskConfig) -> bool:
        """작업을 추가합니다."""
        try:
            if self._settings is None:
                self.load_settings()

            assert self._settings is not None
            self._settings.add_task(task)
            self.save_settings(self._settings)
            logger.info(f"작업 추가 완료: {task.name}")
            return True
        except Exception as e:
            logger.error(f"작업 추가 실패: {e}")
            raise TaskConfigurationError(f"작업 추가 실패: {e}")

    def remove_task(self, task_id: str) -> bool:
        """작업을 제거합니다."""
        try:
            if self._settings is None:
                self.load_settings()

            assert self._settings is not None
            if task_id not in (self._settings.tasks or {}):
                return False

            self._settings.remove_task(task_id)
            self.save_settings(self._settings)
            logger.info(f"작업 제거 완료: {task_id}")
            return True
        except Exception as e:
            logger.error(f"작업 제거 실패: {e}")
            raise TaskConfigurationError(f"작업 제거 실패: {e}")

    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        """특정 작업을 조회합니다."""
        if self._settings is None:
            self.load_settings()

        assert self._settings is not None
        return self._settings.get_task(task_id)

    def get_all_tasks(self) -> Dict[str, TaskConfig]:
        """모든 작업을 조회합니다."""
        if self._settings is None:
            self.load_settings()

        assert self._settings is not None
        return (self._settings.tasks or {}).copy()

    def get_enabled_tasks(self) -> Dict[str, TaskConfig]:
        """활성화된 작업만 조회합니다."""
        if self._settings is None:
            self.load_settings()

        assert self._settings is not None
        return self._settings.get_enabled_tasks()

    @property
    def settings(self) -> TaskSettings:
        """현재 설정을 반환합니다."""
        if self._settings is None:
            self.load_settings()

        assert self._settings is not None
        return self._settings
