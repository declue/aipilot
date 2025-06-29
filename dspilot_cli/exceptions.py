from typing import Optional


class CLIError(Exception):
    """DSPilot CLI 기본 예외 클래스"""


class ManagerInitializationError(CLIError):
    """개별 매니저 초기화 실패 예외"""

    def __init__(self, manager_name: str, original_error: Optional[Exception] = None):
        self.manager_name = manager_name
        self.original_error = original_error
        message = f"{manager_name} 초기화에 실패했습니다"
        if original_error:
            message += f" → {original_error}"
        super().__init__(message)


class SystemInitializationError(CLIError):
    """시스템 전역 초기화 실패 예외"""

    def __init__(self, reason: str):
        super().__init__(f"시스템 초기화 실패: {reason}")


class ExecutionError(CLIError):
    """워크플로우 실행 단계에서 발생한 예외"""

    def __init__(self, step: str, original_error: Optional[Exception] = None):
        self.step = step
        self.original_error = original_error
        message = f"'{step}' 단계 실행 중 오류가 발생했습니다"
        if original_error:
            message += f" → {original_error}"
        super().__init__(message)


class CleanupError(CLIError):
    """리소스 정리 단계에서 발생한 예외"""

    def __init__(self, original_error: Exception):
        self.original_error = original_error
        super().__init__(f"리소스 정리 실패: {original_error}")


class CommandHandlerError(CLIError):
    """명령어 처리 중 발생한 예외"""

    def __init__(self, command: str, original_error: Optional[Exception] = None):
        self.command = command
        self.original_error = original_error
        message = f"명령 '{command}' 처리 중 오류가 발생했습니다"
        if original_error:
            message += f" → {original_error}"
        super().__init__(message)


class ModeHandlerError(CLIError):
    """모드 전환/실행 중 발생한 예외"""

    def __init__(self, mode: str, original_error: Optional[Exception] = None):
        self.mode = mode
        self.original_error = original_error
        message = f"{mode} 모드 실행 중 오류가 발생했습니다"
        if original_error:
            message += f" → {original_error}"
        super().__init__(message) 