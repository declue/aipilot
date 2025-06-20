import pytest

from application.util.markdown_manager import PYGMENTS_AVAILABLE, MarkdownManager


class TestMarkdownManagerDetectLanguage:
    """`detect_language` 메서드에 대한 테스트"""

    @pytest.mark.parametrize(
        "code, expected",
        [
            ("def foo():\n    pass", "python"),
            ("function foo() { console.log('hi'); }", "javascript"),
            ("public static void main(String[] args) { }", "java"),
            ("SELECT * FROM users WHERE id = 1;", "sql"),
            ("<html><body></body></html>", "html"),
            ("{\"name\": \"bob\"}", "json"),
            ("#!/bin/bash\necho 'hi'", "bash"),
            ("some unknown content", "text"),
        ],
    )
    def test_detect_language(self, code: str, expected: str) -> None:
        manager = MarkdownManager()
        assert manager.detect_language(code) == expected


class TestMarkdownManagerTableStyle:
    """`apply_table_styles` 메서드에 대한 테스트"""

    def test_apply_table_styles(self) -> None:
        manager = MarkdownManager()
        html = "<table><tr><th>H</th></tr><tr><td>1</td></tr></table>"
        styled = manager.apply_table_styles(html)

        # 테이블 태그가 스타일 속성을 포함하는지 확인
        assert "border-collapse: collapse" in styled
        # th, td 역시 스타일이 적용됐는지 확인
        assert "background: linear-gradient" in styled  # th 스타일
        assert "vertical-align: top" in styled  # td 스타일


class TestMarkdownManagerOptimizeForQTextBrowser:
    """`optimize_for_qtextbrowser` 메서드에 대한 테스트"""

    def test_optimize_for_qtextbrowser(self) -> None:
        manager = MarkdownManager()
        html = "   <p>hello</p>  \n\n   <p>world</p>   "
        optimized = manager.optimize_for_qtextbrowser(html)
        assert optimized == "<p>hello</p>\n<p>world</p>"


class TestMarkdownManagerConvert:
    """`convert_with_syntax_highlighting` 메서드에 대한 테스트"""

    def test_convert_with_code_block(self) -> None:
        manager = MarkdownManager()
        markdown_text = (
            "```python\n"
            "def foo():\n"
            "    return 42\n"
            "```"
        )

        html, code_blocks = manager.convert_with_syntax_highlighting(markdown_text)

        # 반환된 코드 블록 리스트가 올바른지
        assert len(code_blocks) == 1
        assert "def foo():" in code_blocks[0]

        # 생성된 HTML 구조 확인
        assert "code-block" in html
        assert "PYTHON" in html  # 언어 라벨

    @pytest.mark.skipif(not PYGMENTS_AVAILABLE, reason="Pygments 미설치 환경")
    def test_convert_html_contains_syntax_highlight(self) -> None:
        """Pygments 가 설치된 경우 실제 하이라이트된 HTML 이 포함되는지 간단히 확인"""
        manager = MarkdownManager()
        markdown_text = "```python\nprint('hi')\n```"
        html, _ = manager.convert_with_syntax_highlighting(markdown_text)
        # pygments 가 적용되면 span 태그 등이 포함됨
        assert "<span" in html 