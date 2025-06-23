"""작업 스케줄러 인터페이스"""

from abc import ABC, abstractmethod
from typing import Callable, List, Optional

from application.tasks.models.task_config import TaskConfig


class ITaskScheduler(ABC):
    """작업 스케줄러 인터페이스"""

    @abstractmethod
    def start(self) -> None:
        """스케줄러를 시작합니다."""

    @abstractmethod
    def stop(self) -> None:
        """스케줄러를 중지합니다."""

    @abstractmethod
    def add_job(self, task: TaskConfig) -> bool:
        """작업을 스케줄러에 추가합니다.

        Args:
            task: 추가할 작업

        Returns:
            성공 여부
        """

    @abstractmethod
    def remove_job(self, task_id: str) -> bool:
        """작업을 스케줄러에서 제거합니다.

        Args:
            task_id: 제거할 작업 ID

        Returns:
            성공 여부
        """

    @abstractmethod
    def update_job(self, task: TaskConfig) -> bool:
        """작업을 업데이트합니다.

        Args:
            task: 업데이트할 작업

        Returns:
            성공 여부
        """

    @abstractmethod
    def get_running_jobs(self) -> List[dict]:
        """실행 중인 작업 목록을 반환합니다.

        Returns:
            실행 중인 작업 목록
        """

    @abstractmethod
    def set_job_listener(
        self,
        on_executed: Optional[Callable[[str, object], None]] = None,
        on_error: Optional[Callable[[str, object], None]] = None,
    ) -> None:
        """작업 실행 결과 리스너를 설정합니다.

        Args:
            on_executed: 작업 실행 완료 콜백
            on_error: 작업 실행 오류 콜백
        """

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """스케줄러 실행 상태를 반환합니다."""
