import logging
from typing import Dict, List, Optional

from PySide6.QtCore import QThread, Signal

from application.tasks.interfaces import ITaskConfiguration, ITaskScheduler
from application.tasks.models.task_config import TaskConfig
from application.tasks.task_manager import TaskManager
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("task") or logging.getLogger("task")


class TaskThread(QThread):
    """작업 스케줄러를 별도 스레드에서 실행하는 클래스 (리팩토링됨)"""

    # 시그널 정의
    task_executed = Signal(str, object)  # task_id, event
    task_error = Signal(str, object)  # task_id, event
    scheduler_started = Signal()
    scheduler_stopped = Signal()

    def __init__(
        self, 
        config_file: str = "task.json",
        task_configuration: Optional[ITaskConfiguration] = None,
        task_scheduler: Optional[ITaskScheduler] = None,
        http_client_timeout: int = 30,
        max_workers: int = 5
    ) -> None:
        super().__init__()
        self.config_file = config_file
        self.task_manager: Optional[TaskManager] = None
        self.is_running = False
        
        # 의존성 주입을 위한 매개변수 저장
        self._task_configuration = task_configuration
        self._task_scheduler = task_scheduler
        self._http_client_timeout = http_client_timeout
        self._max_workers = max_workers

    def run(self) -> None:
        """스레드에서 작업 스케줄러 실행"""
        try:
            logger.info("작업 스케줄러 스레드 시작")

            # TaskManager 생성 (의존성 주입 적용)
            self.task_manager = TaskManager(
                config_file=self.config_file,
                task_configuration=self._task_configuration,
                task_scheduler=self._task_scheduler,
                http_client_timeout=self._http_client_timeout,
                max_workers=self._max_workers
            )

            # 콜백 함수 설정
            self.task_manager.on_task_executed = self._on_task_executed
            self.task_manager.on_task_error = self._on_task_error

            # 스케줄러 시작
            self.task_manager.start()
            self.is_running = True
            self.scheduler_started.emit()

            # 스레드가 종료될 때까지 대기
            self.exec()

        except Exception as e:
            logger.error(f"작업 스케줄러 스레드 실행 오류: {e}")
        finally:
            self._cleanup()

    def _on_task_executed(self, task_id: str, event: object) -> None:
        """작업 실행 완료 콜백"""
        logger.debug(f"스레드에서 작업 실행 완료 시그널 발생: {task_id}")
        self.task_executed.emit(task_id, event)

    def _on_task_error(self, task_id: str, event: object) -> None:
        """작업 실행 오류 콜백"""
        logger.debug(f"스레드에서 작업 오류 시그널 발생: {task_id}")
        self.task_error.emit(task_id, event)

    def stop_scheduler(self) -> None:
        """스케줄러 중지"""
        logger.info("작업 스케줄러 중지 요청")
        if self.task_manager and self.is_running:
            self.task_manager.stop()
            self.is_running = False
            self.scheduler_stopped.emit()

        # 스레드 종료
        self.quit()

    def _cleanup(self) -> None:
        """정리 작업"""
        if self.task_manager:
            self.task_manager.stop()
        logger.info("작업 스케줄러 스레드 종료")

    def get_task_manager(self) -> Optional[TaskManager]:
        """TaskManager 인스턴스 반환"""
        return self.task_manager

    def add_task(self, task_config: TaskConfig) -> bool:
        """작업 추가 (스레드 안전)"""
        if self.task_manager:
            return self.task_manager.add_task(task_config)
        return False

    def update_task(self, task_config: TaskConfig) -> bool:
        """작업 수정 (스레드 안전)"""
        if self.task_manager:
            return self.task_manager.update_task(task_config)
        return False

    def remove_task(self, task_id: str) -> bool:
        """작업 제거 (스레드 안전)"""
        if self.task_manager:
            return self.task_manager.remove_task(task_id)
        return False

    def get_tasks(self) -> Dict[str, TaskConfig]:
        """모든 작업 조회 (스레드 안전)"""
        if self.task_manager:
            return self.task_manager.get_tasks()
        return {}

    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        """특정 작업 조회 (스레드 안전)"""
        if self.task_manager:
            return self.task_manager.get_task(task_id)
        return None

    def toggle_task(self, task_id: str) -> bool:
        """작업 활성화/비활성화 토글 (스레드 안전)"""
        if self.task_manager:
            return self.task_manager.toggle_task(task_id)
        return False

    def set_scheduler_enabled(self, enabled: bool) -> None:
        """스케줄러 전체 활성화/비활성화 (스레드 안전)"""
        if self.task_manager:
            self.task_manager.set_enabled(enabled)

    def get_running_jobs(self) -> List[Dict]:
        """실행 중인 작업 조회 (스레드 안전)"""
        if self.task_manager:
            return self.task_manager.get_running_jobs()
        return []
