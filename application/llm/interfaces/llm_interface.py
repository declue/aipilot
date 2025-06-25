"""
LLM 인터페이스 정의 - 추상 기본 클래스
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional


class LLMInterface(ABC):
    """LLM 처리를 위한 추상 인터페이스"""

    @abstractmethod
    async def generate_response(
        self,
        user_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        사용자 메시지에 대한 응답 생성

        Args:
            user_message: 사용자 입력 메시지
            streaming_callback: 스트리밍 콜백 함수

        Returns:
            Dict[str, Any]: 응답 데이터 (response, reasoning, used_tools)
        """
        pass

    @abstractmethod
    def add_user_message(self, message: str) -> None:
        """사용자 메시지를 대화 히스토리에 추가"""
        pass

    @abstractmethod
    def add_assistant_message(self, message: str) -> None:
        """어시스턴트 메시지를 대화 히스토리에 추가"""
        pass

    @abstractmethod
    def clear_conversation(self) -> None:
        """대화 히스토리 초기화"""
        pass

    @abstractmethod
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """대화 히스토리 반환"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """리소스 정리"""
        pass
