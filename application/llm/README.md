# LLM 모듈 아키텍처 문서

## 개요

LLM 모듈은 대규모 언어 모델(Large Language Model)과의 상호작용을 관리하는 핵심 컴포넌트입니다. 이 모듈은 다양한 LLM 모델과 통합하고, 도구 사용 및 워크플로우 실행을 지원하며, 사용자 요청에 대한 응답을 생성합니다.

## 디렉토리 구조

```
application/llm/
├── mcp/                  # Multi-Component Platform 관련 코드
│   ├── config/           # MCP 설정 관리
│   ├── process/          # MCP 프로세스 관리
│   ├── tool/             # MCP 도구 관련 코드
│   ├── mcp_manager.py    # MCP 서버 관리
│   └── mcp_tool_manager.py # MCP 도구 관리 및 실행
├── workflow/             # 워크플로우 관련 코드
│   └── __init__.py       # 워크플로우 레지스트리 및 기본 클래스
├── llm_agent.py          # LLM 에이전트 핵심 클래스
└── __init__.py           # 패키지 초기화
```

## 주요 컴포넌트

### LLMAgent (llm_agent.py)

LLMAgent는 LLM 모듈의 핵심 클래스로, 다음과 같은 기능을 제공합니다:

- LLM 모델과의 통신 관리
- 사용자 메시지에 대한 응답 생성
- 대화 기록(history) 관리
- 도구 사용 여부 결정 및 도구 호출
- 워크플로우 모드 지원

주요 메서드:
- `generate_response`: 사용자 메시지에 대한 응답 생성
- `generate_response_streaming`: 스트리밍 방식으로 응답 생성
- `_respond`: 내부 응답 생성 로직 처리
- `_should_use_tools`: 도구 사용 여부 결정
- `_generate_with_tools`: 도구를 사용한 응답 생성
- `_generate_basic_response`: 기본 응답 생성

### MCP (Multi-Component Platform)

MCP는 외부 도구와의 통합을 위한 플랫폼으로, 다음과 같은 컴포넌트로 구성됩니다:

#### MCPManager (mcp/mcp_manager.py)
- MCP 서버 관리
- 서버 연결 테스트
- 서버 설정 관리

#### MCPToolManager (mcp/mcp_tool_manager.py)
- MCP 도구 관리 및 실행을 위한 고수준 퍼사드(Facade)
- 도구 메타데이터 캐싱
- OpenAI 함수 호출 형식으로 도구 변환
- ReAct(Reason-Act-Observe) 패턴 구현

주요 클래스:
- `ToolExecutor`: 단일 MCP 도구 호출 실행
- `ToolCache`: 도구 메타데이터 캐싱
- `ToolConverter`: 도구 스키마 변환

### 워크플로우 (workflow/)

워크플로우는 복잡한 LLM 작업을 단계별로 처리하기 위한 프레임워크를 제공합니다:

#### BaseWorkflow (workflow/__init__.py)
- 모든 워크플로우의 기본 인터페이스
- `run` 메서드 정의

#### SequentialWorkflow (workflow/__init__.py)
- 여러 단계를 순차적으로 실행하는 워크플로우
- 각 단계는 이전 단계의 결과를 입력으로 받음

#### BasicChatWorkflow (workflow/__init__.py)
- 기본 채팅 워크플로우 구현
- 단순 응답 생성

## 주요 흐름

### 기본 응답 생성 흐름
1. 사용자가 메시지 입력
2. LLMAgent가 메시지 수신
3. LLMAgent가 OpenAI API를 통해 응답 생성
4. 생성된 응답을 사용자에게 반환

### 도구 사용 흐름
1. 사용자가 메시지 입력
2. LLMAgent가 `_should_use_tools`를 통해 도구 사용 여부 결정
3. 도구 사용이 필요한 경우:
   - MCPToolManager를 통해 사용 가능한 도구 목록 가져오기
   - ReAct 패턴을 사용하여 도구 호출 및 결과 관찰
   - 최종 응답 생성
4. 생성된 응답을 사용자에게 반환

### 워크플로우 실행 흐름
1. 사용자가 메시지 입력
2. LLMAgent가 설정에 따라 워크플로우 모드 확인
3. 워크플로우 모드인 경우:
   - 워크플로우 레지스트리에서 워크플로우 가져오기
   - 워크플로우 실행
   - 워크플로우 결과를 사용자에게 반환

## 통합 다이어그램

```
┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │
│    사용자 UI     │◄────►│    LLMAgent     │
│                 │      │                 │
└─────────────────┘      └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  ConfigManager  │
                         └─────────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 │                                 │
        ┌────────▼─────────┐            ┌──────────▼─────────┐
        │                  │            │                     │
        │   Workflow       │            │   MCPToolManager    │
        │                  │            │                     │
        └──────────────────┘            └─────────┬───────────┘
                                                  │
                                        ┌─────────┴───────────┐
                                        │                     │
                                        │    MCPManager       │
                                        │                     │
                                        └─────────────────────┘
```

## 확장 방법

### 새로운 워크플로우 추가
1. `BaseWorkflow` 또는 `SequentialWorkflow`를 상속받는 새 클래스 생성
2. `run` 메서드 구현
3. `register_workflow` 함수를 사용하여 워크플로우 등록

### 새로운 MCP 도구 추가
1. MCP 서버 구현
2. 서버 설정 추가
3. MCPManager를 통해 서버 활성화

## 결론

LLM 모듈은 확장 가능하고 유연한 아키텍처를 통해 다양한 LLM 모델과 도구를 통합할 수 있는 프레임워크를 제공합니다. 핵심 컴포넌트인 LLMAgent, MCPToolManager, 워크플로우 시스템은 복잡한 LLM 작업을 효율적으로 처리할 수 있도록 설계되었습니다.