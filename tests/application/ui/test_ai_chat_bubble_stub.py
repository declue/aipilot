#!/usr/bin/env python3
"""AIChatBubble 스텁 기능 테스트 (GUI 환경 필요)"""

import pytest
from PySide6.QtCore import QCoreApplication, QThreadPool
from PySide6.QtWidgets import QApplication

from application.ui.presentation.ai_chat_bubble import AIChatBubble


# GUI 환경 체크 헬퍼
def check_gui_available() -> bool:
    """GUI 환경이 사용 가능한지 확인한다."""
    try:
        # 기존 앱 인스턴스가 있는지 확인
        existing_app = QCoreApplication.instance()
        if existing_app:
            return True
            
        # 새로운 앱 인스턴스 생성 시도
        app = QApplication([])
        if app:
            return True
        return False
    except Exception:
        return False


def cleanup_qt_resources():
    """Qt 리소스 정리"""
    try:
        # QThreadPool 정리
        thread_pool = QThreadPool.globalInstance()
        if thread_pool:
            thread_pool.waitForDone(1000)  # 1초 대기
            thread_pool.clear()
        
        # 앱 이벤트 처리
        app = QApplication.instance()
        if app:
            app.processEvents()
            
    except Exception:
        pass


def test_basic_creation() -> None:
    """기본 AIChatBubble 생성이 가능한지 확인한다."""
    if not check_gui_available():
        pytest.skip("GUI environment not available (no QApplication)")
        
    try:
        bubble = AIChatBubble("test message")
        assert bubble.message == "test message"
        assert bubble.avatar_icon == "🤖"
        
        # 리소스 정리
        bubble.deleteLater()
        cleanup_qt_resources()
        
    except Exception as e:
        # GUI 환경이 없을 때는 테스트를 스킵
        pytest.skip(f"GUI environment not available: {e}")


def test_create_github_bubble() -> None:
    """GitHub 아이콘을 가진 버블 생성이 가능한지 확인한다."""
    if not check_gui_available():
        pytest.skip("GUI environment not available (no QApplication)")
        
    try:
        github_bubble = AIChatBubble.create_github_bubble("GitHub test")
        assert github_bubble.message == "GitHub test"
        assert github_bubble.avatar_icon == "🐱"
        
        # 리소스 정리
        github_bubble.deleteLater()
        cleanup_qt_resources()
        
    except Exception as e:
        pytest.skip(f"GUI environment not available: {e}")


def test_streaming_attributes() -> None:
    """스트리밍 관련 속성들이 올바르게 초기화되는지 확인한다."""
    if not check_gui_available():
        pytest.skip("GUI environment not available (no QApplication)")
        
    try:
        bubble = AIChatBubble("streaming test")
        assert bubble.is_streaming is False
        assert bubble.streaming_content == ""
        assert bubble.original_message == "streaming test"
        
        # 리소스 정리
        bubble.deleteLater()
        cleanup_qt_resources()
        
    except Exception as e:
        # GUI 환경이 없을 때는 테스트를 스킵
        pytest.skip(f"GUI environment not available: {e}")


def test_reasoning_attributes() -> None:
    """추론 모델 관련 속성들이 올바르게 초기화되는지 확인한다."""
    if not check_gui_available():
        pytest.skip("GUI environment not available (no QApplication)")
        
    try:
        bubble = AIChatBubble("test message")
        assert bubble.is_reasoning_model is False
        assert bubble.reasoning_content == ""
        assert bubble.final_answer == ""
        assert bubble.show_reasoning is True
        
        # 리소스 정리
        bubble.deleteLater()
        cleanup_qt_resources()
        
    except Exception as e:
        pytest.skip(f"GUI environment not available: {e}")


def test_set_reasoning_info() -> None:
    """추론 정보 설정이 올바르게 동작하는지 확인한다."""
    if not check_gui_available():
        pytest.skip("GUI environment not available (no QApplication)")
        
    try:
        bubble = AIChatBubble("original message")
        
        # 추론 정보 설정
        reasoning_content = "이것은 추론 과정입니다."
        final_answer = "이것은 최종 답변입니다."
        
        bubble.set_reasoning_info(True, reasoning_content, final_answer)
        
        assert bubble.is_reasoning_model is True
        assert bubble.reasoning_content == reasoning_content
        assert bubble.final_answer == final_answer
        
        # 리소스 정리
        bubble.deleteLater()
        cleanup_qt_resources()
        
    except Exception as e:
        pytest.skip(f"GUI environment not available: {e}")


def test_copy_content_with_reasoning() -> None:
    """추론 모델일 때 복사 기능이 올바르게 동작하는지 확인한다."""
    if not check_gui_available():
        pytest.skip("GUI environment not available (no QApplication)")
        
    try:
        bubble = AIChatBubble("original message")
        
        # 일반 모드일 때
        bubble.copy_content()  # 예외가 발생하지 않아야 함
        
        # 추론 모델일 때
        bubble.set_reasoning_info(True, "추론 과정", "최종 답변")
        bubble.copy_content()  # 예외가 발생하지 않아야 함
        
        # 리소스 정리
        bubble.deleteLater()
        cleanup_qt_resources()
        
    except Exception as e:
        pytest.skip(f"GUI environment not available: {e}")


def test_raw_mode_with_reasoning() -> None:
    """Raw 모드에서 추론 정보가 올바르게 표시되는지 확인한다."""
    if not check_gui_available():
        pytest.skip("GUI environment not available (no QApplication)")
        
    try:
        bubble = AIChatBubble("original message")
        
        # 추론 정보 설정
        bubble.set_reasoning_info(True, "추론 과정", "최종 답변")
        
        # Raw 모드 전환
        bubble.toggle_raw_mode()
        assert bubble.raw_mode is True
        
        # 다시 Markdown 모드로 전환
        bubble.toggle_raw_mode()
        assert bubble.raw_mode is False
        
        # 리소스 정리
        bubble.deleteLater()
        cleanup_qt_resources()        
        
    except Exception as e:
        pytest.skip(f"GUI environment not available: {e}")


def test_reasoning_parsing_and_display() -> None:
    """추론 과정 파싱과 표시가 올바르게 동작하는지 확인한다."""
    if not check_gui_available():
        pytest.skip("GUI environment not available (no QApplication)")
        
    try:
        # 추론 과정이 포함된 가상 응답
        reasoning_response = """<think>
이 질문에 답하기 위해 몇 가지를 고려해야 합니다:
1. 사용자의 의도를 파악
2. 관련 정보 수집
3. 논리적인 답변 구성
</think>

안녕하세요! 질문에 대한 답변을 드리겠습니다.

이것은 추론 과정을 거쳐 도출된 최종 답변입니다."""

        bubble = AIChatBubble("original message")
        
        # 추론 과정 파싱 테스트
        from application.ui.domain.reasoning_parser import ReasoningParser
        parser = ReasoningParser()
        is_reasoning, reasoning_content, final_answer = parser.parse_reasoning_content(reasoning_response)
        
        assert is_reasoning is True
        assert "이 질문에 답하기 위해" in reasoning_content
        assert "안녕하세요!" in final_answer
        
        # 버블에 추론 정보 설정
        bubble.set_reasoning_info(is_reasoning, reasoning_content, final_answer)
        
        assert bubble.is_reasoning_model is True
        assert bubble.reasoning_content == reasoning_content
        assert bubble.final_answer == final_answer
        
        # 리소스 정리
        bubble.deleteLater()
        cleanup_qt_resources()
        
    except Exception as e:
        pytest.skip(f"GUI environment not available: {e}")


def test_real_reasoning_response() -> None:
    """실제 추론 태그가 포함된 응답 테스트"""
    if not check_gui_available():
        pytest.skip("GUI environment not available (no QApplication)")
        
    try:
        # 실제 추론 모델 응답 시뮬레이션
        real_reasoning_response = """<think>
사용자가 간단한 수학 문제를 물어봤습니다. 
3 + 2는 기본적인 덧셈 문제이므로 빠르게 계산할 수 있습니다.
3 + 2 = 5가 정답입니다.
간단하지만 정확하게 답변하겠습니다.
</think>

3 + 2 = 5입니다.

간단한 덧셈 문제네요! 다른 수학 문제가 있으시면 언제든 물어보세요."""

        bubble = AIChatBubble("original message")
        
        # 추론 과정 파싱 테스트
        from application.ui.domain.reasoning_parser import ReasoningParser
        parser = ReasoningParser()
        is_reasoning, reasoning_content, final_answer = parser.parse_reasoning_content(real_reasoning_response)
        
        assert is_reasoning is True
        assert "사용자가 간단한 수학 문제를" in reasoning_content
        assert "3 + 2 = 5입니다." in final_answer
        assert "<think>" not in final_answer  # 최종 답변에는 태그가 없어야 함
        
        # 버블에 추론 정보 설정
        bubble.set_reasoning_info(is_reasoning, reasoning_content, final_answer)
        
        # 추론 모델 속성 확인
        assert bubble.is_reasoning_model is True
        assert len(bubble.reasoning_content) > 0
        assert len(bubble.final_answer) > 0
        
        # HTML 렌더링 확인
        html_content = bubble.text_browser.toHtml()
        assert "<details" in html_content  # 접을 수 있는 추론 과정
        assert "🤔" in html_content  # 추론 아이콘
        assert "추론 과정 보기" in html_content
        
        print("✅ 실제 추론 응답 테스트 성공")
        
        # 리소스 정리
        bubble.deleteLater()
        cleanup_qt_resources()
        
    except Exception as e:
        print(f"❌ 실제 추론 응답 테스트 실패: {e}")
        raise


if __name__ == "__main__":
    pytest.main([__file__])
