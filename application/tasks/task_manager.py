import asyncio
import logging
from typing import Callable, Dict, List, Optional

from application.tasks.interfaces import ITaskConfiguration, ITaskScheduler
from application.tasks.models.task_config import TaskConfig
from application.tasks.services import HttpClient, TaskConfiguration, TaskExecutor, TaskScheduler
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("task") or logging.getLogger("task")


class TaskManager:
    """작업 스케줄링 관리자 (리팩토링됨 - 의존성 주입 적용)"""

    def __init__(
        self,
        config_file: str = "task.json",
        task_configuration: Optional[ITaskConfiguration] = None,
        task_scheduler: Optional[ITaskScheduler] = None,
        http_client_timeout: int = 30,
        max_workers: int = 5,
    ) -> None:
        # 의존성 주입을 통한 구성 요소 설정
        self.task_configuration = task_configuration or TaskConfiguration(config_file)

        # HTTP 클라이언트 및 작업 실행자 생성
        self.http_client = HttpClient(timeout=http_client_timeout)
        self.task_executor = TaskExecutor(self.http_client)

        # 설정 로드
        settings = self.task_configuration.load_settings()

        # 스케줄러 생성
        self.task_scheduler = task_scheduler or TaskScheduler(
            task_executor=self.task_executor, settings=settings, max_workers=max_workers
        )

        # 작업 실행 콜백
        self.on_task_executed: Optional[Callable[[str, object], None]] = None
        self.on_task_error: Optional[Callable[[str, object], None]] = None

        # 콜백 설정
        self.task_scheduler.set_job_listener(
            on_executed=self._on_task_executed, on_error=self._on_task_error
        )

    def _on_task_executed(self, task_id: str, event: object) -> None:
        """작업 실행 완료 이벤트"""
        logger.info(f"작업 실행 완료: {task_id}")

        # 작업 실행 횟수 및 마지막 실행 시간 업데이트
        task = self.task_configuration.get_task(task_id)
        if task:
            task.update_last_run()
            self.task_configuration.save_settings(self.task_configuration.settings)

        if self.on_task_executed is not None:
            self.on_task_executed(task_id, event)

    def _on_task_error(self, task_id: str, event: object) -> None:
        """작업 실행 오류 이벤트"""
        logger.error(f"작업 실행 오류: {task_id} - {event}")

        if self.on_task_error is not None:
            self.on_task_error(task_id, event)

    def start(self) -> None:
        """스케줄러 시작"""
        if not self.is_running and self.task_configuration.settings.enabled:
            try:
                self.task_scheduler.start()
                logger.info("작업 스케줄러 시작됨")

                # 기존 작업들 등록
                self._register_all_tasks()

            except Exception as e:
                logger.error(f"작업 스케줄러 시작 실패: {e}")

    def stop(self) -> None:
        """스케줄러 중지"""
        if self.is_running:
            try:
                self.task_scheduler.stop()
                # HTTP 클라이언트 종료
                asyncio.run(self.http_client.close())
                logger.info("작업 스케줄러 중지됨")
            except Exception as e:
                logger.error(f"작업 스케줄러 중지 실패: {e}")

    def _register_all_tasks(self) -> None:
        """모든 활성화된 작업을 스케줄러에 등록"""
        enabled_tasks = self.task_configuration.get_enabled_tasks()
        for task_id, task in enabled_tasks.items():
            try:
                self.task_scheduler.add_job(task)
                logger.debug(f"작업 등록 완료: {task_id} - {task.name}")
            except Exception as e:
                logger.error(f"작업 등록 실패: {task_id} - {e}")

    @property
    def is_running(self) -> bool:
        """스케줄러 실행 상태"""
        return self.task_scheduler.is_running

    def add_task(self, task: TaskConfig) -> bool:
        """작업 추가"""
        try:
            success = self.task_configuration.add_task(task)
            if success and self.is_running and task.enabled:
                self.task_scheduler.add_job(task)
            logger.info(f"작업 추가 완료: {task.name}")
            return success
        except Exception as e:
            logger.error(f"작업 추가 실패: {e}")
            return False

    def update_task(self, task: TaskConfig) -> bool:
        """작업 수정"""
        try:
            # 설정 업데이트
            success = self.task_configuration.add_task(task)  # 동일 ID로 덮어쓰기

            if success and self.is_running:
                # 스케줄러에서 업데이트
                self.task_scheduler.update_job(task)

            logger.info(f"작업 수정 완료: {task.name}")
            return success
        except Exception as e:
            logger.error(f"작업 수정 실패: {e}")
            return False

    def remove_task(self, task_id: str) -> bool:
        """작업 제거"""
        try:
            # 스케줄러에서 제거
            if self.is_running:
                self.task_scheduler.remove_job(task_id)

            # 설정에서 제거
            success = self.task_configuration.remove_task(task_id)
            logger.info(f"작업 제거 완료: {task_id}")
            return success
        except Exception as e:
            logger.error(f"작업 제거 실패: {e}")
            return False

    def get_tasks(self) -> Dict[str, TaskConfig]:
        """모든 작업 조회"""
        return self.task_configuration.get_all_tasks()

    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        """특정 작업 조회"""
        return self.task_configuration.get_task(task_id)

    def get_running_jobs(self) -> List[Dict]:
        """실행 중인 작업 조회"""
        return self.task_scheduler.get_running_jobs()

    def toggle_task(self, task_id: str) -> bool:
        """작업 활성화/비활성화 토글"""
        task = self.get_task(task_id)
        if not task:
            return False

        task.enabled = not task.enabled
        return self.update_task(task)

    def set_enabled(self, enabled: bool) -> None:
        """스케줄러 전체 활성화/비활성화"""
        settings = self.task_configuration.settings
        settings.enabled = enabled
        self.task_configuration.save_settings(settings)

        if enabled and not self.is_running:
            self.start()
        elif not enabled and self.is_running:
            self.stop()
