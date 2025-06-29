"""
Workflow 서브패키지
===================

`dspilot_core.llm.workflow` 는 사용자 질의를 **전략 패턴** 형태로 처리하는
다양한 워크플로우(Workflow) 구현을 제공합니다.

• `base_workflow.py`    : 최소 인터페이스 정의 (run)
• `agent_workflow.py`   : 기본 Tool-Aware 에이전트 워크플로우
• `adaptive_workflow.py`: 검색·도구 사용 여부를 LLM이 스스로 판단하도록
                          하는 적응형 워크플로우
• `research_workflow.py`: 심층 리서치 전용 – 다단계 웹 검색 + 검증

워크플로우 선택 로직은 `UnifiedAgent` 가 담당하며, **플러그인 형태**로
auto-discovery 할 수 있도록 추후 메타데이터 등록 방식으로 확장 예정입니다.
"""

from dspilot_core.llm.workflow.agent_workflow import AgentWorkflow
from dspilot_core.llm.workflow.base_workflow import BaseWorkflow
from dspilot_core.llm.workflow.basic_chat_workflow import BasicChatWorkflow
from dspilot_core.llm.workflow.workflow_utils import (
    get_available_workflows,
    get_workflow,
    register_workflow,
)

__all__ = ["BaseWorkflow", "BasicChatWorkflow", "AgentWorkflow", "get_workflow", "register_workflow", "get_available_workflows"] 
