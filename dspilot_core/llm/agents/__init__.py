"""
Agents 서브패키지
=================

`dspilot_core.llm.agents` 는 **에이전트 구체 구현체** 모음을 제공합니다.
현재는 `UnifiedAgent` 가 대부분의 기능을 흡수했지만, 계층 분리를 위해
아래 구조를 유지합니다.

• `base_agent.py`      : 공통 인터페이스 및 기본 기능
• `unified_agent.py`   : 툴·워크플로우 인지형 통합 에이전트 (권장 사용)
• `mixins/*`           : 설정 관리, 대화 상태, 도구 처리 기능 믹스인
• `agent_factory.py`   : 설정을 기반으로 적절한 에이전트 인스턴스를 생성하는
                          *Simple Factory* 구현

에이전트 라이프사이클
-------------------
```mermaid
sequenceDiagram
    participant UI/CLI
    participant Factory
    participant Agent
    participant Workflow
    UI/CLI->>Factory: create_agent(config)
    Factory-->>Agent: UnifiedAgent
    Agent->>Workflow: select & execute
    Workflow-->>Agent: response
    Agent-->>UI/CLI: final answer
```
"""
