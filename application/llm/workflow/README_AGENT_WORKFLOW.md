# Agent Workflow

Cursor와 같은 AI agent 도구들의 워크플로우를 모방한 **단계별 Interactive Workflow**입니다.

사용자 피드백을 받으면서 단계적으로 작업을 진행하며, 각 단계에서 명확한 선택지를 제공합니다.

## 🚀 특징

### 1. 단계별 Interactive 진행

- **분석 → 컨텍스트 수집 → 계획 → 실행 → 검토 → 다음 단계** 순으로 진행
- 각 단계에서 사용자의 피드백과 승인을 받음
- 명확한 선택지 제공으로 사용자 친화적

### 2. 상태 관리

- 워크플로우 상태 유지 및 추적
- 사용자 피드백 누적 저장
- 실행 결과 및 컨텍스트 정보 관리

### 3. 유연한 진행 방식

- 계획 수정/승인 시스템
- 추가 작업 및 개선 지원
- 단계별 또는 전체 승인 방식 선택 가능

## 📋 워크플로우 단계

### 1. Initial Analysis (초기 분석)

- 사용자 요청 분석
- 요청 유형, 복잡도, 필요 도구 파악
- 잠재적 위험 요소 식별

### 2. Context Gathering (컨텍스트 수집)

- 관련 파일 및 정보 수집
- 프로젝트 구조 파악
- 외부 정보 검색 (필요시)

### 3. Planning (계획 수립)

- 상세한 실행 계획 작성
- 단계별 분해 및 도구 선정
- 위험 요소 및 대응 방안 수립

### 4. Execution (실행)

- 계획된 작업 실행
- MCP 도구 활용
- 실시간 결과 보고

### 5. Review (검토)

- 실행 결과 품질 평가
- 목표 달성도 확인
- 개선 필요 사항 식별

### 6. Next Steps (다음 단계)

- 추가 작업 제안
- 새로운 요청 처리
- 워크플로우 완료 또는 계속

## 🎯 사용법

### 기본 사용

```python
from application.llm.workflow.agent_workflow import AgentWorkflow

# 워크플로우 인스턴스 생성
workflow = AgentWorkflow()

# 첫 번째 실행 (초기화)
result1 = await workflow.run(agent, "hello.py를 작성해줘", streaming_callback)
print(result1)  # 분석 결과 + 다음 단계 선택지

# 두 번째 실행 (사용자 피드백 반영)
result2 = await workflow.run(agent, "승인", streaming_callback)
print(result2)  # 컨텍스트 수집 결과

# 계속해서 사용자 피드백을 받으며 진행...
```

### 사용자 선택지 예시

#### 계획 단계에서

- **"1"** 또는 **"승인"**: 계획 승인하고 실행 단계로
- **"2"** 또는 **"수정"**: 계획 수정 요청
- **"단계별로 진행해주세요"**: 각 단계마다 확인

#### 검토 단계에서

- **"1"** 또는 **"완료"**: 결과 수락하고 워크플로우 완료
- **"2"** 또는 **"추가 작업"**: 개선 또는 보완 작업 요청
- **"3"** 또는 **"새로운 요청"**: 완전히 새로운 작업 시작

## 🔧 고급 사용법

### 상태 확인

```python
# 현재 워크플로우 상태 확인
if workflow.state:
    print(f"현재 단계: {workflow.state.stage}")
    print(f"반복 횟수: {workflow.iteration_count}")
    print(f"피드백 수: {len(workflow.state.user_feedback)}")
```

### 사용자 의도 감지

```python
# 사용자 입력 의도 분석
user_input = "추가로 테스트 코드도 작성해주세요"

if workflow._is_plan_approved(user_input):
    print("계획 승인됨")
elif workflow._should_do_additional_work(user_input):
    print("추가 작업 요청됨")
elif workflow._should_complete_workflow(user_input):
    print("워크플로우 완료 요청됨")
```

### 커스텀 스트리밍 콜백

```python
def my_streaming_callback(text: str):
    """실시간 진행 상황 표시"""
    print(f"[STREAM] {text}", end="")

result = await workflow.run(agent, "요청", my_streaming_callback)
```

## 📝 실제 사용 예시

### 파일 생성 요청

```
👤 사용자: "hello.py를 작성해줘. 간단한 덧셈 프로그램이야"

🤖 Agent Workflow:
🔍 1단계: 요청 분석
- 요청 유형: 파일 생성 및 프로그래밍
- 복잡도: 단순
- 필요 도구: write_file, read_file

📚 2단계: 컨텍스트 수집
- 프로젝트 구조 확인
- 기존 파일 존재 여부 확인

📋 3단계: 실행 계획 수립
### 계획 승인 및 진행 방식 선택
1. **계획 승인** - 제시된 계획으로 바로 실행 시작
2. **계획 수정** - 일부 단계나 접근 방식 변경 요청
...

👤 사용자: "1"

⚙️ 4단계: 계획 실행
- hello.py 파일 생성
- 덧셈 프로그램 구현
- 테스트 실행

🔍 5단계: 결과 검토
### 다음 단계 선택
1. **결과 수락** - 현재 결과로 워크플로우 완료
2. **추가 작업** - 미흡한 부분 보완
...

👤 사용자: "2 - 단위 테스트도 추가해주세요"

🔧 추가 작업: 단위 테스트 추가
...
```

## 🎨 주요 메서드

### 워크플로우 제어

| 메서드 | 설명 |
|--------|------|
| `run(agent, message, streaming_callback)` | 워크플로우 실행 (메인 진입점) |
| `_initialize_workflow()` | 새 워크플로우 초기화 |
| `_continue_workflow()` | 기존 워크플로우 계속 |

### 단계 처리

| 메서드 | 설명 |
|--------|------|
| `_handle_initial_analysis()` | 초기 요청 분석 |
| `_handle_context_gathering()` | 컨텍스트 수집 |
| `_handle_planning()` | 실행 계획 수립 |
| `_handle_execution()` | 계획 실행 |
| `_handle_review()` | 결과 검토 |
| `_handle_next_steps()` | 다음 단계 처리 |

### 사용자 의도 분석

| 메서드 | 설명 |
|--------|------|
| `_is_plan_approved()` | 계획 승인 여부 |
| `_should_complete_workflow()` | 워크플로우 완료 여부 |
| `_should_do_additional_work()` | 추가 작업 필요 여부 |
| `_should_start_new_request()` | 새 요청 시작 여부 |

## 🔄 상태 클래스

### WorkflowState

```python
@dataclass
class WorkflowState:
    stage: WorkflowStage           # 현재 단계
    original_request: str          # 원래 요청
    context: Dict[str, Any]        # 컨텍스트 정보
    current_plan: Optional[Dict]   # 현재 계획
    execution_results: List[Dict]  # 실행 결과들
    user_feedback: List[str]       # 사용자 피드백들
```

### WorkflowStage

```python
class WorkflowStage(Enum):
    INITIAL_ANALYSIS = "initial_analysis"
    CONTEXT_GATHERING = "context_gathering" 
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"
    NEXT_STEPS = "next_steps"
    COMPLETED = "completed"
```

## 🧪 테스트

```bash
# 단위 테스트 실행
python -m pytest tests/application/llm/workflow/test_agent_workflow.py -v

# 데모 실행
PYTHONPATH=. python examples/agent_workflow_demo.py
```

## 🔗 Workflow 등록

`workflow_utils.py`에 등록되어 있어 다음과 같이 사용 가능:

```python
from application.llm.workflow.workflow_utils import get_workflow

# 워크플로우 클래스 가져오기
AgentWorkflow = get_workflow("agent")

# 인스턴스 생성
workflow = AgentWorkflow()
```

## 💡 사용 팁

### 1. 적절한 피드백 제공

- 명확하고 구체적인 요청 작성
- 번호 선택 또는 자유 텍스트 모두 가능
- 단계별로 세밀한 조정 가능

### 2. 상태 활용

- 워크플로우 상태를 활용한 진행 상황 파악
- 중간 결과를 바탕으로 한 의사 결정

### 3. 오류 처리

- 각 단계에서 적절한 오류 처리
- 실패 시 재시도 또는 대안 제시

## 🎯 vs 다른 워크플로우

### vs BasicChatWorkflow  

- **BasicChatWorkflow**: 단순 질의응답, Cursor/Cline Ask 모드 스타일
- **AgentWorkflow**: 복잡한 작업의 체계적이고 대화형 진행

### vs ResearchWorkflow

- **ResearchWorkflow**: Perplexity 스타일 전문 웹검색 및 리서치
- **AgentWorkflow**: 범용적 대화형 작업 처리

### 사용 시나리오

- **간단한 질문/설명**: BasicChatWorkflow
- **전문적인 조사/리서치**: ResearchWorkflow  
- **복잡한 대화형 협업**: **AgentWorkflow** ⭐

---

**Agent Workflow**는 사용자와 AI가 협력하여 복잡한 작업을 단계별로 진행할 수 있는 강력하고 유연한 워크플로우입니다.
