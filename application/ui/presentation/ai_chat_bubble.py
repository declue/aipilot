from __future__ import annotations

"""AIChatBubble – Presentation Layer

최소 standalone 구현.
기존 레거시 버전(수백 라인)을 단계적으로
이곳으로 이전하기 전에, 우선 BaseChatBubble 을 상속한
간단한 메시지 렌더러를 제공해 순환 import 를 제거한다.
"""

import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from application.ui.presentation.base_chat_bubble import ChatBubble
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("ai_chat_bubble") or logging.getLogger("ai_chat_bubble")


class AIChatBubble(ChatBubble):  # pylint: disable=too-many-ancestors
    """간단한 AI 응답 채팅 버블.

    완전한 기능(Markdown 하이라이트, raw/markdown 토글, 툴 정보 표시 등)은
    향후 단계에서 다시 채워넣는다. 현재는 최소한의 QTextBrowser 로 내용을
    렌더링하여 UI 가 깨지지 않도록 보장하는 수준이다.
    """

    AVATAR_ICON = "🤖"
    AVATAR_SIZE = 40

    def __init__(
        self,
        message: str,
        ui_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QFrame] = None,
        avatar_icon: Optional[str] = None,
    ) -> None:
        self.avatar_icon = avatar_icon or self.AVATAR_ICON
        # streaming related defaults (for compatibility with legacy managers)
        self.is_streaming: bool = False
        self.streaming_content: str = ""
        self.original_content: str = ""
        self.original_message: str = message
        
        # Raw 모드 관련 초기화
        self.raw_mode: bool = False
        self.toggle_button: Optional[QPushButton] = None
        self.copy_button: Optional[QPushButton] = None
        
        super().__init__(message=message, ui_config=ui_config, parent=parent)

    # ------------------------------------------------------------------
    # ChatBubble overrides
    # ------------------------------------------------------------------
    def setup_ui(self) -> None:  # noqa: D401 – Not a docstring test target
        """QFrame 기반의 간단한 좌측 정렬 버블 UI 작성."""
        self.setContentsMargins(0, 0, 0, 0)
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        # Avatar (이모지 아이콘)
        avatar_lbl = QLabel(self.avatar_icon)
        avatar_lbl.setFixedSize(self.AVATAR_SIZE, self.AVATAR_SIZE)
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        root_layout.addWidget(avatar_lbl)

        # Bubble container
        bubble_frame: QFrame = QFrame()
        
        # 최대 너비 설정 (화면의 80%)
        max_width = self.get_max_width()
        bubble_frame.setMaximumWidth(max_width)
        
        bubble_frame.setStyleSheet(
            """
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }"""
        )
        bubble_layout = QVBoxLayout(bubble_frame)
        bubble_layout.setContentsMargins(12, 8, 12, 8)

        # Text area
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)
        
        # 최대 너비 설정 (버블 너비에서 여백 제외)
        text_browser.setMaximumWidth(max_width - 32)  # 버블 여백 고려
        
        # word wrap
        text_browser.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        
        # 스크롤바 비활성화 (높이 자동 조절을 위해)
        text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        font_family, font_size = self.get_font_config()
        text_browser.setStyleSheet(
            f"QTextBrowser {{ background: transparent; border: none; font-family: '{font_family}'; font-size: {font_size}px; }}"
        )
        
        # 초기 메시지에 마크다운 렌더링 적용
        try:
            import markdown

            from application.util.markdown_manager import MarkdownManager
            
            html_content = markdown.markdown(
                self.message,
                extensions=["codehilite", "fenced_code", "tables", "toc"],
            )
            
            # 테이블 스타일 적용 (스트리밍과 동일하게)
            md_manager = MarkdownManager()
            html_content = md_manager.apply_table_styles(html_content)
            
            styled_html = f"""
            <div style="
                color: #1F2937;
                line-height: 1.6;
                font-family: '{font_family}';
                font-size: {font_size}px;
            ">
                {html_content}
            </div>
            """
            text_browser.setHtml(styled_html)
        except Exception as e:
            logger.warning(f"초기 마크다운 변환 실패: {e}")
            text_browser.setHtml(self.message.replace("\n", "<br>"))
        
        # 텍스트 내용에 맞게 높이 자동 조절
        self._adjust_text_browser_height(text_browser)
        
        # 문서 내용이 변경될 때마다 높이 자동 조절
        text_browser.document().contentsChanged.connect(
            lambda: self._adjust_text_browser_height(text_browser)
        )
        
        bubble_layout.addWidget(text_browser)

        # 버튼 컨테이너 추가
        button_container = QFrame()
        button_container.setStyleSheet("QFrame{background:transparent;border:none;}")
        btn_layout = QHBoxLayout(button_container)
        btn_layout.setContentsMargins(0, 8, 0, 0)
        btn_layout.addStretch()

        # Copy 버튼
        self.copy_button = QPushButton("📋")
        self.copy_button.setMinimumSize(32, 28)
        self.copy_button.setToolTip("내용 복사")
        self.copy_button.setStyleSheet(
            """
            QPushButton {
                background-color: #F3F4F6;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                font-size: 11px;
                font-weight: 500;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
                border-color: #9CA3AF;
            }
            QPushButton:pressed {
                background-color: #D1D5DB;
                border-color: #6B7280;
            }
        """
        )
        self.copy_button.clicked.connect(self.copy_content)

        # Raw 토글 버튼
        self.toggle_button = QPushButton("📝")
        self.toggle_button.setMinimumSize(32, 28)
        self.toggle_button.setToolTip("RAW 전환")
        self.toggle_button.setStyleSheet(
            """
            QPushButton {
                background-color: #F3F4F6;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                font-size: 11px;
                font-weight: 500;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
                border-color: #9CA3AF;
            }
            QPushButton:pressed {
                background-color: #D1D5DB;
                border-color: #6B7280;
            }
        """
        )
        self.toggle_button.clicked.connect(self.toggle_raw_mode)

        # 버튼들을 컨테이너에 추가
        btn_layout.addWidget(self.copy_button)
        btn_layout.addSpacing(4)
        btn_layout.addWidget(self.toggle_button)
        bubble_layout.addWidget(button_container)

        # expose for external managers
        self.text_browser: QTextBrowser = text_browser  # type: ignore

        # bubble_frame을 stretch factor 1로 추가하여 사용자 버블과 동일한 동작 구현
        root_layout.addWidget(bubble_frame, 1)
        root_layout.addStretch()

    # ------------------------------------------------------------------
    # Convenience factory (GitHub icon etc.) – stubbed
    # ------------------------------------------------------------------
    @staticmethod
    def create_github_bubble(  # type: ignore[override]
        message: str,
        ui_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QFrame] = None,
    ) -> "AIChatBubble":
        """현재는 아이콘만 바꾼 동일 버전의 버블을 반환한다."""
        return AIChatBubble(message=message, ui_config=ui_config, parent=parent, avatar_icon="🐱")

    # ------------------------------------------------------------------
    # Legacy-API compatibility (no-op stubs)
    # ------------------------------------------------------------------
    def adjust_browser_height(self, browser: QTextBrowser) -> None:  # noqa: D401
        """Resize browser height to fit its document (simple version)."""
        self._adjust_text_browser_height(browser)

    def _adjust_text_browser_height(self, browser: QTextBrowser) -> None:
        """텍스트 브라우저 높이를 내용에 맞게 자동 조절"""
        try:
            from PySide6.QtCore import QTimer

            # 짧은 지연 후 높이 조절 (렌더링 완료 대기)
            def adjust_height() -> None:
                try:
                    # 문서 크기 계산
                    document = browser.document()
                    
                    # 현재 브라우저 너비에 맞게 텍스트 너비 설정
                    if browser.viewport().width() > 0:
                        document.setTextWidth(browser.viewport().width())
                    
                    # 문서 높이 가져오기
                    doc_height = document.size().height()
                    
                    # 최소 높이와 최대 높이 설정 (합리적인 범위)
                    min_height = 40  # 최소 높이
                    max_height = 1000  # 최대 높이 (화면에 맞게 조정)
                    
                    # 계산된 높이에 여백 추가
                    calculated_height = int(doc_height) + 30  # 여분의 여백
                    
                    # 범위 내에서 높이 설정
                    final_height = max(min_height, min(calculated_height, max_height))
                    
                    # 현재 높이와 다를 때만 설정 (불필요한 업데이트 방지)
                    if browser.height() != final_height:
                        browser.setFixedHeight(final_height)
                        logger.debug(f"텍스트 브라우저 높이 조절: {final_height}px (문서 높이: {doc_height}px)")
                    
                except Exception as e:
                    logger.warning(f"지연된 높이 조절 실패: {e}")
                    browser.setFixedHeight(100)
            
            # 50ms 지연 후 높이 조절
            QTimer.singleShot(50, adjust_height)
            
        except Exception as e:
            logger.warning(f"텍스트 브라우저 높이 조절 실패: {e}")
            # 실패 시 기본 높이 설정
            browser.setFixedHeight(100)

    def show_raw_button(self) -> None:  # noqa: D401
        """Show the raw/markdown toggle button."""
        if self.toggle_button:
            self.toggle_button.show()
        if self.copy_button:
            self.copy_button.show()

    def set_used_tools(self, _tools: list[Any] | None = None) -> None:  # noqa: D401
        """Store tools list for later (unused)."""
        self._used_tools = _tools  # type: ignore

    def set_reasoning_info(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
        """Stub for reasoning-model metadata."""
        pass

    def update_message_content(self, new_content: str) -> None:  # noqa: D401
        """Update displayed HTML with new content."""
        import markdown

        from application.util.markdown_manager import MarkdownManager
        
        self.message = new_content
        if hasattr(self, "text_browser") and self.text_browser:
            # Raw 모드인 경우 플레인 텍스트 표시
            if self.raw_mode:
                font_family, font_size = self.get_font_config()
                raw_html = f"""
                <div style="
                    color: #1F2937;
                    line-height: 1.6;
                    font-family: 'monospace';
                    font-size: {font_size}px;
                    white-space: pre-wrap;
                    background-color: #F3F4F6;
                    padding: 12px;
                    border-radius: 8px;
                    border: 1px solid #D1D5DB;
                ">
                    {new_content}
                </div>
                """
                self.text_browser.setHtml(raw_html)
                # 높이 자동 조절
                self._adjust_text_browser_height(self.text_browser)
                return
            
            # 마크다운을 HTML로 변환
            try:
                html_content = markdown.markdown(
                    new_content,
                    extensions=["codehilite", "fenced_code", "tables", "toc"],
                )
                
                # 테이블 스타일 적용 (스트리밍과 동일하게)
                md_manager = MarkdownManager()
                html_content = md_manager.apply_table_styles(html_content)
                
                # UI 설정 가져오기
                font_family, font_size = self.get_font_config()
                
                # 스타일이 적용된 HTML 생성
                styled_html = f"""
                <div style="
                    color: #1F2937;
                    line-height: 1.6;
                    font-family: '{font_family}';
                    font-size: {font_size}px;
                ">
                    {html_content}
                </div>
                """
                
                self.text_browser.setHtml(styled_html)
            except Exception as e:
                logger.warning(f"마크다운 변환 실패, 플레인 HTML 사용: {e}")
                # 변환 실패 시 기본 줄바꿈 처리
                self.text_browser.setHtml(new_content.replace("\n", "<br>"))
            
            # 마크다운 렌더링 후 높이 자동 조절
            self._adjust_text_browser_height(self.text_browser)

    def copy_content(self) -> None:
        """메시지 내용을 클립보드에 복사"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.message)
            logger.debug("메시지 내용이 클립보드에 복사되었습니다")
        except Exception as e:
            logger.error(f"클립보드 복사 실패: {e}")

    def toggle_raw_mode(self) -> None:
        """Raw/Markdown 모드 전환"""
        self.raw_mode = not self.raw_mode
        
        # 토글 버튼 텍스트 업데이트
        if self.toggle_button:
            if self.raw_mode:
                self.toggle_button.setText("📄")
                self.toggle_button.setToolTip("Markdown으로 전환")
            else:
                self.toggle_button.setText("📝")
                self.toggle_button.setToolTip("RAW로 전환")
        
        # 메시지 내용 다시 렌더링
        self.update_message_content(self.message)
        
        logger.debug(f"표시 모드 전환: {'RAW' if self.raw_mode else 'Markdown'}")


__all__: list[str] = ["AIChatBubble"] 