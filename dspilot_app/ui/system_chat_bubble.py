import logging

import markdown
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

from dspilot_app.ui.chat_bubble import ChatBubble
from dspilot_app.util.logger import setup_logger

logger: logging.Logger = setup_logger("ui") or logging.getLogger("ui")


class SystemChatBubble(ChatBubble):
    """시스템 메시지 채팅 버블"""

    AVATAR_ICON = "⚙️"
    AVATAR_SIZE = 40

    toggle_button: QPushButton
    copy_button: QPushButton
    text_browser: QTextBrowser

    def __init__(
        self,
        message: str,
        ui_config=None,
        is_html: bool = False,
        parent=None,
    ) -> None:
        self.is_html = is_html
        # Raw 모드 관련 초기화
        self.raw_mode = False
        super().__init__(message, ui_config, parent)

    def setup_ui(self) -> None:
        """시스템 메시지 UI 레이아웃 설정 - AIChatBubble과 동일한 배치"""
        try:
            self.setContentsMargins(0, 0, 0, 0)
            layout: QHBoxLayout = QHBoxLayout(self)

            # 시스템 메시지 (좌측 정렬) - AIChatBubble과 동일한 스타일
            logger.debug("Setting up SYSTEM bubble")
            layout.setContentsMargins(8, 16, 8, 16)  # 좌우 여백을 8px로 최소화
            layout.setSpacing(16)
            self.setup_system_bubble(layout)
            # 우측에 stretch 추가 (버블이 좌측에 붙도록)
            layout.addStretch()

        except Exception as exception:
            logger.error("Failed to setup UI layout: %s", str(exception))
            raise RuntimeError("UI setup failed") from exception

    def setup_system_bubble(self, layout: QHBoxLayout) -> None:
        """시스템 메시지 버블 설정 - AIChatBubble과 동일한 구조"""
        try:
            # 시스템 아바타
            avatar: QLabel = QLabel(self.AVATAR_ICON)
            avatar.setFixedSize(self.AVATAR_SIZE, self.AVATAR_SIZE)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(
                """
                QLabel {
                    background-color: #F59E0B;
                    border-radius: 20px;
                    font-size: 18px;
                    color: white;
                    font-weight: bold;
                }
            """
            )
            layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)

            # 메시지 버블 컨테이너
            bubble_container: QFrame = QFrame()
            bubble_container_layout: QVBoxLayout = QVBoxLayout(bubble_container)
            bubble_container_layout.setContentsMargins(0, 0, 0, 0)
            bubble_container_layout.setSpacing(0)  # 간격 제거

            # 메시지 버블
            message_bubble_frame: QFrame = QFrame()
            max_width: int = self.get_max_width()
            message_bubble_frame.setMaximumWidth(max_width)
            message_bubble_frame.setStyleSheet(
                """
                QFrame {
                    background-color: #FEF3C7;
                    border: 1px solid #F59E0B;
                    border-radius: 20px;
                    padding: 0;
                    margin: 0;
                }
            """
            )

            bubble_layout: QVBoxLayout = QVBoxLayout(message_bubble_frame)
            bubble_layout.setContentsMargins(12, 16, 12, 16)
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
                    background-color: #F3F4F6;
                    color: #92400E;
                    border: 1px solid #D97706;
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #E5E7EB;
                    border-color: #B45309;
                    color: #78350F;
                }
                QPushButton:pressed {
                    background-color: #D1D5DB;
                    border-color: #92400E;
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
                    background-color: #F3F4F6;
                    color: #92400E;
                    border: 1px solid #D97706;
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #E5E7EB;
                    border-color: #B45309;
                    color: #78350F;
                }
                QPushButton:pressed {
                    background-color: #D1D5DB;
                    border-color: #92400E;
                }
            """
            )
            self.copy_button.clicked.connect(self.copy_content)

            # 버튼들을 컨테이너에 추가 (약간의 간격을 두고)
            button_container_layout.addWidget(self.copy_button)
            button_container_layout.addSpacing(4)  # 버튼 사이 간격
            button_container_layout.addWidget(self.toggle_button)
            bubble_layout.addWidget(button_container)

            # 텍스트 브라우저
            self.text_browser: QTextBrowser = QTextBrowser()
            self.text_browser.setMaximumWidth(max_width - 16)

            # HTML 또는 Markdown 처리
            if self.is_html:
                # HTML 메시지인 경우 직접 사용
                html_content = self.message
            else:
                # Markdown을 HTML로 변환
                try:
                    html_content = markdown.markdown(
                        self.message,
                        extensions=["codehilite", "fenced_code", "tables", "toc"],
                    )
                except Exception as exception:
                    logger.warning(
                        "Markdown conversion failed, using plain text: %s",
                        str(exception),
                    )
                    html_content = self.message.replace("\n", "<br>")

            font_family, font_size = self.get_font_config()

            styled_html = f"""
            <div style="
                color: #92400E;
                line-height: 1.6;
                font-family: '{font_family}';
                font-size: {font_size}px;
            ">
                {html_content}
            </div>
            """

            self.text_browser.setHtml(styled_html)
            self.text_browser.setStyleSheet(
                f"""
                QTextBrowser {{
                    background-color: transparent;
                    border: none;
                    font-size: {font_size}px;
                    font-family: '{font_family}';
                    color: #92400E;
                    padding: 0;
                    margin: 0;
                    line-height: 1.6;
                }}
            """
            )

            self.text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.text_browser.setOpenExternalLinks(True)
            self.text_browser.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

            # 동적 높이 조정
            self.text_browser.document().documentLayout().documentSizeChanged.connect(
                lambda: self.adjust_browser_height(self.text_browser)
            )

            bubble_layout.addWidget(self.text_browser)

            # 즉시 높이 조정 (초기 설정)
            self.adjust_browser_height(self.text_browser)

            # 버블을 컨테이너에 추가
            bubble_container_layout.addWidget(message_bubble_frame)
            layout.addWidget(bubble_container, 1)

            logger.debug("System bubble setup completed successfully")

        except Exception as exception:
            logger.error("Failed to setup system bubble: %s", str(exception))
            raise RuntimeError("System bubble setup failed") from exception

    def adjust_browser_height(self, text_browser: QTextBrowser) -> None:
        """텍스트 브라우저 높이를 내용에 맞게 조정 - AIChatBubble과 동일"""
        try:
            if text_browser and text_browser.document():
                # 문서 높이 계산
                document_height = text_browser.document().size().height()
                # 최소 높이 보장 및 여백 추가
                adjusted_height = max(int(document_height) + 10, 30)
                text_browser.setFixedHeight(adjusted_height)
                logger.debug(f"Browser height adjusted to: {adjusted_height}px")
        except Exception as exception:
            logger.error("Failed to adjust browser height: %s", str(exception))

    def update_styles(self) -> None:
        """스타일 업데이트 - 시스템 버블 전용"""
        try:
            font_family, font_size = self.get_font_config()
            max_width = self.get_max_width()

            logger.debug(
                f"시스템 버블 스타일 업데이트: 폰트={font_family}, 크기={font_size}px, 최대너비={max_width}px"
            )

            # 텍스트 브라우저 업데이트
            if hasattr(self, "text_browser") and self.text_browser:
                # HTML 또는 Markdown 처리
                if self.is_html:
                    # HTML 메시지인 경우 직접 사용
                    html_content = self.message
                else:
                    # Markdown을 HTML로 변환
                    try:
                        html_content = markdown.markdown(
                            self.message,
                            extensions=["codehilite", "fenced_code", "tables", "toc"],
                        )
                    except Exception as exception:
                        logger.warning(
                            "Markdown conversion failed, using plain text: %s",
                            str(exception),
                        )
                    html_content = self.message.replace("\n", "<br>")

                styled_html = f"""
                <div style="
                    color: #92400E;
                    line-height: 1.6;
                    font-family: '{font_family}';
                    font-size: {font_size}px;
                ">
                    {html_content}
                </div>
                """

                self.text_browser.setHtml(styled_html)
                self.text_browser.setStyleSheet(
                    f"""
                    QTextBrowser {{
                        background-color: transparent;
                        border: none;
                        font-size: {font_size}px;
                        font-family: '{font_family}';
                        color: #92400E;
                        padding: 0;
                        margin: 0;
                        line-height: 1.6;
                    }}
                """
                )

                # 크기 재조정
                self.text_browser.setMaximumWidth(max_width - 16)
                self.text_browser.document().setTextWidth(max_width - 16)
                self.text_browser.document().adjustSize()
                self.adjust_browser_height(self.text_browser)

                logger.debug("시스템 버블 텍스트 브라우저 크기 조정 완료")

            # 버블 프레임들 크기 업데이트
            bubble_frames = self.findChildren(QFrame)
            for frame in bubble_frames:
                if frame.styleSheet() and (
                    "background-color: #FEF3C7" in frame.styleSheet()
                    or "border: 1px solid #F59E0B" in frame.styleSheet()
                ):
                    frame.setMaximumWidth(max_width)
                    logger.debug(f"시스템 버블 프레임 최대 너비 설정: {max_width}px")

            # 부모 레이아웃에 업데이트 알림
            self.updateGeometry()
            self.update()

        except Exception as exception:
            logger.error("Failed to update system bubble styles: %s", str(exception))

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
                        color: #92400E;
                        line-height: 1.4;
                    }}
                """
                )
            else:
                # Markdown 모드: HTML 렌더링 표시
                self.toggle_button.setText("📝")
                self.toggle_button.setToolTip("RAW 전환")

                # HTML 또는 Markdown 처리
                if self.is_html:
                    # HTML 메시지인 경우 직접 사용
                    html_content = self.message
                else:
                    # Markdown을 HTML로 변환
                    try:
                        html_content = markdown.markdown(
                            self.message,
                            extensions=["codehilite", "fenced_code", "tables", "toc"],
                        )
                    except Exception as exception:
                        logger.warning(
                            "Markdown conversion failed, using plain text: %s",
                            str(exception),
                        )
                        html_content = self.message.replace("\n", "<br>")

                font_family, font_size = self.get_font_config()

                styled_html = f"""
                <div style="
                    color: #92400E;
                    line-height: 1.6;
                    font-family: '{font_family}';
                    font-size: {font_size}px;
                ">
                    {html_content}
                </div>
                """

                self.text_browser.setHtml(styled_html)
                self.text_browser.setStyleSheet(
                    f"""
                    QTextBrowser {{
                        background-color: transparent;
                        border: none;
                        font-size: {font_size}px;
                        font-family: '{font_family}';
                        color: #92400E;
                        padding: 0;
                        margin: 0;
                        line-height: 1.6;
                    }}
                """
                )

            # 높이 재조정
            self.adjust_browser_height(self.text_browser)

            # 위젯 업데이트 강제 실행
            self.text_browser.update()
            self.update()

        except Exception as exception:
            logger.error("Failed to toggle raw mode: %s", str(exception))

    def copy_content(self) -> None:
        """현재 모드에 따라 내용을 클립보드에 복사"""
        try:
            clipboard = QApplication.clipboard()

            if self.raw_mode:
                # Raw 모드: 원본 텍스트 복사
                clipboard.setText(self.message)
                logger.debug(f"Raw content copied to clipboard: {len(self.message)} characters")
            else:
                # Markdown 모드: 렌더링된 마크다운 텍스트 복사
                clipboard.setText(self.message)
                logger.debug(
                    f"Markdown content copied to clipboard: {len(self.message)} characters"
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
