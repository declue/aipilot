"""
Agents 서브패키지
=================

`dspilot_core.llm.agents` 는 **에이전트 구체 구현체** 모음을 제공합니다.
현재는 `ProblemAgent` 가 대부분의 기능을 담당하며, 계층 분리를 위해
아래 구조를 유지합니다.

• `base_agent.py`      : 공통 인터페이스 및 기본 기능
• `mixins/*`           : 설정 관리, 대화 상태, 도구 처리 기능 믹스인
• `agent_factory.py`   : 설정을 기반으로 적절한 에이전트 인스턴스를 생성하는
                          *Simple Factory* 구현
• `ask_agent.py`       : 단순 정보 조회용 AskAgent
• `problem_agent.py`   : 복합 문제 해결용 ProblemAgent

에이전트 라이프사이클
-------------------
```mermaid
sequenceDiagram
    participant UI/CLI
    participant Factory
    participant Agent
    participant Workflow
    UI/CLI->>Factory: create_agent(config)
    Factory-->>Agent: ProblemAgent
    Agent->>Workflow: select & execute
    Workflow-->>Agent: response
    Agent-->>UI/CLI: final answer
```
"""
