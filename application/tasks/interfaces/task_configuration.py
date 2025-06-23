"""작업 설정 관리 인터페이스"""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from application.tasks.models.task_config import TaskConfig, TaskSettings


class ITaskConfiguration(ABC):
    """작업 설정 관리 인터페이스"""

    @abstractmethod
    def load_settings(self) -> TaskSettings:
        """설정을 로드합니다.

        Returns:
            로드된 작업 설정
        """

    @abstractmethod
    def save_settings(self, settings: TaskSettings) -> bool:
        """설정을 저장합니다.

        Args:
            settings: 저장할 작업 설정

        Returns:
            성공 여부
        """

    @abstractmethod
    def add_task(self, task: TaskConfig) -> bool:
        """작업을 추가합니다.

        Args:
            task: 추가할 작업

        Returns:
            성공 여부
        """

    @abstractmethod
    def remove_task(self, task_id: str) -> bool:
        """작업을 제거합니다.

        Args:
            task_id: 제거할 작업 ID

        Returns:
            성공 여부
        """

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        """특정 작업을 조회합니다.

        Args:
            task_id: 조회할 작업 ID

        Returns:
            작업 설정 또는 None
        """

    @abstractmethod
    def get_all_tasks(self) -> Dict[str, TaskConfig]:
        """모든 작업을 조회합니다.

        Returns:
            모든 작업 목록
        """

    @abstractmethod
    def get_enabled_tasks(self) -> Dict[str, TaskConfig]:
        """활성화된 작업만 조회합니다.

        Returns:
            활성화된 작업 목록
        """

    @property
    @abstractmethod
    def settings(self) -> TaskSettings:
        """현재 설정을 반환합니다."""
