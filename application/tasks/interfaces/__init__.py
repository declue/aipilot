"""작업 관리 시스템 인터페이스 패키지"""

from application.tasks.interfaces.http_client import IHttpClient
from application.tasks.interfaces.task_configuration import ITaskConfiguration
from application.tasks.interfaces.task_executor import ITaskExecutor
from application.tasks.interfaces.task_scheduler import ITaskScheduler

__all__ = [
    "IHttpClient",
    "ITaskConfiguration",
    "ITaskExecutor",
    "ITaskScheduler",
]
