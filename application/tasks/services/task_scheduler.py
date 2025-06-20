"""작업 스케줄러 서비스 구현"""

import asyncio
import logging
from typing import Callable, List, Optional

from apscheduler.events import (  # type: ignore
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    JobExecutionEvent,
)
from apscheduler.executors.pool import ThreadPoolExecutor  # type: ignore
from apscheduler.jobstores.memory import MemoryJobStore  # type: ignore
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore

from application.tasks.exceptions import TaskSchedulerError
from application.tasks.interfaces.task_executor import ITaskExecutor
from application.tasks.interfaces.task_scheduler import ITaskScheduler
from application.tasks.models.task_config import TaskConfig, TaskSettings
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("task_scheduler") or logging.getLogger("task_scheduler")


class TaskScheduler(ITaskScheduler):
    """작업 스케줄러 서비스 구현"""

    def __init__(
        self, 
        task_executor: ITaskExecutor,
        settings: TaskSettings,
        max_workers: int = 5
    ) -> None:
        self.task_executor = task_executor
        self.settings = settings
        self._scheduler: Optional[BackgroundScheduler] = None
        self._is_running = False
        
        # 이벤트 콜백
        self._on_executed: Optional[Callable[[str, object], None]] = None
        self._on_error: Optional[Callable[[str, object], None]] = None
        
        # 스케줄러 초기화
        self._init_scheduler(max_workers)

    def _init_scheduler(self, max_workers: int) -> None:
        """스케줄러를 초기화합니다."""
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": ThreadPoolExecutor(max_workers=max_workers)}
        job_defaults = {"coalesce": False, "max_instances": 1}

        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=self.settings.timezone,
        )

        # 이벤트 리스너 등록
        self._scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)

    def start(self) -> None:
        """스케줄러를 시작합니다."""
        if self._is_running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return

        try:
            assert self._scheduler is not None
            self._scheduler.start()
            self._is_running = True
            logger.info("작업 스케줄러가 시작되었습니다")
        except Exception as e:
            logger.error(f"스케줄러 시작 실패: {e}")
            raise TaskSchedulerError(f"스케줄러 시작 실패: {e}")

    def stop(self) -> None:
        """스케줄러를 중지합니다."""
        if not self._is_running or not self._scheduler:
            return

        try:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("작업 스케줄러가 중지되었습니다")
        except Exception as e:
            logger.error(f"스케줄러 중지 실패: {e}")
            raise TaskSchedulerError(f"스케줄러 중지 실패: {e}")

    def add_job(self, task: TaskConfig) -> bool:
        """작업을 스케줄러에 추가합니다."""
        if not self._scheduler:
            logger.error("스케줄러가 초기화되지 않았습니다")
            return False

        try:
            trigger = CronTrigger.from_crontab(task.cron_expression, timezone=self.settings.timezone)
            
            self._scheduler.add_job(
                func=self._execute_task_wrapper,
                trigger=trigger,
                id=task.id,
                name=task.name,
                args=[task],
                replace_existing=True,
            )
            
            logger.debug(f"작업이 스케줄러에 추가되었습니다: {task.name}")
            return True
        except Exception as e:
            logger.error(f"작업 추가 실패: {task.name} - {e}")
            return False

    def remove_job(self, task_id: str) -> bool:
        """작업을 스케줄러에서 제거합니다."""
        if not self._scheduler:
            return False

        try:
            if self._scheduler.get_job(task_id):
                self._scheduler.remove_job(task_id)
                logger.debug(f"작업이 스케줄러에서 제거되었습니다: {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"작업 제거 실패: {task_id} - {e}")
            return False

    def update_job(self, task: TaskConfig) -> bool:
        """작업을 업데이트합니다."""
        # 기존 작업 제거 후 다시 추가
        self.remove_job(task.id)
        if task.enabled:
            return self.add_job(task)
        return True

    def get_running_jobs(self) -> List[dict]:
        """실행 중인 작업 목록을 반환합니다."""
        if not self._scheduler:
            return []

        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs

    def set_job_listener(
        self, 
        on_executed: Optional[Callable[[str, object], None]] = None,
        on_error: Optional[Callable[[str, object], None]] = None
    ) -> None:
        """작업 실행 결과 리스너를 설정합니다."""
        self._on_executed = on_executed
        self._on_error = on_error

    @property
    def is_running(self) -> bool:
        """스케줄러 실행 상태를 반환합니다."""
        return self._is_running

    def _execute_task_wrapper(self, task: TaskConfig) -> None:
        """작업 실행 래퍼 함수 (동기 함수에서 비동기 함수 호출)"""
        try:
            asyncio.run(self.task_executor.execute_task(task))
        except Exception as e:
            logger.error(f"작업 실행 래퍼에서 오류 발생: {task.name} - {e}")
            raise

    def _job_executed(self, event: JobExecutionEvent) -> None:
        """작업 실행 완료 이벤트 핸들러"""
        job_id = event.job_id
        logger.info(f"작업 실행 완료: {job_id}")
        
        if self._on_executed:
            self._on_executed(job_id, event)

    def _job_error(self, event: JobExecutionEvent) -> None:
        """작업 실행 오류 이벤트 핸들러"""
        job_id = event.job_id
        exception = event.exception
        logger.error(f"작업 실행 오류: {job_id} - {exception}")
        
        if self._on_error:
            self._on_error(job_id, event) 