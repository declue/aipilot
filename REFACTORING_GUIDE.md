# DSPilot CLI 리팩토링 가이드

## 개요

DSPilot CLI와 LLM 코드를 SOLID 원칙에 맞게 리팩토링하여 범용 Claude Code 스타일의 에이전트로 개선했습니다.

## 주요 개선사항

### 1. 프롬프트 관리 시스템 개선

#### 기존 문제점

- `constants.py`에 프롬프트가 하드코딩되어 있음
- 프롬프트 수정 시 코드 변경 필요
- 커스터마이징이 어려움

#### 개선 내용

- 파일 기반 프롬프트 관리 시스템 구축
- `dspilot_core/instructions/` 폴더에 프롬프트 파일 관리
- `PromptManager` 클래스로 동적 로드 지원

```python
# 기존 방식 (하드코딩)
ANALYSIS_PROMPT_TEMPLATE = """다음 사용자 요청을 분석하여..."""

# 새로운 방식 (파일 기반)
from dspilot_core.instructions import get_prompt

prompt = get_prompt("analysis_prompts", user_message="질문", tools_desc="도구목록")
```

#### 새로운 프롬프트 파일들

- `analysis_prompts.txt`: 요청 분석 프롬프트
- `final_analysis_prompts.txt`: 최종 분석 프롬프트  
- `enhanced_prompts.txt`: 향상된 대화 프롬프트
- `default_agent_instructions.txt`: 기본 에이전트 지시사항
- `openai_agent_instructions.txt`: OpenAI 전용 지시사항

### 2. SOLID 원칙 적용

#### Single Responsibility Principle (SRP)

- **OutputManager**: 출력 관리만 담당
- **ConversationManager**: 대화 히스토리 관리만 담당
- **ExecutionManager**: 실행 계획 수립 및 관리만 담당
- **PromptManager**: 프롬프트 로드 및 관리만 담당

#### Open/Closed Principle (OCP)

- 새로운 프롬프트 타입 추가 시 기존 코드 수정 없이 확장 가능
- 새로운 워크플로우 추가 시 ProblemAgent 수정 없이 확장 가능

#### Dependency Inversion Principle (DIP)

- 구체적 구현 대신 인터페이스에 의존
- 프롬프트 관리자를 의존성 주입으로 사용

### 3. ProblemAgent 개선

#### 범용 에이전트 설계

```python
class ProblemAgent(BaseAgent):
    """
    범용 통합 Agent - Cursor/Claude Code 스타일의 에이전트 구현
    
    특징:
    - 범용적이고 확장 가능한 설계
    - 특정 MCP 도구에 의존하지 않는 구조
    - 다양한 워크플로우를 지원하는 플러그인 시스템
    """
```

#### 주요 개선사항

- 워크플로우 캐싱으로 성능 개선
- 상호작용 모드 지원
- 확장 가능한 워크플로우 매핑 시스템

### 4. 중복 로직 제거

#### 설정 관리 통합

- 중복된 설정 로드/저장 로직 제거
- 공통 검증 로직 통합

#### 공통 유틸리티 함수 정리

- 중복된 오류 처리 로직 통합
- 공통 출력 포맷팅 함수 활용

## 사용법

### 기본 사용법 (변경 없음)

```bash
# 대화형 모드
python -m dspilot_cli

# 단일 질문 모드
python -m dspilot_cli "질문"

# 자동 모드
python -m dspilot_cli "질문" --full-auto
```

### 프롬프트 커스터마이징

#### 1. 기존 프롬프트 수정

```bash
# dspilot_core/instructions/analysis_prompts.txt 파일 수정
vi dspilot_core/instructions/analysis_prompts.txt
```

#### 2. 새로운 프롬프트 추가

```python
from dspilot_core.instructions import PromptManager

manager = PromptManager()
manager.add_custom_prompt("my_prompt", "커스텀 프롬프트: {input}")
```

#### 3. 프로그래밍 방식으로 프롬프트 사용

```python
from dspilot_core.instructions import get_prompt

# 기본 프롬프트 로드
prompt = get_prompt("analysis_prompts", 
                   user_message="사용자 질문",
                   tools_desc="도구 목록")
```

### 새로운 워크플로우 추가

#### 1. 워크플로우 클래스 생성

```python
class MyCustomWorkflow:
    def __init__(self, llm_service, mcp_tool_manager):
        self.llm_service = llm_service
        self.mcp_tool_manager = mcp_tool_manager
    
    async def run(self, agent, user_message, streaming_callback=None):
        # 커스텀 워크플로우 로직
        pass
```

#### 2. UnifiedAgent에 워크플로우 등록

```python
# problem_agent.py의 _mode_to_workflow 딕셔너리에 추가
self._mode_to_workflow = {
    "basic": "basic_chat",
    "mcp_tools": "agent",
    "custom": "my_custom_workflow"  # 새로운 워크플로우 추가
}
```

## 테스트

### 테스트 실행

```bash
# 전체 테스트
pytest tests/application/cli/test_refactored_cli.py

# 특정 테스트
pytest tests/application/cli/test_refactored_cli.py::TestPromptManager
```

### 수동 테스트

```bash
# 프롬프트 관리자 테스트
python tests/application/cli/test_refactored_cli.py
```

## 마이그레이션 가이드

### 기존 코드에서 새로운 구조로 이전

#### 1. 하드코딩된 프롬프트 교체

```python
# 기존
from dspilot_cli.constants import ANALYSIS_PROMPT_TEMPLATE
prompt = ANALYSIS_PROMPT_TEMPLATE.format(user_message=msg)

# 새로운 방식
from dspilot_core.instructions import get_prompt
prompt = get_prompt("analysis_prompts", user_message=msg)
```

#### 2. 매니저 클래스 의존성 주입

```python
# 기존
class MyClass:
    def __init__(self):
        self.output_manager = OutputManager()

# 새로운 방식
class MyClass:
    def __init__(self, output_manager: OutputManager):
        self.output_manager = output_manager
```

## 확장성

### 새로운 프롬프트 타입 추가

1. `dspilot_core/instructions/`에 `.txt` 파일 생성
2. `PromptNames` 클래스에 상수 추가
3. 필요한 곳에서 `get_prompt()` 사용

### 새로운 매니저 추가

1. SOLID 원칙을 따라 단일 책임 클래스 생성
2. 의존성 주입 패턴 사용
3. 적절한 인터페이스 정의

### 새로운 에이전트 워크플로우 추가

1. 워크플로우 클래스 구현
2. `workflow_utils.py`에 등록
3. `ProblemAgent`의 매핑에 추가

## 성능 개선

### 캐싱 시스템

- 프롬프트 캐싱으로 파일 I/O 최소화
- 워크플로우 캐싱으로 초기화 비용 절약

### 지연 로딩

- 필요한 시점에만 컴포넌트 초기화
- 메모리 사용량 최적화

## 보안 고려사항

### 프롬프트 보안

- 프롬프트 파일 권한 관리
- 사용자 입력 검증 강화

### 의존성 주입 보안

- 인터페이스 기반 검증
- 타입 안정성 확보

## 향후 개선 계획

1. **더 많은 프롬프트 템플릿**: 다양한 시나리오별 프롬프트 추가
2. **프롬프트 버전 관리**: Git 기반 프롬프트 버전 관리 시스템
3. **동적 워크플로우 로딩**: 런타임에 워크플로우 추가/제거
4. **성능 모니터링**: 각 컴포넌트별 성능 메트릭 수집
5. **플러그인 시스템**: 서드파티 확장 지원

## 결론

이번 리팩토링을 통해 DSPilot CLI는 다음과 같은 이점을 얻었습니다:

1. **유지보수성 향상**: SOLID 원칙으로 코드 구조 개선
2. **확장성 증대**: 새로운 기능 추가가 용이한 구조
3. **재사용성 강화**: 각 컴포넌트의 독립성 확보
4. **커스터마이징 용이**: 파일 기반 프롬프트 관리
5. **범용성 확보**: 특정 도구에 의존하지 않는 구조

이러한 개선으로 DSPilot은 진정한 범용 AI 에이전트 도구로 발전할 수 있는 기반을 마련했습니다.
