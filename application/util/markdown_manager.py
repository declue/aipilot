import logging
import re
from typing import List, Match, Tuple, cast

import markdown

try:
    from pygments import highlight  # type: ignore
    from pygments.formatters import HtmlFormatter  # type: ignore
    from pygments.lexers import get_lexer_by_name  # type: ignore
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


class MarkdownManager:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def apply_table_styles(self, html_content: str) -> str:
        """HTML 테이블에 인라인 스타일 적용 (QTextBrowser 호환성 향상)"""
        try:
            # 테이블 스타일 적용
            html_content = re.sub(
                r"<table>",
                '<table style="border-collapse: collapse; width: 100%; margin: 16px 0; border: 2px solid #E5E7EB; border-radius: 8px; overflow: hidden;">',
                html_content,
            )

            # 테이블 헤더 스타일
            html_content = re.sub(
                r"<th>",
                '<th style="background: linear-gradient(135deg, #F3F4F6 0%, #E5E7EB 100%); color: #374151; font-weight: 600; padding: 12px 16px; text-align: left; border-bottom: 2px solid #D1D5DB; font-size: 14px;">',
                html_content,
            )

            # 테이블 셀 스타일
            html_content = re.sub(
                r"<td>",
                '<td style="padding: 12px 16px; border-bottom: 1px solid #F3F4F6; vertical-align: top; font-size: 14px; line-height: 1.6;">',
                html_content,
            )

            # 테이블 행 hover 효과는 QTextBrowser에서 지원되지 않으므로 제외
            return html_content

        except Exception as e:
            self.logger.error("테이블 스타일 적용 중 오류: %s", e)
            return html_content

    def optimize_for_qtextbrowser(self, html_content: str) -> str:
        """QTextBrowser에 최적화된 HTML로 변환"""
        try:
            result_lines = []
            for line in html_content.split("\n"):
                stripped_line = line.strip()
                if stripped_line:
                    result_lines.append(stripped_line)

            return "\n".join(result_lines)
        except Exception as e:
            self.logger.error("QTextBrowser 최적화 중 오류: %s", e)
            return html_content

    def convert_with_syntax_highlighting(
        self, markdown_content: str
    ) -> Tuple[str, List[str]]:
        """
        마크다운을 HTML로 변환하면서 코드 블록에 문법 하이라이트를 적용합니다.
        Returns: (html_content, code_blocks_list)
        """
        try:
            code_blocks = []
            processed_content = markdown_content

            # 1. Fenced code blocks 찾기 및 처리
            def process_fenced_code(match: Match[str]) -> str:
                language = match.group(1) or ""
                code_content = match.group(2).strip()

                # 코드 블록 리스트에 추가
                code_blocks.append(code_content)
                code_index = len(code_blocks) - 1

                # 언어 자동 감지
                if not language:
                    language = self.detect_language(code_content)

                # 문법 하이라이트 적용
                highlighted_code = self.apply_syntax_highlighting(
                    code_content, language
                )

                # 코드 블록 HTML 생성
                return self.create_code_block_html(
                    highlighted_code, language, code_index
                )

            # Fenced code blocks 패턴 (```language\ncode\n```)
            fenced_pattern = r"```(\w+)?\n(.*?)\n```"
            processed_content = re.sub(
                fenced_pattern, process_fenced_code, processed_content, flags=re.DOTALL
            )

            # 2. 나머지 마크다운을 HTML로 변환
            html_content = markdown.markdown(
                processed_content,
                extensions=[
                    "markdown.extensions.tables",
                    "markdown.extensions.nl2br",
                    "markdown.extensions.extra",
                ],
            )

            # 3. 표 스타일 적용
            html_content = self.apply_table_styles(html_content)

            return html_content, code_blocks

        except Exception as e:
            self.logger.error("문법 하이라이트 변환 중 오류: %s", e)
            # 오류 시 기본 마크다운 변환
            basic_html = markdown.markdown(
                markdown_content,
                extensions=[
                    "markdown.extensions.tables",
                    "markdown.extensions.fenced_code",
                    "markdown.extensions.nl2br",
                ],
            )
            return self.apply_table_styles(basic_html), []

    def apply_syntax_highlighting(self, code_content: str, language: str) -> str:
        """Pygments를 사용하여 코드에 문법 하이라이트를 적용합니다."""
        try:

            # 언어별 Lexer 가져오기
            try:
                lexer = get_lexer_by_name(language, stripall=True)
            except Exception as e:
                self.logger.error("언어 감지 중 오류: %s", e)
                # 알 수 없는 언어는 text로 처리
                lexer = get_lexer_by_name("text", stripall=True)

            # HTML 포매터 설정 (밝은 배경용 어두운 글자색)
            formatter = HtmlFormatter(
                style="default",  # 기본 스타일 (어두운 글자색)
                noclasses=True,
                nowrap=True,
                cssclass="",
            )

            # 문법 하이라이트 적용
            highlighted_raw = highlight(code_content, lexer, formatter)
            # Pygments highlight stubs may return Any; cast to str for static typing tools
            highlighted: str = cast(str, highlighted_raw)

            # 어두운 글자색으로 색상 조정
            highlighted = self._adjust_colors_for_light_background(highlighted)

            return highlighted

        except ImportError:
            # Pygments가 없는 경우 기본 처리
            import html

            return html.escape(code_content)
        except Exception:
            # Pygments가 없거나 오류가 발생한 경우
            if not PYGMENTS_AVAILABLE:
                import html
                return html.escape(code_content)
            raise
        except Exception as e:
            self.logger.warning("문법 하이라이트 적용 실패: %s", e)
            import html

            return html.escape(code_content)

    def create_code_block_html(
        self, highlighted_code: str, language: str, code_index: int
    ) -> str:
        """코드 블록 HTML을 생성합니다."""
        display_language = language.upper() if language else "TEXT"

        return f"""
<div class="code-block" data-code-index="{code_index}" style="margin: 16px 0; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden;">
    <div class="code-header" style="background-color: #F1F5F9; padding: 12px 16px; border-bottom: 1px solid #E2E8F0;">
        <span style="font-size: 12px; font-weight: 600; color: #475569; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;">{display_language}</span>
    </div>
    <div class="code-content" style="background-color: #F8FAFC; padding: 20px; overflow-x: auto;">
        <pre style="margin: 0; padding: 0; background: transparent; color: #1F2937; font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace; font-size: 14px; line-height: 1.45; white-space: pre; overflow-x: auto;">{highlighted_code}</pre>
    </div>
</div>"""

    def detect_language(self, code_content: str) -> str:
        """코드 내용을 분석하여 프로그래밍 언어를 추정합니다."""
        code_lower = code_content.lower().strip()

        # SQL 패턴 (Python보다 먼저 검사)
        if any(
            keyword in code_lower
            for keyword in [
                "select ",
                "from ",
                "where ",
                "insert ",
                "update ",
                "delete ",
            ]
        ):
            return "sql"

        # Python 패턴
        if any(
            keyword in code_lower
            for keyword in [
                "def ",
                "import ",
                "from ",
                "print(",
                "if __name__",
                "class ",
            ]
        ):
            return "python"

        # JavaScript 패턴
        if any(
            keyword in code_lower
            for keyword in ["function", "const ", "let ", "var ", "console.log", "=>"]
        ):
            return "javascript"

        # Java 패턴
        if any(
            keyword in code_lower
            for keyword in [
                "public class",
                "public static void main",
                "System.out.println",
            ]
        ):
            return "java"

        # HTML 패턴
        if any(
            keyword in code_lower for keyword in ["<html", "<!doctype", "<div", "<body"]
        ):
            return "html"

        # JSON 패턴
        stripped = code_content.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        ):
            return "json"

        # Bash/Shell 패턴
        if any(
            keyword in code_lower
            for keyword in ["#!/bin/bash", "#!/bin/sh", "echo ", "cd ", "ls "]
        ):
            return "bash"

        return "text"  # 기본값

    def _adjust_colors_for_light_background(self, highlighted_html: str) -> str:
        """밝은 배경에 맞게 글자색을 어두운색으로 조정"""


        # 기본 색상을 어두운색으로 매핑
        color_mappings = {
            # 기본 텍스트 색상
            "color: #000000": "color: #1F2937",  # 검은색 → 진한 회색
            "color: #000080": "color: #1E40AF",  # 네이비 → 파란색
            "color: #008000": "color: #059669",  # 초록색 → 에메랄드
            "color: #800080": "color: #7C3AED",  # 보라색 → 바이올렛
            "color: #800000": "color: #DC2626",  # 마룬 → 빨간색
            "color: #808000": "color: #D97706",  # 올리브 → 주황색
            "color: #008080": "color: #0891B2",  # 틸 → 시안
            "color: #c0c0c0": "color: #6B7280",  # 실버 → 회색
            "color: #808080": "color: #4B5563",  # 회색 → 진한 회색
            "color: #ff0000": "color: #EF4444",  # 빨간색 → 밝은 빨간색
            "color: #00ff00": "color: #10B981",  # 라임 → 초록색
            "color: #ffff00": "color: #F59E0B",  # 노란색 → 앰버
            "color: #0000ff": "color: #3B82F6",  # 파란색 → 밝은 파란색
            "color: #ff00ff": "color: #EC4899",  # 마젠타 → 핑크
            "color: #00ffff": "color: #06B6D4",  # 시안 → 밝은 시안
            "color: #ffffff": "color: #111827",  # 흰색 → 거의 검은색
        }

        # 색상 교체
        for old_color, new_color in color_mappings.items():
            highlighted_html = highlighted_html.replace(old_color, new_color)

        # 배경색 제거 (코드 블록 자체 배경 사용)
        highlighted_html = re.sub(r"background-color: [^;]+;", "", highlighted_html)
        highlighted_html = re.sub(r"background: [^;]+;", "", highlighted_html)

        return highlighted_html
