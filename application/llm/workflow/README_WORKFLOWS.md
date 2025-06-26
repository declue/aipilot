# 📚 DSPilot 워크플로우 가이드

DSPilot의 워크플로우는 각각 특화된 용도에 맞게 설계되어 다양한 사용자 요구를 충족합니다.

## 🎯 워크플로우 개요

| 워크플로우 | 특화 분야 | 적합한 상황 |
|-----------|----------|-----------|
| **AgentWorkflow** | 대화형 협업 | 복잡한 작업을 단계별로 사용자와 함께 진행 |
| **BasicChatWorkflow** | 단순 질의응답 | Cursor/Cline Ask 모드 스타일의 빠른 질문 답변 |
| **ResearchWorkflow** | 전문 리서치 | Perplexity 스타일의 웹검색 기반 심층 조사 |

## 🤖 AgentWorkflow - 대화형 AI 어시스턴트

### 📋 특징

- **Cursor 스타일**: 사용자와 단계별 상호작용
- **상태 유지**: 워크플로우 진행 상황 추적
- **유연성**: 사용자 피드백에 따른 계획 수정
- **투명성**: 각 단계마다 명확한 선택지 제공

### 🎯 사용 사례

```python
# 복잡한 코딩 작업
await agent_workflow.run(agent, "Python 웹 크롤러를 만들어주세요")

# 프로젝트 계획
await agent_workflow.run(agent, "새로운 앱 개발 계획을 세워주세요")

# 문제 해결
await agent_workflow.run(agent, "서버 성능 문제를 분석하고 해결해주세요")
```

### 💬 상호작용 예시

```
🤖 Agent: 다음 계획으로 진행하겠습니다:
1. 요구사항 분석
2. 라이브러리 선택
3. 코드 구현
4. 테스트 및 검증

어떻게 진행할까요?
1. **계획 승인** - 바로 실행
2. **계획 수정** - 일부 변경 후 실행
3. **더 자세히** - 계획을 더 구체화

👤 사용자: 1

🤖 Agent: 네, 승인된 계획으로 진행하겠습니다...
```

## 💬 BasicChatWorkflow - 단순 질의응답

### 📋 특징

- **빠른 응답**: 복잡한 도구 없이 즉시 답변
- **질문 유형 인식**: 코딩, 설명, 비교, 문제해결 등 자동 감지
- **최적화된 프롬프트**: 각 질문 유형에 맞는 응답 구조

### 🎯 사용 사례

```python
# 개념 설명
await basic_workflow.run(agent, "Python의 리스트와 튜플의 차이점은?")

# 코딩 도움
await basic_workflow.run(agent, "JavaScript에서 비동기 처리하는 방법")

# 문제 해결
await basic_workflow.run(agent, "pip install 시 에러가 발생해요")
```

### 🔧 질문 유형별 최적화

| 유형 | 키워드 예시 | 응답 스타일 |
|------|-----------|-----------|
| 코딩 도움 | 코드, 함수, 에러, Python | 실용적 해결책 + 코드 예시 |
| 개념 설명 | 설명, 뭐야, 차이, 어떻게 | 명확한 개념 + 구체적 예시 |
| 비교 분석 | 비교, vs, 차이점, 장단점 | 구조화된 비교표 |
| 문제 해결 | 문제, 오류, 안돼, 해결 | 단계별 해결 방법 |

## 🔍 ResearchWorkflow - 전문 리서치

### 📋 특징

- **Perplexity 스타일**: 실시간 웹검색 기반 전문 조사
- **다각도 접근**: 여러 관점에서 정보 수집
- **신뢰성 검증**: 정보 출처 및 신뢰도 평가
- **종합 보고서**: 구조화된 전문 리서치 결과

### 🎯 사용 사례

```python
# 기술 동향 조사
await research_workflow.run(agent, "2024년 AI 기술 동향")

# 시장 분석
await research_workflow.run(agent, "전기차 시장 현황과 전망")

# 경쟁사 분석
await research_workflow.run(agent, "ChatGPT vs Claude 비교 분석")
```

### 🔄 리서치 프로세스

1. **검색 쿼리 생성**: 다각도 관점의 전문 검색어 생성
2. **웹검색 실행**: 실시간 정보 수집
3. **심화 검색**: 부족한 영역 추가 조사
4. **정보 검증**: 신뢰성 및 정확성 평가
5. **종합 보고서**: Perplexity 스타일 전문 리포트

### 📊 보고서 구조

```markdown
# 리서치 주제

## 🔍 핵심 요약
- 주요 발견사항 요약

## 📊 주요 발견사항
1. 첫 번째 핵심 발견
2. 두 번째 핵심 발견
3. 세 번째 핵심 발견

## 🧭 심층 분석
- 데이터 연관성 분석
- 패턴과 트렌드

## 🔮 시사점 및 전망
- 현재 상황 의미
- 미래 전망

## ⚠️ 제한사항
- 정보의 한계점
- 추가 조사 필요 영역
```

## 🚀 워크플로우 선택 가이드

### 📝 질문별 추천 워크플로우

| 질문 유형 | 추천 워크플로우 | 이유 |
|----------|---------------|------|
| "Python 함수 작성법은?" | BasicChatWorkflow | 단순한 지식 질문 |
| "웹 크롤러를 만들어주세요" | AgentWorkflow | 복잡한 구현 작업 |
| "2024년 AI 동향은?" | ResearchWorkflow | 최신 정보 조사 필요 |
| "React vs Vue 비교" | BasicChatWorkflow | 일반적 비교 질문 |
| "블로그 사이트 개발해주세요" | AgentWorkflow | 단계적 프로젝트 진행 |
| "양자컴퓨팅 시장 현황" | ResearchWorkflow | 전문적 시장 조사 |

### 🎯 사용 팁

1. **간단한 질문**: BasicChatWorkflow로 빠른 답변
2. **복잡한 작업**: AgentWorkflow로 단계별 진행
3. **최신 정보**: ResearchWorkflow로 웹검색 기반 조사

## 🔧 개발자 가이드

### 워크플로우 사용

```python
from application.llm.workflow import get_workflow

# 워크플로우 선택
workflow = get_workflow("agent")()  # "basic", "research", "agent"

# 실행
result = await workflow.run(agent, "사용자 요청", streaming_callback)
```

### 커스텀 워크플로우 등록

```python
from application.llm.workflow import register_workflow

register_workflow("custom", CustomWorkflow)
```

---

이렇게 특화된 워크플로우들을 통해 다양한 사용자 요구에 최적화된 AI 어시스턴트 경험을 제공합니다. 🚀
