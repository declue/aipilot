"""
BaseWorkflow 모듈
=================

모든 워크플로우의 최소 공통 인터페이스를 정의하는 **추상 기반 클래스**. 각
워크플로우는 `run()` 코루틴을 구현하여 에이전트와 사용자 메시지를 입력 받아
최종 응답 문자열을 반환해야 합니다.

설계 노트
---------
• 워크플로우는 상태를 가질 수 있으며, `cleanup()` 메서드를 선택적으로
  구현해 리소스를 해제할 수 있습니다.  
• 에이전트(`BaseAgent`) 와의 결합도를 낮추기 위해 `Any` 타입을 사용하지만
  런타임에서는 실제 에이전트 구현을 기대합니다.

사용 예시
---------
```python
class HelloWorkflow(BaseWorkflow):
    async def run(self, agent, message: str, streaming_callback=None):
        return "안녕하세요!"
```
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
