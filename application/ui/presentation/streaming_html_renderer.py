from __future__ import annotations

from typing import Any, Dict

"""StreamingHtmlRenderer – Presentation Layer"""

import markdown

from application.util.markdown_manager import MarkdownManager


class StreamingHtmlRenderer:
    """스트리밍용 HTML을 렌더링하는 클래스"""

    def __init__(self, ui_config: Dict[str, Any]):
        self.ui_config: Dict[str, Any] = ui_config
        self.md_manager = MarkdownManager()

    # --- 기존 구현 메서드들 ---

    def create_reasoning_html(self, reasoning_content: str, final_answer: str) -> str:
        """추론 과정을 폴딩 가능한 HTML로 생성"""
        reasoning_html = markdown.markdown(
            reasoning_content,
            extensions=["codehilite", "fenced_code", "tables", "toc"],
        )
        reasoning_html = self.md_manager.apply_table_styles(reasoning_html)

        final_html = ""
        if final_answer:
            final_html = markdown.markdown(
                final_answer,
                extensions=["codehilite", "fenced_code", "tables", "toc"],
            )
            final_html = self.md_manager.apply_table_styles(final_html)

        return f"""
        <div style="
            color: #1F2937;
            line-height: 1.6;
            font-family: '{self.ui_config['font_family']}';
            font-size: {self.ui_config['font_size']}px;
        ">
            <details style="margin-bottom: 16px; border: 1px solid #F59E0B; border-radius: 8px; padding: 12px; background-color: #FFFBEB;">
                <summary style="
                    cursor: pointer;
                    font-size: {max(self.ui_config['font_size'] - 2, 10)}px;
                    color: #F59E0B;
                    font-weight: 500;
                    margin-bottom: 8px;
                    user-select: none;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                ">
                    <span style="font-size: 14px;">🤔</span>
                    <span>&lt;think&gt; 추론 과정 보기</span>
                </summary>
                <div style="
                    font-size: {max(self.ui_config['font_size'] - 2, 10)}px;
                    color: #6B7280;
                    background-color: #F9FAFB;
                    padding: 12px;
                    border-radius: 6px;
                    margin-top: 8px;
                    border-left: 3px solid #F59E0B;
                ">
                    {reasoning_html}
                </div>
            </details>
            {final_html}
        </div>
        """

    def create_streaming_reasoning_html(
        self,
        reasoning_content: str,
        final_answer: str,
        show_cursor: bool = True,
        reasoning_only: bool = False,
    ) -> str:
        """스트리밍 중인 추론 과정을 위한 HTML 생성"""
        reasoning_html = markdown.markdown(
            reasoning_content,
            extensions=["codehilite", "fenced_code", "tables", "toc"],
        )
        reasoning_html = self.md_manager.apply_table_styles(reasoning_html)

        final_html = ""
        if final_answer:
            final_html = markdown.markdown(
                final_answer,
                extensions=["codehilite", "fenced_code", "tables", "toc"],
            )
            final_html = self.md_manager.apply_table_styles(final_html)

        cursor = (
            '<span style="color: #10B981; font-weight: bold;">▌</span>'
            if show_cursor
            else ""
        )

        if reasoning_only:
            return f"""
            <div style="
                color: #1F2937;
                line-height: 1.6;
                font-family: '{self.ui_config['font_family']}';
                font-size: {self.ui_config['font_size']}px;
            ">
                <div style="
                    font-size: {max(self.ui_config['font_size'] - 2, 10)}px;
                    color: #6B7280;
                    background-color: #F9FAFB;
                    padding: 12px;
                    border-radius: 6px;
                    border-left: 3px solid #F59E0B;
                    margin-bottom: 12px;
                ">
                    <div style="
                        font-weight: 500; 
                        margin-bottom: 8px;
                        color: #F59E0B;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    ">
                        <span style="font-size: 14px;">🤔</span>
                        <span>&lt;think&gt; 추론 중...</span>
                    </div>
                    {reasoning_html}
                    {cursor}
                </div>
            </div>
            """
        return f"""
            <div style="
                color: #1F2937;
                line-height: 1.6;
                font-family: '{self.ui_config['font_family']}';
                font-size: {self.ui_config['font_size']}px;
            ">
                <details open style="margin-bottom: 16px; border: 1px solid #F59E0B; border-radius: 8px; padding: 12px; background-color: #FFFBEB;">
                    <summary style="
                        cursor: pointer;
                        font-size: {max(self.ui_config['font_size'] - 2, 10)}px;
                        color: #F59E0B;
                        font-weight: 500;
                        margin-bottom: 8px;
                        user-select: none;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    ">
                        <span style="font-size: 14px;">🤔</span>
                        <span>&lt;think&gt; 추론 과정 보기</span>
                    </summary>
                    <div style="
                        font-size: {max(self.ui_config['font_size'] - 2, 10)}px;
                        color: #6B7280;
                        background-color: #F9FAFB;
                        padding: 12px;
                        border-radius: 6px;
                        margin-top: 8px;
                        border-left: 3px solid #F59E0B;
                    ">
                        {reasoning_html}
                    </div>
                </details>
                {final_html}
                {cursor}
            </div>
            """

    def create_regular_streaming_html(self, content: str) -> str:
        """일반 스트리밍용 HTML 생성"""
        html_content = markdown.markdown(
            content,
            extensions=["codehilite", "fenced_code", "tables", "toc"],
        )
        html_content = self.md_manager.apply_table_styles(html_content)

        return f"""
        <div style="
            color: #1F2937;
            line-height: 1.6;
            font-family: '{self.ui_config['font_family']}';
            font-size: {self.ui_config['font_size']}px;
        ">
            {html_content}
            <span style="color: #10B981; font-weight: bold;">▌</span>
        </div>
        """

    def create_stopped_html(self, content: str) -> str:
        """중단된 스트리밍용 HTML 생성"""
        html_content = (
            markdown.markdown(
                content,
                extensions=["codehilite", "fenced_code", "tables", "toc"],
            )
            if content
            else ""
        )

        return f"""
        <div style="
            color: #1F2937;
            line-height: 1.6;
            font-family: '{self.ui_config['font_family']}';
            font-size: {self.ui_config['font_size']}px;
        ">
            {html_content}
            <div style="color: #DC2626; font-style: italic; margin-top: 10px;">
                [응답이 중단되었습니다]
            </div>
        </div>
        """ 