"""작업 실행자 인터페이스"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from application.tasks.models.task_config import TaskConfig


class ITaskExecutor(ABC):
    """작업 실행자 인터페이스"""

    @abstractmethod
    async def execute_task(self, task: TaskConfig) -> Dict[str, Any]:
        """작업을 실행합니다.
        
        Args:
            task: 실행할 작업 설정
            
        Returns:
            작업 실행 결과
            
        Raises:
            TaskExecutionError: 작업 실행 실패 시
        """
        pass

    @abstractmethod
    async def execute_llm_request(self, task: TaskConfig) -> Dict[str, Any]:
        """LLM 요청을 실행합니다.
        
        Args:
            task: LLM 요청 작업 설정
            
        Returns:
            LLM 응답 결과
        """
        pass

    @abstractmethod
    async def execute_api_call(self, task: TaskConfig) -> Dict[str, Any]:
        """API 호출을 실행합니다.
        
        Args:
            task: API 호출 작업 설정
            
        Returns:
            API 응답 결과
        """
        pass

    @abstractmethod
    async def execute_notification(self, task: TaskConfig) -> Dict[str, Any]:
        """알림을 실행합니다.
        
        Args:
            task: 알림 작업 설정
            
        Returns:
            알림 처리 결과
        """
        pass 