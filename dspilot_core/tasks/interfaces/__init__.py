"""작업 관리 시스템 인터페이스 패키지"""

from dspilot_core.tasks.interfaces.http_client import IHttpClient
from dspilot_core.tasks.interfaces.task_configuration import ITaskConfiguration
from dspilot_core.tasks.interfaces.task_executor import ITaskExecutor
from dspilot_core.tasks.interfaces.task_scheduler import ITaskScheduler

__all__ = [
    "IHttpClient",
    "ITaskConfiguration",
    "ITaskExecutor",
    "ITaskScheduler",
]
