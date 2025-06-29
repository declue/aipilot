"""
워크플로우 유틸리티 함수 및 레지스트리
===================================

DSPilot 워크플로우 시스템의 핵심 유틸리티 함수들과 워크플로우 레지스트리를 제공합니다.
워크플로우의 등록, 조회, 관리 기능을 담당하며, 플러그인 형태의 워크플로우 확장을 지원합니다.

주요 기능
=========

1. **워크플로우 레지스트리**
   - 사용 가능한 모든 워크플로우 클래스 관리
   - 이름 기반 워크플로우 조회 및 인스턴스 생성
   - 동적 워크플로우 등록 지원

2. **레거시 호환성**
   - 기존 설정 파일과의 호환성 보장
   - 구 버전 워크플로우 이름 자동 매핑
   - 무중단 마이그레이션 지원

3. **React Agent 지원**
   - LangChain React Agent용 스트리밍 유틸리티
   - 그래프 기반 실행 지원
   - 실시간 진행 상황 피드백

워크플로우 레지스트리 구조
=========================

현재 등록된 워크플로우:

### 핵심 워크플로우
- **"smart"**: SmartWorkflow (권장) - 복잡도 자동 판단 통합 워크플로우
- **"basic"**: BasicChatWorkflow - 순수 LLM 기반 질의응답
- **"research"**: ResearchWorkflow - 전문 리서치 및 조사

### 레거시 호환 매핑
- **"agent"** → SmartWorkflow (구 AgentWorkflow)
- **"tool"** → SmartWorkflow (구 ToolWorkflow)  
- **"adaptive"** → SmartWorkflow (구 AdaptiveWorkflow)
- **"basic_chat"** → BasicChatWorkflow (별칭)

사용법 가이드
============

### 1. 기본 워크플로우 조회 및 사용

```python
from dspilot_core.llm.workflow.workflow_utils import get_workflow

# 워크플로우 클래스 가져오기
WorkflowClass = get_workflow("smart")

# 인스턴스 생성 및 실행
workflow = WorkflowClass()
result = await workflow.run(agent, message, streaming_callback)
```

### 2. 사용 가능한 워크플로우 목록 확인

```python
from dspilot_core.llm.workflow.workflow_utils import get_available_workflows

available = get_available_workflows()
print("사용 가능한 워크플로우:", available)
# 출력: ['basic', 'research', 'smart', 'agent', 'tool', 'adaptive', 'basic_chat']
```

### 3. 커스텀 워크플로우 등록

```python
from dspilot_core.llm.workflow import BaseWorkflow
from dspilot_core.llm.workflow.workflow_utils import register_workflow

class MyCustomWorkflow(BaseWorkflow):
    async def run(self, agent, message, streaming_callback=None):
        return "커스텀 처리 결과"

# 워크플로우 등록
register_workflow("my_custom", MyCustomWorkflow)

# 등록 후 사용
CustomWorkflow = get_workflow("my_custom")
```

### 4. 에이전트에서 워크플로우 선택

```python
class ProblemAgent(BaseAgent):
    def _get_workflow_name(self, mode: str) -> str:
        mode_mapping = {
            "basic": "basic",           # BasicChatWorkflow
            "mcp_tools": "smart",       # SmartWorkflow  
            "workflow": "smart",        # SmartWorkflow
            "auto": "smart",            # SmartWorkflow
            "research": "research"      # ResearchWorkflow
        }
        return mode_mapping.get(mode, "smart")  # 기본값: smart
        
    async def generate_response(self, message, streaming_callback=None):
        workflow_name = self._get_workflow_name(self.llm_mode)
        WorkflowClass = get_workflow(workflow_name)
        workflow = WorkflowClass()
        return await workflow.run(self, message, streaming_callback)
```

레거시 호환성 세부사항
====================

### 자동 매핑 규칙
기존 설정 파일에서 사용하던 워크플로우 이름들이 새로운 통합 워크플로우로 자동 매핑됩니다:

```python
# 기존 설정 파일
{
    "llm_mode": "agent"  # 또는 "tool", "adaptive"
}

# 자동으로 SmartWorkflow로 매핑되어 동작
# 설정 파일 수정 불필요
```

### 마이그레이션 가이드
1. **즉시 사용 가능**: 기존 설정 파일 수정 없이 바로 사용
2. **권장 업데이트**: 새로운 설정에서는 "smart" 사용 권장
3. **단계적 전환**: 필요에 따라 점진적으로 설정 업데이트

React Agent 지원 함수
====================

### astream_graph 함수

LangChain React Agent의 그래프 실행을 위한 스트리밍 유틸리티:

```python
async def astream_graph(
    graph,                                    # 실행할 그래프
    inputs: Dict[str, Any],                  # 입력 데이터  
    config: Optional[RunnableConfig] = None, # 실행 설정
    streaming_callback: Optional[Callable[[str], None]] = None  # 콜백
) -> AsyncGenerator[str, None]:
```

**주요 기능**:
- 그래프 실행 결과의 실시간 스트리밍
- 메시지 추출 및 포맷팅
- 오류 처리 및 로깅
- UUID 기반 스레드 관리

**사용 예시**:
```python
async for chunk in astream_graph(react_graph, inputs, config, callback):
    print(f"실시간 출력: {chunk}")
```

오류 처리 및 로깅
================

### 워크플로우 조회 오류
```python
try:
    workflow_class = get_workflow("non_existent")
except ValueError as e:
    print(f"오류: {e}")
    # 출력: 지원하지 않는 워크플로우: non_existent. 사용 가능한 워크플로우: basic, research, smart, ...
```

### 스트리밍 실행 오류
- 그래프 실행 중 오류 발생 시 자동으로 오류 메시지 스트리밍
- 로그에 상세한 오류 정보 기록
- 부분 실행 결과라도 사용자에게 전달

성능 및 최적화
=============

### 레지스트리 성능
- 딕셔너리 기반 O(1) 조회 성능
- 메모리 효율적인 클래스 참조 저장
- 지연 로딩으로 초기화 시간 최소화

### 스트리밍 최적화
- 청크 단위 실시간 전송
- 불필요한 빈 메시지 필터링
- 메모리 사용량 최소화

확장 가이드
===========

### 새로운 워크플로우 추가 패턴

```python
# 1. BaseWorkflow 상속
class NewWorkflow(BaseWorkflow):
    async def run(self, agent, message, streaming_callback=None):
        # 워크플로우 로직 구현
        return "결과"

# 2. 패키지 __init__.py에 추가
from .new_workflow import NewWorkflow
__all__.append("NewWorkflow")

# 3. workflow_utils.py 레지스트리에 등록
_WORKFLOW_REGISTRY["new"] = NewWorkflow

# 4. 문서 업데이트
# README.md, 패키지 문서에 새 워크플로우 설명 추가
```

### 플러그인 방식 확장

```python
# 외부 플러그인에서 워크플로우 등록
def register_plugin_workflows():
    from my_plugin.workflows import AdvancedWorkflow
    register_workflow("advanced", AdvancedWorkflow)

# 애플리케이션 시작 시 호출
register_plugin_workflows()
```

문제 해결
=========

### 일반적인 문제들

1. **워크플로우를 찾을 수 없음**
   - `get_available_workflows()`로 사용 가능한 목록 확인
   - 오타나 대소문자 확인

2. **레거시 워크플로우 동작 이상**
   - 로그에서 자동 매핑 메시지 확인
   - 필요시 명시적으로 "smart" 사용

3. **스트리밍 콜백 작동 안함**
   - 콜백 함수 시그니처 확인: `(str) -> None`
   - 비동기 함수인 경우 동기 함수로 변경

4. **성능 이슈**
   - 워크플로우별 특성 확인 (ResearchWorkflow는 다소 느림)
   - 스트리밍 콜백 내부 로직 최적화
"""

import logging
import uuid
from typing import Any, AsyncGenerator, Callable, Dict, Optional, Type

from langchain_core.runnables import RunnableConfig

from dspilot_core.llm.workflow.base_workflow import BaseWorkflow
from dspilot_core.llm.workflow.basic_chat_workflow import BasicChatWorkflow
from dspilot_core.llm.workflow.code_modification_workflow import CodeModificationWorkflow
from dspilot_core.llm.workflow.research_workflow import ResearchWorkflow
from dspilot_core.llm.workflow.smart_workflow import SmartWorkflow
from dspilot_core.util.logger import setup_logger

logger = setup_logger("workflow_utils") or logging.getLogger("workflow_utils")


# 워크플로우 레지스트리
_WORKFLOW_REGISTRY: Dict[str, Type[BaseWorkflow]] = {
    # === 핵심 워크플로우 ===
    "basic": BasicChatWorkflow,      # 순수 LLM 기반 질의응답
    "code_mod": CodeModificationWorkflow,  # 코드 수정 전용 워크플로우
    "research": ResearchWorkflow,    # 전문 리서치 및 조사  
    "smart": SmartWorkflow,          # 통합 스마트 워크플로우 (권장)
    
    # === 레거시 호환 매핑 ===
    "agent": SmartWorkflow,          # 구 AgentWorkflow → SmartWorkflow
    "tool": SmartWorkflow,           # 구 ToolWorkflow → SmartWorkflow
    "adaptive": SmartWorkflow,       # 구 AdaptiveWorkflow → SmartWorkflow
    "basic_chat": BasicChatWorkflow, # BasicChatWorkflow 별칭
}


def get_workflow(workflow_name: str) -> Type[BaseWorkflow]:
    """
    워크플로우 이름으로 워크플로우 클래스 반환

    워크플로우 레지스트리에서 지정된 이름의 워크플로우 클래스를 조회합니다.
    레거시 워크플로우 이름도 자동으로 새로운 워크플로우로 매핑됩니다.

    Args:
        workflow_name: 워크플로우 이름 (대소문자 무관)

    Returns:
        Type[BaseWorkflow]: 워크플로우 클래스

    Raises:
        ValueError: 지원하지 않는 워크플로우인 경우

    Examples:
        >>> WorkflowClass = get_workflow("smart")
        >>> workflow = WorkflowClass()
        >>> 
        >>> # 레거시 이름도 자동 매핑
        >>> AgentWorkflow = get_workflow("agent")  # SmartWorkflow 반환
    """
    workflow_name = workflow_name.lower()

    if workflow_name not in _WORKFLOW_REGISTRY:
        available_workflows = ", ".join(sorted(_WORKFLOW_REGISTRY.keys()))
        raise ValueError(
            f"지원하지 않는 워크플로우: {workflow_name}. "
            f"사용 가능한 워크플로우: {available_workflows}"
        )

    workflow_class = _WORKFLOW_REGISTRY[workflow_name]
    
    # 레거시 매핑 로깅
    if workflow_name in ["agent", "tool", "adaptive"]:
        logger.debug(f"레거시 워크플로우 '{workflow_name}'를 SmartWorkflow로 매핑")
    
    logger.debug(f"워크플로우 반환: {workflow_name} → {workflow_class.__name__}")
    return workflow_class


def register_workflow(name: str, workflow_class: Type[BaseWorkflow]) -> None:
    """
    새로운 워크플로우 등록

    워크플로우 레지스트리에 새로운 워크플로우 클래스를 등록합니다.
    플러그인이나 확장 모듈에서 커스텀 워크플로우를 추가할 때 사용합니다.

    Args:
        name: 워크플로우 이름 (소문자 권장)
        workflow_class: BaseWorkflow를 상속받은 워크플로우 클래스

    Raises:
        TypeError: workflow_class가 BaseWorkflow를 상속받지 않은 경우

    Examples:
        >>> class MyWorkflow(BaseWorkflow):
        ...     async def run(self, agent, message, streaming_callback=None):
        ...         return "커스텀 결과"
        >>> 
        >>> register_workflow("my_custom", MyWorkflow)
        >>> 
        >>> # 등록 후 사용
        >>> workflow = get_workflow("my_custom")()
    """
    if not issubclass(workflow_class, BaseWorkflow):
        raise TypeError(f"워크플로우 클래스는 BaseWorkflow를 상속받아야 합니다: {workflow_class}")
    
    name = name.lower()
    _WORKFLOW_REGISTRY[name] = workflow_class
    logger.info(f"워크플로우 등록 완료: {name} → {workflow_class.__name__}")


def get_available_workflows() -> list[str]:
    """
    사용 가능한 워크플로우 목록 반환

    현재 레지스트리에 등록된 모든 워크플로우 이름을 정렬된 목록으로 반환합니다.
    핵심 워크플로우와 레거시 호환 이름을 모두 포함합니다.

    Returns:
        list[str]: 정렬된 워크플로우 이름 목록

    Examples:
        >>> workflows = get_available_workflows()
        >>> print("사용 가능한 워크플로우:", workflows)
        ['adaptive', 'agent', 'basic', 'basic_chat', 'research', 'smart', 'tool']
    """
    return sorted(_WORKFLOW_REGISTRY.keys())


def random_uuid() -> str:
    """
    랜덤 UUID 생성

    스레드 ID나 고유 식별자가 필요한 경우 사용합니다.
    주로 React Agent의 스레드 관리에 활용됩니다.

    Returns:
        str: UUID4 문자열

    Examples:
        >>> thread_id = random_uuid()
        >>> print(f"생성된 UUID: {thread_id}")
    """
    return str(uuid.uuid4())


async def astream_graph(
    graph,
    inputs: Dict[str, Any],
    config: Optional[RunnableConfig] = None,
    streaming_callback: Optional[Callable[[str], None]] = None,
) -> AsyncGenerator[str, None]:
    """
    그래프 스트리밍 실행 (React Agent용)
    
    LangChain React Agent의 그래프를 실행하고 결과를 실시간으로 스트리밍합니다.
    메시지 추출, 포맷팅, 오류 처리를 자동으로 수행합니다.
    
    Args:
        graph: 실행할 LangChain 그래프 객체
        inputs: 그래프 입력 데이터 딕셔너리
        config: LangChain RunnableConfig (선택사항)
        streaming_callback: 실시간 출력 콜백 함수 (선택사항)
        
    Yields:
        str: 그래프 실행 결과의 텍스트 청크
        
    Examples:
        >>> async for chunk in astream_graph(react_graph, {"input": "질문"}, config):
        ...     print(f"실시간: {chunk}")
        
        >>> # 콜백과 함께 사용
        >>> def callback(text):
        ...     print(f"[STREAM] {text}")
        >>> 
        >>> async for chunk in astream_graph(graph, inputs, config, callback):
        ...     # 추가 처리
        ...     pass
    """
    # 스레드 ID 설정 (config에서 추출하거나 새로 생성)
    thread_id = (
        config.get("configurable", {}).get("thread_id") 
        if config else str(uuid.uuid4())
    )
    
    logger.debug(f"그래프 스트리밍 시작 - 스레드 ID: {thread_id}")
    
    try:
        async for chunk in graph.astream(inputs, config=config):
            if isinstance(chunk, dict):
                # 딕셔너리 형태의 청크 처리
                for node_name, output in chunk.items():
                    logger.debug(f"노드 '{node_name}' 출력 처리 중")
                    
                    if "messages" in output:
                        # 메시지 형태의 출력 처리
                        for message in output["messages"]:
                            content = getattr(message, "content", str(message))
                            if content and content.strip():
                                if streaming_callback:
                                    streaming_callback(content)
                                yield content
                    else:
                        # 일반 출력 처리
                        content = str(output)
                        if content and content.strip():
                            if streaming_callback:
                                streaming_callback(content)
                            yield content
            else:
                # 단순 청크 처리
                content = str(chunk)
                if content and content.strip():
                    if streaming_callback:
                        streaming_callback(content)
                    yield content
                    
    except Exception as e:
        error_msg = f"그래프 스트리밍 실행 오류: {e}"
        logger.error(error_msg)
        
        # 오류도 스트리밍으로 전달
        if streaming_callback:
            streaming_callback(error_msg)
        yield error_msg
