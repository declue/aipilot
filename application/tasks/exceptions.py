"""작업 관리 시스템 예외 클래스"""


class TaskManagerError(Exception):
    """작업 관리자 기본 예외"""
    pass


class TaskExecutionError(TaskManagerError):
    """작업 실행 오류"""
    
    def __init__(self, task_id: str, message: str, original_error: Exception | None = None):
        self.task_id = task_id
        self.original_error = original_error
        super().__init__(f"Task '{task_id}' execution failed: {message}")


class TaskSchedulerError(TaskManagerError):
    """작업 스케줄러 오류"""
    pass


class TaskConfigurationError(TaskManagerError):
    """작업 설정 오류"""
    pass


class HttpClientError(TaskManagerError):
    """HTTP 클라이언트 오류"""
    
    def __init__(self, url: str, status_code: int | None = None, message: str | None = None):
        self.url = url
        self.status_code = status_code
        error_msg = f"HTTP request to '{url}' failed"
        if status_code:
            error_msg += f" with status {status_code}"
        if message:
            error_msg += f": {message}"
        super().__init__(error_msg) 