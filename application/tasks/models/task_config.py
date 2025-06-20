"""작업 설정 모델"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class TaskConfig:
    """개별 작업 설정"""

    id: str
    name: str
    description: str
    cron_expression: str  # cron 표현식 (예: "0 10 * * *")
    action_type: str  # "llm_request", "api_call", "notification" 등
    action_params: Dict[str, Any]  # 작업별 파라미터
    enabled: bool = True
    created_at: Optional[str] = None
    last_run: Optional[str] = None
    run_count: int = 0

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskConfig":
        """딕셔너리에서 생성"""
        return cls(**data)

    def update_last_run(self) -> None:
        """마지막 실행 시간 업데이트"""
        self.last_run = datetime.now().isoformat()
        self.run_count += 1


@dataclass
class TaskSettings:
    """전체 작업 설정"""

    enabled: bool = True
    max_concurrent_jobs: int = 3
    timezone: str = "Asia/Seoul"
    log_level: str = "INFO"
    tasks: Dict[str, TaskConfig] = field(default_factory=dict)

    def add_task(self, task: TaskConfig) -> None:
        """작업 추가"""
        self.tasks[task.id] = task

    def remove_task(self, task_id: str) -> None:
        """작업 제거"""
        if task_id in self.tasks:
            del self.tasks[task_id]

    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        """작업 조회"""
        return self.tasks.get(task_id)

    def get_enabled_tasks(self) -> Dict[str, TaskConfig]:
        """활성화된 작업들 조회"""
        return {tid: task for tid, task in self.tasks.items() if task.enabled}

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "enabled": self.enabled,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "timezone": self.timezone,
            "log_level": self.log_level,
            "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskSettings":
        """딕셔너리에서 생성"""
        tasks_data = data.pop("tasks", {})
        settings = cls(**data)

        for tid, task_data in tasks_data.items():
            task = TaskConfig.from_dict(task_data)
            settings.tasks[tid] = task

        return settings


class TaskConfigFileManager:
    """작업 설정 파일 관리자 - 파일 I/O 책임 분리"""

    @staticmethod
    def save_to_file(task_settings: TaskSettings, file_path: str) -> None:
        """파일로 저장"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(task_settings.to_dict(), f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise RuntimeError(f"작업 설정 파일 저장 실패: {e}") from e

    @staticmethod
    def load_from_file(file_path: str) -> TaskSettings:
        """파일에서 로드"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return TaskSettings.from_dict(data)
        except FileNotFoundError:
            return TaskSettings()  # 기본 설정 반환
        except (IOError, json.JSONDecodeError) as e:
            raise RuntimeError(f"작업 설정 파일 로드 실패: {e}") from e
