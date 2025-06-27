"""
워크플로우 기본 클래스
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class BaseWorkflow(ABC):
    """워크플로우 기본 추상 클래스"""

    @abstractmethod
    async def run(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        워크플로우 실행

        Args:
            agent: LLM 에이전트
            message: 입력 메시지
            streaming_callback: 스트리밍 콜백

        Returns:
            str: 처리 결과
        """
        pass
