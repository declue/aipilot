"""
Agent Workflow 사용 예제
Cursor 스타일의 Interactive Workflow 데모
"""

import asyncio
import logging
from unittest.mock import MagicMock

from application.llm.workflow.agent_workflow import AgentWorkflow, WorkflowStage


class MockAgent:
    """테스트용 Mock Agent"""
    
    def __init__(self):
        self.mcp_tool_manager = MagicMock()
        
    async def _generate_basic_response(self, prompt: str, streaming_callback=None) -> str:
        """기본 응답 생성 시뮬레이션"""
        if streaming_callback:
            streaming_callback("생각 중...\n")
        
        # 프롬프트에 따른 다른 응답들
        if "분석" in prompt:
            return """
**요청 유형**: 파일 생성 및 프로그래밍
**복잡도**: 단순
**필요한 도구들**: write_file, read_file
**컨텍스트 필요성**: 기존 프로젝트 구조 확인 필요
**예상 단계 수**: 3-4단계
**잠재적 위험 요소**: 기존 파일 덮어쓰기 가능성
"""
        
        elif "컨텍스트" in prompt:
            return """
**프로젝트 구조 분석**:
- dspilot/ 디렉토리 확인
- Python 프로젝트임을 확인
- 기존 hello.py 파일 존재 확인

**관련 파일들**:
- pyproject.toml: 프로젝트 설정
- requirements.txt: 의존성 관리

**코딩 스타일**:
- Python 3.8+ 사용
- Black 포맷터 적용
- Type hints 사용 권장
"""
        
        elif "계획" in prompt:
            return """
# 실행 계획

## 1단계: 기존 파일 확인
- hello.py 파일 존재 여부 확인
- 기존 내용 백업 (필요시)

## 2단계: 새로운 hello.py 작성
- 간단한 덧셈 프로그램 구현
- 사용자 입력 받는 기능 추가
- 결과 출력 및 검증

## 3단계: 테스트 및 검증
- 프로그램 실행 테스트
- 다양한 입력값으로 검증
- 오류 처리 확인

## 4단계: 최종 확인
- 코드 품질 검토
- 문서화 추가 (필요시)
"""
        
        elif "실행" in prompt:
            return """
**1단계 완료**: 기존 hello.py 파일 확인
- 기존 파일 발견: 간단한 덧셈 코드
- 백업 생성: hello.py.bak

**2단계 완료**: 새로운 hello.py 작성
```python
def main():
    print("간단한 덧셈 계산기")
    try:
        num1 = float(input("첫 번째 숫자: "))
        num2 = float(input("두 번째 숫자: "))
        result = num1 + num2
        print(f"{num1} + {num2} = {result}")
    except ValueError:
        print("올바른 숫자를 입력해주세요.")

if __name__ == "__main__":
    main()
```

**3단계 완료**: 테스트 실행
- 정수 입력 테스트: 10 + 20 = 30 ✅
- 실수 입력 테스트: 1.5 + 2.5 = 4.0 ✅
- 잘못된 입력 테스트: 오류 메시지 출력 ✅

**4단계 완료**: 최종 검토
- 코드 스타일 확인 ✅
- 예외 처리 적절 ✅
- 사용자 친화적 인터페이스 ✅
"""
        
        elif "검토" in prompt:
            return """
**목표 달성도**: ⭐⭐⭐⭐⭐ (5/5)
- 요청된 간단한 덧셈 프로그램 완벽 구현
- 사용자 입력 기능 추가로 더 실용적

**품질 평가**: ⭐⭐⭐⭐⭐ (5/5)
- 깨끗하고 이해하기 쉬운 코드
- 적절한 예외 처리
- 사용자 친화적 인터페이스

**개선 필요 사항**:
- 추가 연산 기능 (뺄셈, 곱셈, 나눗셈)
- 계산 히스토리 저장
- GUI 인터페이스 고려

**추가 작업 제안**:
- calculator.py로 확장된 계산기 구현
- 단위 테스트 코드 작성
- 사용법 문서 작성
"""
        
        else:
            return f"Mock 응답: {prompt[:100]}..."
    
    async def generate_response(self, prompt: str, streaming_callback=None) -> dict:
        """도구를 사용한 응답 생성 시뮬레이션"""
        response = await self._generate_basic_response(prompt, streaming_callback)
        
        # 도구 사용 시뮬레이션
        used_tools = []
        if "파일" in prompt or "write" in prompt:
            used_tools.append("write_file")
        if "읽기" in prompt or "read" in prompt:
            used_tools.append("read_file")
        if "검색" in prompt:
            used_tools.append("web_search")
            
        return {
            "response": response,
            "used_tools": used_tools
        }


async def demo_interactive_workflow():
    """Interactive Agent Workflow 데모"""
    
    print("🚀 Agent Workflow Demo 시작")
    print("=" * 50)
    
    # Mock Agent 생성
    agent = MockAgent()
    
    # Agent Workflow 인스턴스 생성
    workflow = AgentWorkflow()
    
    # 시나리오: hello.py 파일 작성 요청
    initial_request = "hello.py를 작성해줘. 간단한 덧셈 프로그램이야"
    
    print(f"📝 초기 요청: {initial_request}")
    print("-" * 50)
    
    # 1단계: 워크플로우 시작 (분석 + 컨텍스트 수집 + 계획)
    result1 = await workflow.run(agent, initial_request)
    print("🔍 1단계 결과:")
    print(result1)
    print("\n" + "=" * 50)
    
    # 2단계: 계획 승인
    approval = "1"  # 계획 승인
    print(f"👤 사용자 입력: {approval}")
    print("-" * 50)
    
    result2 = await workflow.run(agent, approval)
    print("⚙️ 2단계 결과:")
    print(result2)
    print("\n" + "=" * 50)
    
    # 3단계: 검토 완료 - 추가 작업 요청
    additional_work = "2"  # 추가 작업
    print(f"👤 사용자 입력: {additional_work}")
    print("💬 추가 요청: 단위 테스트도 추가해주세요")
    print("-" * 50)
    
    result3 = await workflow.run(agent, "단위 테스트도 추가해주세요")
    print("🔧 3단계 결과:")
    print(result3)
    print("\n" + "=" * 50)
    
    # 4단계: 최종 완료
    completion = "1"  # 결과 수락
    print(f"👤 사용자 입력: {completion}")
    print("-" * 50)
    
    result4 = await workflow.run(agent, completion)
    print("🎉 4단계 결과:")
    print(result4)
    print("\n" + "=" * 50)
    
    print("✅ Demo 완료!")


async def demo_workflow_features():
    """워크플로우 주요 기능 데모"""
    
    print("\n🎯 Agent Workflow 주요 기능들")
    print("=" * 50)
    
    workflow = AgentWorkflow()
    
    # 1. 단계별 진행 상태 확인
    print("1. 워크플로우 단계들:")
    for stage in WorkflowStage:
        print(f"   - {stage.value}")
    
    # 2. 키워드 감지 기능 테스트
    print("\n2. 사용자 의도 감지:")
    test_inputs = [
        ("승인", "계획 승인"),
        ("1", "계획 승인"),
        ("수정해주세요", "계획 수정"),
        ("완료", "워크플로우 완료"),
        ("추가 작업", "추가 작업"),
        ("새로운 요청", "새 요청")
    ]
    
    for input_text, expected in test_inputs:
        approval = workflow._is_plan_approved(input_text)
        completion = workflow._should_complete_workflow(input_text)
        additional = workflow._should_do_additional_work(input_text)
        new_request = workflow._should_start_new_request(input_text)
        
        detected = []
        if approval:
            detected.append("계획승인")
        if completion:
            detected.append("완료")
        if additional:
            detected.append("추가작업")
        if new_request:
            detected.append("새요청")
            
        print(f"   '{input_text}' → {detected if detected else ['인식안됨']}")
    
    print("\n3. 상태 관리:")
    print("   - 워크플로우 상태 유지")
    print("   - 사용자 피드백 누적")
    print("   - 실행 결과 추적")
    print("   - 컨텍스트 정보 관리")
    
    print("\n4. Interactive 특징:")
    print("   - 단계별 사용자 확인")
    print("   - 명확한 선택지 제공")
    print("   - 계획 수정/승인 시스템")
    print("   - 추가 작업 및 개선 지원")


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    print("🎬 Agent Workflow 데모 프로그램")
    print("Cursor 스타일 Interactive AI Agent Workflow")
    print()
    
    # 메인 데모 실행
    asyncio.run(demo_interactive_workflow())
    
    # 기능 데모 실행
    asyncio.run(demo_workflow_features()) 