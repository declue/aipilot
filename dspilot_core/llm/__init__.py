"""
DSPilot Core – LLM 서브시스템
===========================

이 패키지는 DSPilot 에이전트의 **언어 모델 계층**을 담당합니다. 핵심 목적은
외부 LLM(OpenAI, Ollama, 기타 로컬 모델 등)과 MCP(Multi-Capability Plugin)
도구를 통합하여 다음 기능을 제공하는 것입니다.

• 대화 컨텍스트 관리 (`services.conversation_service`)
• Langchain 기반 LLM 호출 (`services.llm_service`)
• 에이전트(Agent) 추상화 및 팩토리 (`agents.*`)
• MCP 도구 인터페이스 (`mcp.*`)
• 워크플로우 엔진 (`workflow.*`) – RAG·Tool-Aware·React 등
• 실행 결과 후처리 Processor (`processors.*`)
• 모니터링/메트릭 수집 (`monitoring.*`)

아키텍처 개요
-------------
```mermaid
graph TD
    subgraph Agent Layer
        PA[ProblemAgent] --> WF[Workflow Engine]
    end
    subgraph Service Layer
        WF -->|Executes Steps| MCP[MCP ToolManager]
        WF --> LLMService
    end
    subgraph Infrastructure
        MCP --> ExternalTools
        LLMService --> OpenAI_API
    end
```

설계 원칙
---------
1. **SOLID** : 각 서브패키지는 단일 책임을 갖도록 분리.
2. **Plugin Friendly** : 새 워크플로우·에이전트·도구 추가 시 기존 코드 변경 최소화.
3. **Async-First** : 네트워크·I/O 요청은 `async` 로 구현하여 UI/CLI 블로킹 방지.
4. **Testability** : 테스트 더블(Mock, Stub)을 활용할 수 있도록 인터페이스/ABC 사용.

하위 패키지
-----------
• `agents`      : 다양한 에이전트 구현체와 믹스인
• `mcp`         : MCP 서버/도구 관리
• `workflow`    : 질의 처리 전략 집합
• `services`    : LLM 호출, 대화 기록 등 상태ful 서비스
• `processors`  : 도구 실행 결과 후처리
• `monitoring`  : 성능 및 사용량 추적
• `utils`       : 보조 유틸리티
"""

from dspilot_core.llm.monitoring.metrics import get_global_metrics, track_response
from dspilot_core.llm.monitoring.performance_tracker import PerformanceTracker
from dspilot_core.llm.utils.logging_utils import get_llm_logger
from dspilot_core.llm.validators.config_validator import LLMConfigValidator, MCPConfigValidator

__all__ = [
    "LLMConfigValidator",
    "MCPConfigValidator",
    "track_response",
    "get_global_metrics",
    "PerformanceTracker",
    "get_llm_logger",
] 
