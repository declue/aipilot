"""
워크플로우 기본 클래스 (BaseWorkflow)
===================================

DSPilot 워크플로우 시스템의 추상 기본 클래스입니다.
모든 워크플로우는 이 클래스를 상속받아 구현되며, 일관된 인터페이스를 제공합니다.

워크플로우 시스템 개요
====================

DSPilot의 워크플로우 시스템은 다양한 유형의 사용자 요청을 처리하기 위한
전략 패턴(Strategy Pattern)을 구현합니다. 각 워크플로우는 특정 작업 유형에
최적화된 처리 방식을 제공합니다.

### 현재 구현된 워크플로우:

1. **SmartWorkflow** (권장)
   - 복잡도 자동 분석으로 최적 처리 방식 선택
   - 단순/복잡 요청 모두 효율적 처리

2. **BasicChatWorkflow**
   - 순수 LLM 기반 질의응답
   - 빠르고 간결한 상호작용

3. **ResearchWorkflow**
   - Perplexity 스타일 전문 리서치
   - 다각도 검색 및 종합 분석

워크플로우 구현 가이드
====================

### 기본 구조

모든 워크플로우는 다음 추상 메서드를 구현해야 합니다:

```python
class MyWorkflow(BaseWorkflow):
    async def run(
        self, 
        agent: Any, 
        message: str, 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        # 워크플로우 로직 구현
        return "처리 결과"
```

### 구현 시 고려사항

1. **비동기 처리**: 모든 워크플로우는 async/await 패턴 사용
2. **스트리밍 지원**: streaming_callback을 통한 실시간 피드백 제공
3. **오류 처리**: 예외 발생 시 적절한 오류 메시지 반환
4. **로깅**: 디버깅을 위한 적절한 로그 기록

### 예시 구현

```python
import logging
from typing import Any, Callable, Optional
from dspilot_core.llm.workflow.base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)

class ExampleWorkflow(BaseWorkflow):
    \"\"\"예시 워크플로우 구현\"\"\"
    
    async def run(
        self, 
        agent: Any, 
        message: str, 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        try:
            logger.info(f"ExampleWorkflow 시작: {message[:50]}...")
            
            if streaming_callback:
                streaming_callback("처리 시작...\n")
            
            # 실제 처리 로직
            result = await self._process_message(agent, message)
            
            if streaming_callback:
                streaming_callback("처리 완료!\n")
            
            logger.info("ExampleWorkflow 완료")
            return result
            
        except Exception as e:
            logger.error(f"ExampleWorkflow 오류: {e}")
            return f"처리 중 오류가 발생했습니다: {str(e)}"
    
    async def _process_message(self, agent: Any, message: str) -> str:
        # 구체적인 처리 로직 구현
        return await agent._generate_basic_response(message, None)
```

워크플로우 등록 및 사용
=====================

### 1. 워크플로우 등록

```python
from dspilot_core.llm.workflow.workflow_utils import register_workflow

# 커스텀 워크플로우 등록
register_workflow("example", ExampleWorkflow)
```

### 2. 워크플로우 사용

```python
from dspilot_core.llm.workflow.workflow_utils import get_workflow

# 워크플로우 클래스 가져오기
WorkflowClass = get_workflow("example")

# 인스턴스 생성 및 실행
workflow = WorkflowClass()
result = await workflow.run(agent, message, streaming_callback)
```

### 3. 에이전트 통합

```python
class MyAgent(BaseAgent):
    def _get_workflow_name(self, mode: str) -> str:
        if mode == "example":
            return "example"
        elif mode == "basic":
            return "basic"
        else:
            return "smart"  # 기본값
```

인터페이스 명세
==============

### run 메서드 시그니처

```python
async def run(
    self, 
    agent: Any,                                           # LLM 에이전트 인스턴스
    message: str,                                         # 사용자 입력 메시지
    streaming_callback: Optional[Callable[[str], None]] = None  # 스트리밍 콜백
) -> str:                                                # 처리 결과 문자열
```

### 매개변수 설명

- **agent**: BaseAgent를 상속받은 LLM 에이전트 인스턴스
  - `_generate_basic_response()` 메서드 제공
  - `mcp_tool_manager` 속성 (MCP 도구 사용 시)
  
- **message**: 사용자가 입력한 원본 메시지
  - 전처리 없이 그대로 전달됨
  - 워크플로우에서 필요에 따라 가공 처리
  
- **streaming_callback**: 실시간 출력을 위한 콜백 함수
  - 시그니처: `(content: str) -> None`
  - 진행 상황, 중간 결과 등을 실시간으로 전달
  - None인 경우 스트리밍 없이 최종 결과만 반환

### 반환값

- **str**: 워크플로우 처리 결과
  - 사용자에게 표시될 최종 응답
  - 마크다운 형식 지원
  - 오류 발생 시에도 문자열로 오류 메시지 반환

모범 사례
=========

### 1. 로깅 활용

```python
import logging
logger = logging.getLogger(__name__)

class MyWorkflow(BaseWorkflow):
    async def run(self, agent, message, streaming_callback=None):
        logger.info(f"워크플로우 시작: {self.__class__.__name__}")
        # ... 처리 로직
        logger.info("워크플로우 완료")
```

### 2. 스트리밍 콜백 활용

```python
async def run(self, agent, message, streaming_callback=None):
    if streaming_callback:
        streaming_callback("🔄 처리 시작...\n")
    
    # 중간 진행 상황 전달
    if streaming_callback:
        streaming_callback("📊 데이터 분석 중...\n")
    
    # 최종 결과 전달
    if streaming_callback:
        streaming_callback("✅ 처리 완료!\n")
```

### 3. 오류 처리

```python
async def run(self, agent, message, streaming_callback=None):
    try:
        # 메인 처리 로직
        return await self._main_process(agent, message)
    except SpecificError as e:
        logger.warning(f"특정 오류 발생: {e}")
        return "특정 오류에 대한 사용자 친화적 메시지"
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        return f"처리 중 오류가 발생했습니다: {str(e)}"
```

### 4. 설정 가능한 워크플로우

```python
class ConfigurableWorkflow(BaseWorkflow):
    def __init__(self, max_iterations=5, timeout=30):
        self.max_iterations = max_iterations
        self.timeout = timeout
    
    async def run(self, agent, message, streaming_callback=None):
        # 설정값을 활용한 처리
        pass
```

확장성 고려사항
==============

### 1. 하위 호환성 유지

새로운 기능을 추가할 때는 기존 워크플로우와의 호환성을 유지해야 합니다.

### 2. 플러그인 아키텍처

워크플로우 시스템은 플러그인 형태의 확장을 지원합니다.
외부 모듈에서 새로운 워크플로우를 등록할 수 있습니다.

### 3. 메타데이터 지원

향후 워크플로우 메타데이터(설명, 카테고리, 버전 등) 지원을 고려하여
확장 가능한 구조로 설계되었습니다.

문제 해결
=========

### 일반적인 구현 오류

1. **비동기 메서드 미사용**: `async def run()` 필수
2. **반환값 누락**: 반드시 문자열 반환
3. **예외 처리 부족**: try-except 블록으로 안전성 확보
4. **스트리밍 콜백 무시**: 사용자 경험을 위해 적극 활용 권장

### 성능 최적화

1. **불필요한 LLM 호출 최소화**
2. **중간 결과 캐싱 활용**  
3. **병렬 처리 가능한 부분 식별**
4. **메모리 사용량 모니터링**
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class BaseWorkflow(ABC):
    """
    워크플로우 추상 기본 클래스
    
    DSPilot의 모든 워크플로우가 상속받아야 하는 기본 클래스입니다.
    일관된 인터페이스를 제공하여 워크플로우 간 호환성을 보장합니다.
    
    모든 워크플로우는 run() 메서드를 구현해야 하며, 다음 원칙을 따라야 합니다:
    - 비동기 처리 (async/await)
    - 스트리밍 콜백 지원
    - 적절한 오류 처리
    - 문자열 결과 반환
    
    Examples:
        >>> class MyWorkflow(BaseWorkflow):
        ...     async def run(self, agent, message, streaming_callback=None):
        ...         return "처리 결과"
        >>> 
        >>> workflow = MyWorkflow()
        >>> result = await workflow.run(agent, "사용자 메시지")
    """

    @abstractmethod
    async def run(
        self, 
        agent: Any, 
        message: str, 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        워크플로우 실행 (추상 메서드)
        
        모든 워크플로우가 구현해야 하는 핵심 메서드입니다.
        사용자 요청을 처리하고 결과를 반환합니다.
        
        Args:
            agent: LLM 에이전트 인스턴스 (BaseAgent 상속)
            message: 사용자 입력 메시지
            streaming_callback: 실시간 출력 콜백 함수 (선택사항)
                - 시그니처: (content: str) -> None
                - 진행 상황이나 중간 결과를 실시간으로 전달
                
        Returns:
            str: 워크플로우 처리 결과
                - 사용자에게 표시될 최종 응답
                - 마크다운 형식 지원
                - 오류 발생 시에도 문자열로 오류 메시지 반환
                
        Raises:
            NotImplementedError: 하위 클래스에서 구현하지 않은 경우
            
        Note:
            - 반드시 비동기 메서드로 구현
            - 예외 발생 시 적절한 오류 메시지 문자열 반환 권장
            - streaming_callback이 제공된 경우 적극 활용하여 사용자 경험 향상
        """
        pass
