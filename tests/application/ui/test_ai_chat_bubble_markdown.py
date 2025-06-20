"""AI 채팅 버블의 마크다운 렌더링 테스트"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication

from application.ui.presentation.ai_chat_bubble import AIChatBubble


@pytest.fixture
def app():
    """PySide6 애플리케이션 픽스처"""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
    finally:
        if app:
            app.quit()


@pytest.fixture
def ui_config():
    """UI 설정 픽스처"""
    return {
        'font_family': 'Arial',
        'font_size': 14
    }


class TestAIChatBubbleMarkdown:
    """AI 채팅 버블 마크다운 렌더링 테스트"""

    def test_initial_markdown_rendering(self, app, ui_config):
        """초기 메시지의 마크다운 렌더링 테스트"""
        markdown_message = """# 제목

이것은 **굵은 글씨**와 *기울임 글씨*가 있는 메시지입니다.

```python
def hello():
    print("안녕하세요!")
```

- 리스트 아이템 1
- 리스트 아이템 2
"""
        
        bubble = AIChatBubble(markdown_message, ui_config=ui_config)
        
        # 텍스트 브라우저가 HTML을 올바르게 설정했는지 확인
        assert hasattr(bubble, 'text_browser')
        html_content = bubble.text_browser.toHtml()
        
        # 마크다운이 HTML로 변환되었는지 확인 (Qt 렌더링 스타일 고려)
        assert '<h1' in html_content and '제목' in html_content
        assert 'font-weight:700' in html_content and '굵은 글씨' in html_content
        assert 'font-style:italic' in html_content and '기울임 글씨' in html_content
        assert 'monospace' in html_content  # 코드 폰트 확인
        assert '<ul' in html_content or '<li' in html_content
        assert '리스트 아이템' in html_content

    def test_update_message_content_markdown(self, app, ui_config):
        """메시지 업데이트 시 마크다운 렌더링 테스트"""
        initial_message = "초기 메시지"
        bubble = AIChatBubble(initial_message, ui_config=ui_config)
        
        # 마크다운이 포함된 새로운 메시지로 업데이트
        new_message = """## 업데이트된 메시지

**새로운 내용**이 추가되었습니다.

- 항목 1
- 항목 2

[링크 예시](https://example.com)
"""
        
        bubble.update_message_content(new_message)
        
        # 업데이트된 HTML 내용 확인 (Qt 렌더링 스타일 고려)
        html_content = bubble.text_browser.toHtml()
        assert '<h2' in html_content and '업데이트된 메시지' in html_content
        assert 'font-weight:700' in html_content and '새로운 내용' in html_content
        assert '<ul' in html_content or '<li' in html_content
        assert 'href="https://example.com"' in html_content and '링크 예시' in html_content

    def test_markdown_conversion_error_handling(self, app, ui_config):
        """마크다운 변환 오류 처리 테스트"""
        bubble = AIChatBubble("초기 메시지", ui_config=ui_config)
        
        # markdown.markdown 메서드가 예외를 발생시키도록 패치
        with patch('markdown.markdown') as mock_markdown:
            mock_markdown.side_effect = Exception("Markdown 변환 실패")
            
            # 에러가 발생해도 기본 HTML 변환이 동작해야 함
            bubble.update_message_content("테스트\n메시지")
            
            html_content = bubble.text_browser.toHtml()
            # 기본 줄바꿈 처리가 적용되었는지 확인
            assert "테스트" in html_content and "메시지" in html_content

    def test_code_block_rendering(self, app, ui_config):
        """코드 블록 렌더링 테스트"""
        code_message = """파이썬 예제 코드:

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# 테스트
print(fibonacci(10))
```

인라인 코드도 있습니다: `print("Hello")`
"""
        
        bubble = AIChatBubble(code_message, ui_config=ui_config)
        html_content = bubble.text_browser.toHtml()
        
        # 코드 블록이 올바르게 렌더링되었는지 확인 (Qt 렌더링 결과 확인)
        assert '<pre' in html_content  # Qt는 pre 태그를 사용
        assert 'monospace' in html_content  # 코드용 폰트 확인
        assert 'fibonacci' in html_content
        assert 'print' in html_content

    def test_table_rendering(self, app, ui_config):
        """테이블 렌더링 테스트"""
        table_message = """테이블 예시:

| 이름 | 나이 | 직업 |
|------|-----|------|
| 홍길동 | 30 | 개발자 |
| 김철수 | 25 | 디자이너 |
"""
        
        bubble = AIChatBubble(table_message, ui_config=ui_config)
        html_content = bubble.text_browser.toHtml()
        
        # 테이블이 올바르게 렌더링되었는지 확인 (실제 렌더링 결과에서는 table 태그가 있음)
        assert '<table' in html_content  # Qt 렌더링에서는 테이블이 제대로 렌더링됨
        assert '<tr>' in html_content
        assert '<td>' in html_content  # Qt는 모든 셀을 td로 렌더링
        assert '홍길동' in html_content
        assert '김철수' in html_content

    def test_font_config_application(self, app, ui_config):
        """폰트 설정 적용 테스트"""
        custom_config = {
            'font_family': 'Times New Roman',
            'font_size': 16
        }
        
        bubble = AIChatBubble("테스트 메시지", ui_config=custom_config)
        html_content = bubble.text_browser.toHtml()
        
        # 스타일이 올바르게 적용되었는지 확인
        assert 'Times New Roman' in html_content
        assert '16px' in html_content

    def test_korean_content_rendering(self, app, ui_config):
        """한국어 콘텐츠 렌더링 테스트"""
        korean_message = """# 한국어 마크다운 테스트

**굵은 글씨**와 *기울임 글씨*를 테스트합니다.

다음은 한국어 목록입니다:
- 첫 번째 항목
- 두 번째 항목
- 세 번째 항목

> 이것은 인용문입니다.
> 한국어 인용문이 잘 렌더링되는지 확인합니다.

```python
# 한국어 주석이 있는 코드
def 안녕():
    print("안녕하세요, 세상!")
```
"""
        
        bubble = AIChatBubble(korean_message, ui_config=ui_config)
        html_content = bubble.text_browser.toHtml()
        
        # 한국어 콘텐츠가 올바르게 렌더링되었는지 확인 (Qt 렌더링 결과 기준)
        assert '<h1' in html_content and '한국어 마크다운 테스트' in html_content
        assert 'font-weight:700' in html_content and '굵은 글씨' in html_content
        assert 'font-style:italic' in html_content and '기울임 글씨' in html_content
        assert '첫 번째 항목' in html_content
        assert 'margin-left:40px' in html_content  # Qt의 인용문 렌더링 스타일
        assert '안녕하세요, 세상!' in html_content 