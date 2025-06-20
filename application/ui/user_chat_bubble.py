import logging

import markdown
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

from application.ui.chat_bubble import ChatBubble
from application.util.logger import setup_logger
from application.util.markdown_manager import MarkdownManager

logger: logging.Logger = setup_logger("user_chat_bubble") or logging.getLogger(
    "user_chat_bubble"
)


class UserChatBubble(ChatBubble):
    """사용자 메시지 채팅 버블"""

    def __init__(
        self,
        message: str,
        ui_config=None,
        parent=None,
    ) -> None:
        # Raw 모드 관련 초기화
        self.raw_mode = False
        super().__init__(message, ui_config, parent)

    def setup_ui(self) -> None:
        """사용자 메시지 UI 레이아웃 설정"""
        try:
            self.setContentsMargins(0, 0, 0, 0)
            layout: QHBoxLayout = QHBoxLayout(self)

            # 사용자 메시지 (우측 정렬) - ChatGPT 스타일
            logger.debug("Setting up USER bubble")
            layout.setContentsMargins(8, 16, 8, 16)  # 좌우 여백을 8px로 최소화
            layout.setSpacing(16)
            layout.addStretch()  # 좌측에 stretch 추가 (버블이 우측에 붙도록)
            self.setup_user_bubble(layout)

        except Exception as exception:
            logger.error("Failed to setup UI layout: %s", str(exception))
            raise RuntimeError("UI setup failed") from exception

    def setup_user_bubble(self, layout: QHBoxLayout) -> None:
        """
        사용자 메시지 버블 설정

        Args:
            layout: 부모 레이아웃

        Raises:
            RuntimeError: 버블 설정 중 오류 발생시
        """
        try:
            bubble_frame: QFrame = QFrame()
            # 반응형 너비: 설정된 최대 너비 사용
            max_width: int = self.get_max_width()
            bubble_frame.setMaximumWidth(max_width)

            bubble_frame.setStyleSheet(
                """
                QFrame {
                    background-color: #2563EB;
                    border-radius: 20px;
                    padding: 0;
                    margin: 0;
                }
            """
            )

            bubble_layout: QVBoxLayout = QVBoxLayout(bubble_frame)
            bubble_layout.setContentsMargins(12, 12, 12, 12)  # 패딩 줄임
            bubble_layout.setSpacing(8)

            # Raw 보기 버튼 컨테이너
            button_container = QFrame()
            button_container.setStyleSheet(
                """
                QFrame {
                    background-color: transparent;
                    border: none;
                    margin: 0;
                    padding: 0;
                }
            """
            )
            button_container_layout = QHBoxLayout(button_container)
            button_container_layout.setContentsMargins(0, 8, 0, 0)
            button_container_layout.addStretch()

            # Raw 토글 버튼
            self.toggle_button = QPushButton("📝")
            self.toggle_button.setMinimumSize(32, 28)
            self.toggle_button.setToolTip("RAW 전환")
            self.toggle_button.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.2);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.3);
                    border-color: rgba(255, 255, 255, 0.5);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.1);
                    border-color: rgba(255, 255, 255, 0.4);
                }
            """
            )
            self.toggle_button.clicked.connect(self.toggle_raw_mode)

            # Copy 버튼
            self.copy_button = QPushButton("📋")
            self.copy_button.setMinimumSize(32, 28)
            self.copy_button.setToolTip("내용 복사")
            self.copy_button.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.2);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.3);
                    border-color: rgba(255, 255, 255, 0.5);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.1);
                    border-color: rgba(255, 255, 255, 0.4);
                }
            """
            )
            self.copy_button.clicked.connect(self.copy_content)

            # 버튼들을 컨테이너에 추가 (약간의 간격을 두고)
            button_container_layout.addWidget(self.copy_button)
            button_container_layout.addSpacing(4)  # 버튼 사이 간격
            button_container_layout.addWidget(self.toggle_button)
            bubble_layout.addWidget(button_container)

            # 메시지 텍스트
            text_browser: QTextBrowser = QTextBrowser()
            # 텍스트 브라우저 최대 너비 설정 (패딩 최소화)
            text_browser.setMaximumWidth(
                max_width - 16
            )  # 패딩을 최소화하여 16px만 빼기

            # 마크다운 렌더링 적용
            self._apply_content_to_browser(text_browser)
            text_browser.setStyleSheet(self._get_user_stylesheet())
            text_browser.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            text_browser.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            text_browser.document().setDocumentMargin(0)
            # 워드랩 활성화하여 텍스트가 너비에 맞게 줄바꿈되도록 설정
            text_browser.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

            # 내용 크기에 맞게 높이 조정
            text_browser.document().setTextWidth(max_width - 16)  # 텍스트 너비 설정
            document_height = text_browser.document().size().height()
            text_browser.setFixedHeight(int(document_height) + 5)  # 약간의 여백 추가

            bubble_layout.addWidget(text_browser)

            # 텍스트 브라우저를 인스턴스 변수로 저장 (토글용)
            self.text_browser = text_browser

            # 버블 프레임에도 stretch factor를 주어 충분히 확장되도록 함
            layout.addWidget(bubble_frame, 1)

            logger.debug("User bubble setup completed successfully")

        except Exception as exception:
            logger.error("Failed to setup user bubble: %s", str(exception))
            raise RuntimeError("User bubble setup failed") from exception

    def update_styles(self) -> None:
        """스타일 업데이트 - 사용자 버블 전용"""
        try:
            font_family, font_size = self.get_font_config()
            max_width = self.get_max_width()

            logger.debug(
                f"사용자 버블 스타일 업데이트: 폰트={font_family}, 크기={font_size}px, 최대너비={max_width}px"
            )

            # 모든 QTextBrowser 위젯을 찾아서 업데이트
            text_browsers = self.findChildren(QTextBrowser)
            for browser in text_browsers:
                # 현재 Raw 모드인지 확인하여 적절한 콘텐츠 적용
                if self.raw_mode:
                    # Raw 모드: 원본 텍스트와 monospace 폰트
                    browser.setPlainText(self.message)
                    browser.setStyleSheet(
                        f"""
                        QTextBrowser {{
                            background-color: transparent;
                            border: none;
                            padding: 0;
                            margin: 0;
                            font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
                            font-size: {font_size}px;
                            color: white;
                            line-height: 1.4;
                        }}
                    """
                    )
                else:
                    # Markdown 모드: 마크다운 렌더링
                    self._apply_content_to_browser(browser)
                    browser.setStyleSheet(self._get_user_stylesheet())

                # 크기 재조정 - 순서가 중요함
                browser.setMaximumWidth(max_width - 16)
                browser.document().setTextWidth(max_width - 16)
                # 문서 업데이트 후 높이 재계산
                browser.document().adjustSize()
                document_height = browser.document().size().height()
                new_height = int(document_height) + 10  # 더 여유있게
                browser.setFixedHeight(new_height)

                logger.debug(
                    f"텍스트 브라우저 크기 조정: 너비={max_width-16}px, 높이={new_height}px"
                )

            # 버블 프레임 크기도 업데이트
            bubble_frames = self.findChildren(QFrame)
            for frame in bubble_frames:
                if (
                    frame.styleSheet()
                    and "background-color: #2563EB" in frame.styleSheet()
                ):
                    frame.setMaximumWidth(max_width)
                    logger.debug(f"사용자 버블 프레임 최대 너비 설정: {max_width}px")

            # 부모 레이아웃에 업데이트 알림
            self.updateGeometry()
            self.update()

        except Exception as exception:
            logger.error("Failed to update user bubble styles: %s", str(exception))

    def toggle_raw_mode(self) -> None:
        """Raw 보기 모드 토글"""
        try:
            if self.text_browser is None or self.toggle_button is None:
                return

            self.raw_mode = not self.raw_mode

            if self.raw_mode:
                # Raw 모드: 원본 텍스트 표시
                self.toggle_button.setText("🎨")
                self.toggle_button.setToolTip("Markdown 전환")

                self.text_browser.setPlainText(self.message)

                font_size = self.ui_config.get("font_size", 14)
                self.text_browser.setStyleSheet(
                    f"""
                    QTextBrowser {{
                        background-color: transparent;
                        border: none;
                        padding: 0;
                        margin: 0;
                        font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
                        font-size: {font_size}px;
                        color: white;
                        line-height: 1.4;
                    }}
                """
                )
            else:
                # Markdown 모드: 마크다운 렌더링 표시
                self.toggle_button.setText("📝")
                self.toggle_button.setToolTip("RAW 전환")

                self._apply_content_to_browser(self.text_browser)
                self.text_browser.setStyleSheet(self._get_user_stylesheet())

            # 높이 재조정
            self._adjust_height()

            # 위젯 업데이트 강제 실행
            self.text_browser.update()
            self.update()

        except Exception as exception:
            logger.error("Failed to toggle raw mode: %s", str(exception))

    def copy_content(self) -> None:
        """현재 내용을 클립보드에 복사"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.message)
            logger.debug(
                f"User content copied to clipboard: {len(self.message)} characters"
            )

            # 복사 완료 시 버튼 아이콘을 잠시 변경해서 피드백 제공
            if self.copy_button:
                original_text = self.copy_button.text()
                self.copy_button.setText("✅")
                # 1초 후 원래 아이콘으로 복원
                import threading

                def restore_icon():
                    import time

                    time.sleep(1)
                    if self.copy_button:
                        self.copy_button.setText(original_text)

                threading.Thread(target=restore_icon, daemon=True).start()

        except Exception as exception:
            logger.error("Failed to copy content: %s", str(exception))

    def _apply_content_to_browser(self, text_browser: QTextBrowser) -> None:
        """텍스트 브라우저에 마크다운 렌더링된 콘텐츠 적용"""
        try:
            # Markdown을 HTML로 변환
            html_content: str = markdown.markdown(
                self.message,
                extensions=[
                    "markdown.extensions.tables",  # 표 지원
                    "markdown.extensions.fenced_code",  # 코드 블록 지원
                    "markdown.extensions.codehilite",  # 코드 하이라이트
                    "markdown.extensions.nl2br",  # 줄바꿈 지원
                ],
            )

            # 표에 인라인 스타일 적용 (QTextBrowser 호환성)
            md = MarkdownManager()
            html_content = md.apply_table_styles(html_content)

            # HTML이 원본과 거의 동일하면 단순 텍스트로 처리
            simple_html = f"<p>{self.message.strip()}</p>"
            if html_content.strip() == simple_html:
                html_content = self.message.replace("\n", "<br>")

            # HTML 스타일링 추가
            font_family, font_size = self.get_font_config()

            styled_html: str = f"""
            <div style="font-family: '{font_family}';
                        font-size: {font_size}px;
                        line-height: 1.6;
                        color: white;">
                {html_content}
            </div>
            """

            text_browser.setHtml(styled_html)

        except Exception as exception:
            logger.warning(
                "Markdown conversion failed, using plain text: %s", str(exception)
            )
            text_browser.setPlainText(self.message)

    def _get_user_stylesheet(self) -> str:
        """사용자 버블용 마크다운 스타일시트 반환"""
        font_family, font_size = self.get_font_config()
        code_font_size: int = max(font_size - 1, 12)

        return f"""
            QTextBrowser {{
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
                font-family: '{font_family}';
                font-size: {font_size}px;
                color: white;
                line-height: 1.6;
            }}
            QTextBrowser code {{
                background-color: rgba(255, 255, 255, 0.2);
                padding: 3px 6px;
                border-radius: 6px;
                font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
                font-size: {code_font_size}px;
                color: #F8FAFC;
            }}
            QTextBrowser pre {{
                background-color: rgba(0, 0, 0, 0.3);
                color: #F8FAFC;
                padding: 16px;
                border-radius: 12px;
                overflow-x: auto;
                font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
                font-size: {code_font_size}px;
                line-height: 1.4;
            }}
            QTextBrowser blockquote {{
                border-left: 4px solid rgba(255, 255, 255, 0.5);
                padding: 0 16px;
                margin: 16px 0;
                color: rgba(255, 255, 255, 0.8);
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 0 6px 6px 0;
            }}
            QTextBrowser h1, h2, h3, h4, h5, h6 {{
                color: white;
                margin: 24px 0 16px 0;
                font-weight: 600;
                line-height: 1.25;
                padding-bottom: 8px;
            }}
            QTextBrowser h1 {{
                font-size: 24px;
                border-bottom: 2px solid rgba(255, 255, 255, 0.3);
            }}
            QTextBrowser h2 {{
                font-size: 20px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.3);
            }}
            QTextBrowser h3 {{
                font-size: 18px;
            }}
            QTextBrowser a {{
                color: #93C5FD;
                text-decoration: none;
            }}
            QTextBrowser a:hover {{
                text-decoration: underline;
            }}
            QTextBrowser strong, QTextBrowser b {{
                font-weight: 600;
                color: white;
            }}
            QTextBrowser p {{
                margin: 0 0 16px 0;
            }}
            QTextBrowser ul, QTextBrowser ol {{
                margin: 0 0 16px 0;
                padding-left: 32px;
            }}
            QTextBrowser li {{
                margin: 4px 0;
                line-height: 1.5;
            }}
            QTextBrowser table {{
                border-collapse: collapse;
                width: 100%;
                margin: 16px 0;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                overflow: hidden;
            }}
            QTextBrowser th, td {{
                border: 1px solid rgba(255, 255, 255, 0.3);
                padding: 8px 13px;
                text-align: left;
                vertical-align: top;
            }}
            QTextBrowser th {{
                background-color: rgba(255, 255, 255, 0.2);
                font-weight: 600;
                color: white;
                border-bottom: 2px solid rgba(255, 255, 255, 0.4);
            }}
            QTextBrowser tr:nth-child(even) {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QTextBrowser tr:hover {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
        """

    def _adjust_height(self) -> None:
        """텍스트 브라우저 높이 조정"""
        try:
            if self.text_browser:
                max_width = self.get_max_width()
                self.text_browser.document().setTextWidth(max_width - 16)
                document_height = self.text_browser.document().size().height()
                new_height = int(document_height) + 10
                self.text_browser.setFixedHeight(new_height)
        except Exception as exception:
            logger.error("Failed to adjust height: %s", str(exception))
