"""
기본 질의응답 워크플로우 (BasicChatWorkflow)
============================================

순수 LLM 기반의 빠르고 간결한 질의응답 워크플로우입니다.
외부 도구나 복잡한 처리 없이 LLM의 기본 지식만으로 응답을 생성합니다.

Cursor/Cline의 Ask 모드와 유사한 단순하고 직접적인 AI 대화 방식을 제공하며,
빠른 응답 속도와 간결한 상호작용이 특징입니다.

주요 특징
=========

1. **순수 LLM 응답**
   - 외부 도구 사용 없이 LLM 기본 지식만 활용
   - 빠른 응답 속도 보장
   - 네트워크나 도구 의존성 없음

2. **질문 유형별 최적화**
   - 프로그래밍, 설명, 비교, 문제해결 등 유형별 프롬프트 최적화
   - 각 질문 유형에 맞는 구조화된 응답 제공

3. **간결한 상호작용**
   - 복잡한 다단계 처리 없음
   - 직관적이고 예측 가능한 응답 패턴

사용 권장 상황
=============

### 적합한 사용 사례:
- 일반적인 지식 질문 및 정보 요청
- 프로그래밍 개념 설명 및 코드 도움
- 빠른 상담이나 조언이 필요한 경우
- 인터넷 연결이 불안정하거나 도구 사용이 제한된 환경
- 단순하고 직접적인 답변을 원하는 경우

### 부적합한 사용 사례:
- 실시간 정보가 필요한 경우 (날씨, 뉴스, 주식 등)
- 파일 읽기/쓰기나 외부 시스템 연동이 필요한 작업
- 복잡한 계산이나 데이터 처리 작업
- 웹 검색이나 최신 정보 조회가 필요한 경우

질문 유형별 최적화
================

### 1. 코딩/프로그래밍 (code_help)
**감지 키워드**: 코드, 프로그래밍, 함수, 에러, 버그, python, javascript 등
**최적화 내용**:
- 핵심 해결 방법 제시
- 간단한 코드 예시 포함
- 주의사항 및 팁 제공

### 2. 설명 요청 (explanation) 
**감지 키워드**: 설명, 뭐야, 무엇, what, explain, 차이, 어떻게, 왜 등
**최적화 내용**:
- 핵심 개념을 명확히 설명
- 구체적인 예시 포함
- 단계별 정리

### 3. 비교 요청 (comparison)
**감지 키워드**: 비교, compare, vs, 차이점, 장단점, 어느게 등
**최적화 내용**:
- 주요 차이점과 공통점
- 각각의 장단점
- 사용 상황별 권장사항

### 4. 문제 해결 (troubleshooting)
**감지 키워드**: 문제, 안돼, 오류, 에러, 해결, 고치, 작동 등
**최적화 내용**:
- 가능한 원인들
- 단계별 해결 방법
- 예방 방법

### 5. 일반 질문 (general)
**기본 처리**: 추가 프롬프트 최적화 없이 원본 메시지 그대로 전달

사용법 및 예시
=============

### 1. 기본 사용법

```python
from dspilot_core.llm.workflow import BasicChatWorkflow

# 워크플로우 초기화
workflow = BasicChatWorkflow()

# 실행
result = await workflow.run(agent, "Python에서 리스트와 튜플의 차이점은?", streaming_callback)
```

### 2. 에이전트에서 사용

```python
class ProblemAgent(BaseAgent):
    def _get_workflow_name(self, mode: str) -> str:
        if mode == "basic":
            return "basic"  # BasicChatWorkflow 사용
        # ... 다른 모드들
```

### 3. 스트리밍과 함께 사용

```python
def chat_callback(content: str):
    print(f"💬 {content}", end="", flush=True)

result = await workflow.run(
    agent=my_agent,
    message="FastAPI와 Flask의 차이점을 설명해주세요",
    streaming_callback=chat_callback
)
```

내부 동작 원리
=============

### 처리 흐름
1. **질문 유형 감지**: 키워드 기반으로 질문 유형 분류
2. **프롬프트 최적화**: 유형별 최적화된 프롬프트 생성
3. **LLM 응답 생성**: agent._generate_basic_response() 호출
4. **결과 반환**: 생성된 응답을 그대로 반환

### 질문 유형 감지 알고리즘
```python
def _detect_question_type(self, message: str) -> str:
    message_lower = message.lower()
    
    # 키워드 기반 매칭
    if any(keyword in message_lower for keyword in code_keywords):
        return "code_help"
    elif any(keyword in message_lower for keyword in explain_keywords):
        return "explanation"
    # ... 기타 유형들
    else:
        return "general"
```

성능 특성
=========

### 장점
- **빠른 응답**: 외부 도구 호출 없이 즉시 응답
- **안정성**: 네트워크나 외부 의존성 없음  
- **예측 가능**: 일관된 응답 패턴
- **리소스 효율**: 최소한의 시스템 리소스 사용

### 제한사항
- **정보 한계**: LLM 훈련 데이터 기준 시점의 정보만 활용
- **실시간성 부족**: 최신 정보나 실시간 데이터 접근 불가
- **도구 연동 불가**: 파일 시스템, 웹 API 등 외부 리소스 사용 불가
- **복잡한 계산 한계**: 정확한 수치 계산이나 데이터 처리에 한계

최적화 팁
=========

### 효과적인 질문 방법
1. **구체적인 질문**: "Python 리스트 정렬 방법" vs "Python 도움말"
2. **컨텍스트 제공**: "웹 개발 초보자를 위한 JavaScript 설명"
3. **명확한 목적**: "면접 준비용 알고리즘 설명"

### 응답 품질 향상
- 질문 유형에 맞는 키워드 사용
- 단계별 설명이 필요한 경우 명시적으로 요청
- 예시가 필요한 경우 "예시와 함께" 명시

문제 해결
=========

### 응답이 부정확한 경우
- 더 구체적이고 명확한 질문으로 재시도
- 질문을 여러 개의 작은 질문으로 분할
- 필요한 컨텍스트나 배경 정보 추가 제공

### 응답이 너무 간단한 경우
- "자세히 설명해주세요" 추가
- "단계별로 설명해주세요" 요청
- "예시와 함께 설명해주세요" 명시

### 에러 발생 시
- 에이전트의 _generate_basic_response 메서드 확인
- 로그에서 구체적인 오류 메시지 확인
- 네트워크 연결 및 LLM 서비스 상태 점검
"""

import logging
from typing import Any, Callable, Optional

from dspilot_core.llm.workflow.base_workflow import BaseWorkflow
from dspilot_core.util.logger import setup_logger

logger = setup_logger("basic_chat_workflow") or logging.getLogger("basic_chat_workflow")


class BasicChatWorkflow(BaseWorkflow):
    """
    기본 질의응답 워크플로우
    
    순수 LLM 기반의 빠르고 간결한 질의응답을 제공합니다.
    외부 도구 사용 없이 LLM의 기본 지식만으로 응답을 생성하며,
    질문 유형별로 최적화된 프롬프트를 사용합니다.
    
    Cursor/Cline의 Ask 모드와 유사한 단순하고 직접적인 AI 대화 방식으로,
    빠른 응답 속도와 간결한 상호작용이 특징입니다.
    
    주요 특징:
    - 순수 LLM 응답 (외부 도구 사용 없음)
    - 질문 유형별 프롬프트 최적화
    - 빠른 응답 속도
    - 안정적이고 예측 가능한 동작
    """

    async def run(
        self, agent: Any, message: str, streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        기본 질의응답 워크플로우 실행

        사용자 질문을 분석하여 유형별로 최적화된 프롬프트를 생성하고,
        순수 LLM 기반으로 응답을 생성합니다.

        Args:
            agent: LLM 에이전트 (BaseAgent 인스턴스)
            message: 사용자 질문
            streaming_callback: 스트리밍 콜백 함수 (선택사항)

        Returns:
            str: AI 생성 응답

        Raises:
            Exception: 에이전트 설정 문제나 LLM 서비스 오류 시
        """
        try:
            logger.info(f"기본 질의응답 시작: {message[:50]}...")

            if streaming_callback:
                streaming_callback("💬 ")

            # 질문 유형에 따른 최적화된 프롬프트 생성
            optimized_prompt = self._optimize_prompt(message)

            # 순수 LLM 기반 응답 생성 (도구 사용 없음)
            if hasattr(agent, "_generate_basic_response"):
                result = await agent._generate_basic_response(optimized_prompt, streaming_callback)
                logger.info("기본 질의응답 완료")
                return result
            else:
                logger.error("에이전트에 기본 응답 생성 기능이 없습니다")
                return "에이전트 설정에 문제가 있습니다. _generate_basic_response 메서드가 필요합니다."

        except Exception as e:
            logger.error(f"기본 질의응답 실행 중 오류: {e}")
            return f"워크플로우 실행 중 오류가 발생했습니다: {str(e)}"

    def _optimize_prompt(self, user_message: str) -> str:
        """
        사용자 질문을 분석하여 최적화된 프롬프트 생성
        
        질문 유형을 감지하고 각 유형에 맞는 구조화된 프롬프트를 생성하여
        더 정확하고 유용한 응답을 얻을 수 있도록 합니다.
        
        Args:
            user_message: 원본 사용자 질문
            
        Returns:
            str: 최적화된 프롬프트 (또는 원본 메시지)
        """
        
        # 질문 유형 감지
        question_type = self._detect_question_type(user_message)
        
        # 유형별 최적화된 프롬프트 생성
        if question_type == "code_help":
            return f"""다음 프로그래밍 관련 질문에 대해 명확하고 실용적인 답변을 제공해주세요:

질문: {user_message}

답변 시 다음을 포함해주세요:
- 핵심 해결 방법
- 간단한 코드 예시 (필요시)
- 주의사항이나 팁

간결하고 실용적인 답변을 제공해주세요."""

        elif question_type == "explanation":
            return f"""다음 질문에 대해 이해하기 쉽게 설명해주세요:

질문: {user_message}

답변 시:
- 핵심 개념을 명확히 설명
- 구체적인 예시 포함
- 단계별로 정리하여 설명

명확하고 이해하기 쉬운 설명을 제공해주세요."""

        elif question_type == "comparison":
            return f"""다음 비교 요청에 대해 객관적이고 구조화된 답변을 제공해주세요:

질문: {user_message}

답변 시:
- 주요 차이점과 공통점
- 각각의 장단점
- 사용 상황별 권장사항

균형 잡힌 비교 분석을 제공해주세요."""

        elif question_type == "troubleshooting":
            return f"""다음 문제 해결 요청에 대해 단계별 해결 방법을 제공해주세요:

문제: {user_message}

답변 시:
- 가능한 원인들
- 단계별 해결 방법
- 예방 방법

실용적이고 따라하기 쉬운 해결책을 제공해주세요."""

        else:  # 일반 질문 – 원본 메시지 그대로 반환
            return user_message

    def _detect_question_type(self, message: str) -> str:
        """
        질문 유형 감지
        
        키워드 기반으로 질문을 분류하여 적절한 프롬프트 최적화 전략을 선택합니다.
        
        Args:
            message: 사용자 질문 메시지
            
        Returns:
            str: 질문 유형 ("code_help", "explanation", "comparison", "troubleshooting", "general")
        """
        message_lower = message.lower()
        
        # 코딩/프로그래밍 관련 키워드
        code_keywords = [
            '코드', 'code', '프로그래밍', 'programming', '함수', 'function', 
            '에러', 'error', '버그', 'bug', '구현', 'implement', 'python', 
            'javascript', 'java', 'c++', 'sql', 'html', 'css', '알고리즘',
            'algorithm', '라이브러리', 'library', '프레임워크', 'framework'
        ]
        if any(keyword in message_lower for keyword in code_keywords):
            return "code_help"
        
        # 설명 요청 키워드
        explain_keywords = [
            '설명', '뭐야', '무엇', 'what', 'explain', '차이', 'difference',
            '어떻게', 'how', '왜', 'why', '의미', 'meaning', '개념', 'concept',
            '정의', 'definition', '원리', 'principle'
        ]
        if any(keyword in message_lower for keyword in explain_keywords):
            return "explanation"
        
        # 비교 요청 키워드
        compare_keywords = [
            '비교', 'compare', 'vs', '대', '차이점', '장단점', '어느게',
            '어떤게', 'which', 'better', '좋은', '추천', 'recommend'
        ]
        if any(keyword in message_lower for keyword in compare_keywords):
            return "comparison"
        
        # 문제 해결 키워드
        trouble_keywords = [
            '문제', 'problem', '안돼', '안되', '오류', '에러', 'error',
            '해결', 'solve', '고치', 'fix', '작동', '실행', 'run',
            '도움', 'help', '트러블', 'trouble', '이슈', 'issue'
        ]
        if any(keyword in message_lower for keyword in trouble_keywords):
            return "troubleshooting"
        
        return "general"
