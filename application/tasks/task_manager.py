"""작업 스케줄링 관리자"""

import asyncio
import logging
import os
from typing import Any, Callable, Dict, List, Optional

import aiohttp
from apscheduler.events import (  # type: ignore
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    JobExecutionEvent,
)
from apscheduler.executors.pool import ThreadPoolExecutor  # type: ignore
from apscheduler.jobstores.memory import MemoryJobStore  # type: ignore
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore

from application.tasks.models.task_config import TaskConfig, TaskSettings
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("task_manager") or logging.getLogger(
    "task_manager"
)


class TaskManager:
    """작업 스케줄링 관리자"""

    def __init__(self, config_file: str = "task.json") -> None:
        self.config_file = config_file
        self.settings: TaskSettings = TaskSettings()
        self.scheduler: Optional[BackgroundScheduler] = None
        self.is_running = False

        # 작업 실행 콜백
        self.on_task_executed: Optional[Callable[[str, object], None]] = None
        self.on_task_error: Optional[Callable[[str, object], None]] = None

        # aiohttp 세션(재사용)
        self._session: Optional[aiohttp.ClientSession] = None

        # 설정 로드
        self.load_settings()

        # 스케줄러 초기화
        self._init_scheduler()

    def _init_scheduler(self) -> None:
        """스케줄러 초기화"""
        jobstores = {"default": MemoryJobStore()}

        executors = {
            "default": ThreadPoolExecutor(max_workers=self.settings.max_concurrent_jobs)
        }

        job_defaults = {"coalesce": False, "max_instances": 1}

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=self.settings.timezone,
        )

        # 이벤트 리스너 등록
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)

    def _job_executed(self, event: JobExecutionEvent) -> None:
        """작업 실행 완료 이벤트"""
        job_id = event.job_id
        logger.info(f"작업 실행 완료: {job_id}")

        # 작업 실행 횟수 및 마지막 실행 시간 업데이트
        if self.settings.tasks and job_id in self.settings.tasks:
            task = self.settings.tasks[job_id]
            task.update_last_run()
            self.save_settings()

        if self.on_task_executed is not None:
            self.on_task_executed(job_id, event)

    def _job_error(self, event: JobExecutionEvent) -> None:
        """작업 실행 오류 이벤트"""
        job_id = event.job_id
        exception = event.exception
        logger.error(f"작업 실행 오류: {job_id} - {exception}")

        if self.on_task_error is not None:
            self.on_task_error(job_id, event)

    def load_settings(self) -> None:
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_file):
                self.settings = TaskSettings.load_from_file(self.config_file)
                logger.info(
                    f"작업 설정 로드 완료: {len(self.settings.tasks or {})}개 작업"
                )
            else:
                logger.info("작업 설정 파일이 없어 기본 설정으로 초기화")
                self.save_settings()  # 기본 설정 저장
        except Exception as e:
            logger.error(f"작업 설정 로드 실패: {e}")
            self.settings = TaskSettings()  # 기본 설정으로 fallback

    def save_settings(self) -> None:
        """설정 파일 저장"""
        try:
            self.settings.save_to_file(self.config_file)
            logger.debug("작업 설정 저장 완료")
        except Exception as e:
            logger.error(f"작업 설정 저장 실패: {e}")

    def start(self) -> None:
        """스케줄러 시작"""
        if not self.is_running and self.settings.enabled:
            try:
                assert self.scheduler is not None
                self.scheduler.start()
                self.is_running = True
                logger.info("작업 스케줄러 시작됨")

                # 기존 작업들 등록
                self._register_all_tasks()

            except Exception as e:
                logger.error(f"작업 스케줄러 시작 실패: {e}")
                self.is_running = False

    def stop(self) -> None:
        """스케줄러 중지"""
        if self.is_running and self.scheduler:
            try:
                self.scheduler.shutdown(wait=False)
                self.is_running = False
                # 세션 종료
                try:
                    asyncio.run(self._close_session())
                finally:
                    logger.info("작업 스케줄러 중지됨")
            except Exception as e:
                logger.error(f"작업 스케줄러 중지 실패: {e}")

    def _register_all_tasks(self) -> None:
        """모든 활성화된 작업을 스케줄러에 등록"""
        for task_id, task in self.settings.get_enabled_tasks().items():
            try:
                self._add_job_to_scheduler(task)
                logger.debug(f"작업 등록 완료: {task_id} - {task.name}")
            except Exception as e:
                logger.error(f"작업 등록 실패: {task_id} - {e}")

    def _add_job_to_scheduler(self, task: TaskConfig) -> None:
        """개별 작업을 스케줄러에 추가"""
        if not self.scheduler:
            return
            
        trigger = CronTrigger.from_crontab(
            task.cron_expression, timezone=self.settings.timezone
        )

        self.scheduler.add_job(
            func=self._execute_task,
            trigger=trigger,
            id=task.id,
            name=task.name,
            args=[task],
            replace_existing=True,
        )

    def _execute_task(self, task: TaskConfig) -> None:
        """작업 실행"""
        logger.info(f"작업 실행 시작: {task.name} ({task.id})")

        try:
            if task.action_type == "llm_request":
                asyncio.run(self._execute_llm_request(task))
            elif task.action_type == "api_call":
                asyncio.run(self._execute_api_call(task))
            elif task.action_type == "notification":
                asyncio.run(self._execute_notification(task))
            else:
                logger.warning(f"알 수 없는 작업 타입: {task.action_type}")

        except Exception as e:
            logger.error(f"작업 실행 중 오류: {task.name} - {e}")
            raise

    async def _execute_llm_request(self, task: TaskConfig) -> None:
        """LLM 요청 실행"""
        params = task.action_params
        prompt = params.get("prompt", "")
        api_url = params.get("api_url", "http://127.0.0.1:8000/llm/request")

        if not prompt:
            logger.warning("LLM 요청에 prompt가 없습니다")
            return

        try:
            session = self._get_session()
            payload = {"prompt": prompt}  # API에서 기대하는 필드명은 'prompt'

            async with session.post(api_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"LLM 요청 완료: {task.name}")
                    logger.debug(f"LLM 응답: {result}")
                else:
                    error_text = await response.text()
                    logger.error(
                        f"LLM API 오류 (status {response.status}): {error_text}"
                    )
                    raise RuntimeError(
                        f"API 응답 오류: {response.status} - {error_text}"
                    )

        except Exception as e:
            logger.error(f"LLM 요청 실행 실패: {e}")
            raise

    async def _execute_api_call(self, task: TaskConfig) -> None:
        """API 호출 실행"""
        params = task.action_params
        url = params.get("url", "")
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        payload = params.get("payload", {})

        if not url:
            logger.warning("API 호출에 URL이 없습니다")
            return

        try:
            session = self._get_session()
            if method == "GET":
                async with session.get(url, headers=headers) as response:
                    result = await response.text()
            elif method == "POST":
                async with session.post(
                    url, json=payload, headers=headers
                ) as response:
                    result = await response.text()
            else:
                logger.warning(f"지원하지 않는 HTTP 메서드: {method}")
                return

            logger.info(f"API 호출 완료: {task.name} - {response.status}")
            logger.debug(f"API 응답: {result[:200]}...")

        except Exception as e:
            logger.error(f"API 호출 실행 실패: {e}")
            raise

    async def _execute_notification(self, task: TaskConfig) -> None:
        """알림 실행"""
        params = task.action_params
        message = params.get("message", "")
        notification_type = params.get("type", "info")
        api_url = params.get(
            "api_url", f"http://127.0.0.1:8000/notifications/{notification_type}"
        )

        if not message:
            logger.warning("알림에 메시지가 없습니다")
            return

        try:
            session = self._get_session()
            payload = {"title": params.get("title", task.name), "message": message}

            async with session.post(api_url, json=payload) as response:
                result = await response.json()
                logger.info(f"알림 전송 완료: {task.name}")
                logger.debug(f"알림 응답: {result}")

        except Exception as e:
            logger.error(f"알림 실행 실패: {e}")
            raise

    def add_task(self, task: TaskConfig) -> bool:
        """작업 추가"""
        try:
            self.settings.add_task(task)
            self.save_settings()

            # 스케줄러가 실행 중이면 즉시 등록
            if self.is_running and task.enabled:
                self._add_job_to_scheduler(task)

            logger.info(f"작업 추가 완료: {task.name}")
            return True

        except Exception as e:
            logger.error(f"작업 추가 실패: {e}")
            return False

    def update_task(self, task: TaskConfig) -> bool:
        """작업 수정"""
        try:
            self.settings.add_task(task)  # 동일 ID로 덮어쓰기
            self.save_settings()

            # 스케줄러에서 기존 작업 제거 후 재등록
            if self.is_running and self.scheduler:
                if self.scheduler.get_job(task.id):
                    self.scheduler.remove_job(task.id)

                if task.enabled:
                    self._add_job_to_scheduler(task)

            logger.info(f"작업 수정 완료: {task.name}")
            return True

        except Exception as e:
            logger.error(f"작업 수정 실패: {e}")
            return False

    def remove_task(self, task_id: str) -> bool:
        """작업 제거"""
        try:
            # 스케줄러에서 제거
            if self.is_running and self.scheduler and self.scheduler.get_job(task_id):
                self.scheduler.remove_job(task_id)

            # 설정에서 제거
            self.settings.remove_task(task_id)
            self.save_settings()

            logger.info(f"작업 제거 완료: {task_id}")
            return True

        except Exception as e:
            logger.error(f"작업 제거 실패: {e}")
            return False

    def get_tasks(self) -> Dict[str, TaskConfig]:
        """모든 작업 조회"""
        return (self.settings.tasks or {}).copy()

    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        """특정 작업 조회"""
        return self.settings.get_task(task_id)

    def get_running_jobs(self) -> List[Dict]:
        """실행 중인 작업 조회"""
        if not self.is_running or not self.scheduler:
            return []

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": (
                        job.next_run_time.isoformat() if job.next_run_time else None
                    ),
                    "trigger": str(job.trigger),
                }
            )

        return jobs

    def toggle_task(self, task_id: str) -> bool:
        """작업 활성화/비활성화 토글"""
        task = self.get_task(task_id)
        if not task:
            return False

        task.enabled = not task.enabled
        return self.update_task(task)

    def set_enabled(self, enabled: bool) -> None:
        """스케줄러 전체 활성화/비활성화"""
        self.settings.enabled = enabled
        self.save_settings()

        if enabled and not self.is_running:
            self.start()
        elif not enabled and self.is_running:
            self.stop()

    # ------------------------------------------------------------------
    # 내부 유틸리티
    # ------------------------------------------------------------------

    def _get_session(self) -> aiohttp.ClientSession:
        """공유 aiohttp 세션을 반환(없으면 생성)"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _close_session(self) -> None:
        """aiohttp 세션 정리"""
        if self._session and not self._session.closed:
            await self._session.close()
