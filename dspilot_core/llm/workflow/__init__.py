"""
DSPilot Workflow 패키지
=======================

DSPilot의 LLM 에이전트가 사용자 요청을 처리하는 다양한 전략을 제공하는 워크플로우 시스템입니다.
각 워크플로우는 특정 유형의 작업에 최적화되어 있으며, 에이전트가 상황에 맞는 최적의 처리 방식을 선택할 수 있도록 합니다.

워크플로우 아키텍처
==================

모든 워크플로우는 `BaseWorkflow` 추상 클래스를 상속받아 구현됩니다:

```python
class BaseWorkflow(ABC):
    @abstractmethod
    async def run(self, agent, message: str, streaming_callback=None) -> str:
        pass
```

사용 가능한 워크플로우
====================

1. **SmartWorkflow** (권장) - 통합 스마트 워크플로우
   - 요청 복잡도를 자동 분석하여 최적의 처리 방식 선택
   - 단순 요청: 직접 도구 실행
   - 복잡 요청: Plan & Execute 방식
   - 모든 MCP 도구와 호환

2. **BasicChatWorkflow** - 순수 LLM 대화
   - 도구 사용 없이 LLM만으로 응답 생성
   - 빠르고 간결한 질의응답
   - 일반적인 정보 제공 및 상담

3. **ResearchWorkflow** - 전문 리서치
   - Perplexity 스타일의 심층 조사
   - 다각도 웹검색 및 정보 검증
   - 종합 리서치 보고서 생성

워크플로우 사용법
================

### 1. 기본 사용법

```python
from dspilot_core.llm.workflow import get_workflow

# 워크플로우 클래스 가져오기
WorkflowClass = get_workflow("smart")
workflow = WorkflowClass()

# 워크플로우 실행
result = await workflow.run(agent, "사용자 메시지", streaming_callback)
```

### 2. 에이전트에서 사용

```python
class ProblemAgent(BaseAgent):
    def _get_workflow_name(self, mode: str) -> str:
        mode_mapping = {
            "basic": "basic",
            "mcp_tools": "smart",    # MCP 도구 사용
            "workflow": "smart",     # 복합 작업
            "auto": "smart",         # 자동 판단
            "research": "research"   # 전문 리서치
        }
        return mode_mapping.get(mode, "smart")
```

### 3. 스트리밍 콜백 사용

```python
def my_streaming_callback(content: str):
    print(f"실시간 출력: {content}")

result = await workflow.run(agent, message, my_streaming_callback)
```

워크플로우 선택 가이드
====================

### SmartWorkflow 사용 권장 상황:
- 일반적인 모든 사용자 요청
- MCP 도구 사용이 필요한 작업
- 복잡도를 미리 판단하기 어려운 요청
- 자동으로 최적화된 처리를 원하는 경우

### BasicChatWorkflow 사용 권장 상황:
- 순수 대화만 필요한 경우
- 외부 도구 없이 빠른 응답이 필요한 경우
- 간단한 질의응답이나 상담

### ResearchWorkflow 사용 권장 상황:
- 심층적인 조사가 필요한 주제
- 다각도 분석이 필요한 복잡한 질문
- 신뢰성 있는 정보 수집과 검증이 중요한 경우

새로운 워크플로우 추가
====================

```python
from dspilot_core.llm.workflow import BaseWorkflow, register_workflow

class MyCustomWorkflow(BaseWorkflow):
    async def run(self, agent, message: str, streaming_callback=None) -> str:
        # 커스텀 로직 구현
        return "처리 결과"

# 워크플로우 등록
register_workflow("my_custom", MyCustomWorkflow)

# 사용
workflow = get_workflow("my_custom")()
```

레거시 호환성
============

기존 설정 파일에서 사용하던 다음 워크플로우 이름들은 자동으로 SmartWorkflow로 매핑됩니다:
- "agent" → SmartWorkflow
- "tool" → SmartWorkflow  
- "adaptive" → SmartWorkflow

이는 기존 설정 파일의 수정 없이도 새로운 통합 워크플로우를 사용할 수 있도록 합니다.
"""

from dspilot_core.llm.workflow.base_workflow import BaseWorkflow
from dspilot_core.llm.workflow.basic_chat_workflow import BasicChatWorkflow
from dspilot_core.llm.workflow.code_modification_workflow import CodeModificationWorkflow
from dspilot_core.llm.workflow.research_workflow import ResearchWorkflow
from dspilot_core.llm.workflow.smart_workflow import SmartWorkflow
from dspilot_core.llm.workflow.workflow_utils import (
    get_available_workflows,
    get_workflow,
    register_workflow,
)

__all__ = [
    "BaseWorkflow", 
    "BasicChatWorkflow", 
    "CodeModificationWorkflow",
    "SmartWorkflow", 
    "ResearchWorkflow",
    "get_workflow", 
    "register_workflow", 
    "get_available_workflows"
] 
