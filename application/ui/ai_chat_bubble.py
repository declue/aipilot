import logging
import os
import re
from typing import Any, Dict, Optional

import markdown
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
                               QPushButton, QTextBrowser, QTextEdit,
                               QVBoxLayout)

from application.ui.chat_bubble import ChatBubble
from application.util.logger import setup_logger
from application.util.markdown_manager import MarkdownManager

logger: logging.Logger = setup_logger("ai_chat_bubble") or logging.getLogger(
    "ai_chat_bubble"
)


class AIChatBubble(ChatBubble):
    """AI 응답 채팅 버블"""

    AVATAR_ICON = "🤖"
    AVATAR_SIZE = 40
    is_streaming: bool = False
    streaming_content: str = ""
    original_message: str = ""
    original_content: str = ""

    def __init__(
        self,
        message: str,
        ui_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QFrame] = None,
        avatar_icon: Optional[str] = None,
        avatar_image_path: Optional[str] = None,
    ) -> None:
        # 속성 초기화
        self.raw_mode = False
        self.is_streaming = False
        self.streaming_content = ""
        self.original_message = message
        self.toggle_button: Optional[QPushButton] = None
        self.copy_button: Optional[QPushButton] = None
        self.text_browser: Optional[QTextBrowser] = None
        self.used_tools: list = []
        self.tools_container: Optional[QFrame] = None
        self.avatar_icon = avatar_icon or self.AVATAR_ICON
        self.avatar_image_path = avatar_image_path
        self.is_reasoning_model = False
        self.reasoning_content = ""
        self.final_answer = ""

        super().__init__(message, ui_config, parent)

    def setup_ui(self) -> None:
        """AI 응답 UI 레이아웃 설정"""
        try:
            self.setContentsMargins(0, 0, 0, 0)
            layout: QHBoxLayout = QHBoxLayout(self)

            # AI 응답 (좌측 정렬) - ChatGPT 스타일로 완전히 좌측에 붙음
            logger.debug("Setting up AI bubble - should have Raw button")
            layout.setContentsMargins(8, 16, 8, 16)  # 좌우 여백을 8px로 최소화
            layout.setSpacing(16)
            self.setup_ai_bubble(layout)
            # 우측에 stretch 추가 (버블이 좌측에 붙도록)
            layout.addStretch()

        except Exception as exception:
            logger.error("Failed to setup UI layout: %s", str(exception))
            raise RuntimeError("UI setup failed") from exception

    def setup_ai_bubble(self, layout: QHBoxLayout) -> None:
        try:
            # 필요한 Qt 모듈들을 미리 import
            from PySide6.QtCore import Qt
            from PySide6.QtGui import (QBitmap, QBrush, QPainter, QPainterPath,
                                       QPen, QPixmap)

            # AI 아바타
            avatar: QLabel = QLabel()
            avatar.setFixedSize(
                self.AVATAR_SIZE, self.AVATAR_SIZE
            )  # 일관된 아바타 크기
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 아바타 이미지 또는 아이콘 설정
            if self.avatar_image_path:
                # 이미지 파일을 사용하는 경우
                
                logger.debug(f"GitHub 아이콘 로드 시도: {self.avatar_image_path}")
                
                pixmap = QPixmap(self.avatar_image_path)
                if not pixmap.isNull():
                    logger.debug(f"GitHub 아이콘 로드 성공: {pixmap.width()}x{pixmap.height()}")
                    
                    # 이미지를 정사각형으로 만들고 크기 조정
                    scaled_pixmap = pixmap.scaled(
                        self.AVATAR_SIZE, self.AVATAR_SIZE,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    
                    # 원형 이미지 생성
                    rounded_pixmap = QPixmap(self.AVATAR_SIZE, self.AVATAR_SIZE)
                    rounded_pixmap.fill(Qt.GlobalColor.transparent)
                    
                    try:
                        painter = QPainter(rounded_pixmap)
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        
                        # 원형 클리핑 경로 생성
                        path = QPainterPath()
                        path.addEllipse(0, 0, self.AVATAR_SIZE, self.AVATAR_SIZE)
                        painter.setClipPath(path)
                        
                        # 이미지 그리기
                        painter.drawPixmap(0, 0, self.AVATAR_SIZE, self.AVATAR_SIZE, scaled_pixmap)
                        painter.end()
                        
                        avatar.setPixmap(rounded_pixmap)
                        logger.debug("GitHub 아이콘 원형 이미지 생성 성공")
                        
                    except Exception as e:
                        logger.warning(f"원형 이미지 생성 실패, 기본 이미지 사용: {e}")
                        # 원형 이미지 생성 실패 시 원본 이미지 사용
                        avatar.setPixmap(scaled_pixmap)
                    
                    avatar.setStyleSheet(
                        """
                        QLabel {
                            background-color: #F8FAFC;
                            border: 2px solid #E2E8F0;
                            border-radius: 20px;
                            padding: 1px;
                        }
                    """
                    )
                    logger.debug("GitHub 아이콘 설정 완료")
                else:
                    # 이미지 로드 실패시 기본 아이콘 사용
                    logger.warning(f"GitHub 아이콘 로드 실패: {self.avatar_image_path}")
                    avatar.setText(self.avatar_icon)
                    avatar.setStyleSheet(
                        """
                        QLabel {
                            background-color: #24292F;
                            border-radius: 20px;
                            font-size: 18px;
                            color: white;
                            font-weight: bold;
                        }
                    """
                    )
            else:
                # 텍스트 아이콘을 사용하는 경우
                avatar.setText(self.avatar_icon)
                # GitHub 메시지인 경우 GitHub 색상 사용
                if self.avatar_icon == "🐱":
                    bg_color = "#24292F"  # GitHub 다크 색상
                else:
                    bg_color = "#10B981"  # 기본 AI 색상
                    
                avatar.setStyleSheet(
                    f"""
                    QLabel {{
                        background-color: {bg_color};
                        border-radius: 20px;
                        font-size: 18px;
                        color: white;
                        font-weight: bold;
                    }}
                """
                )
            
            layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)

            # 메시지 버블 컨테이너
            bubble_container: QFrame = QFrame()
            bubble_container_layout: QVBoxLayout = QVBoxLayout(
                bubble_container)
            bubble_container_layout.setContentsMargins(0, 0, 0, 0)
            bubble_container_layout.setSpacing(8)

            # 메시지 버블
            message_bubble_frame: QFrame = QFrame()
            max_width: int = self.get_max_width()
            logger.info(f"[DEBUG] AI bubble max_width set to: {max_width}px")

            # 버블 프레임만 최대 너비 설정 (컨테이너는 stretch)
            message_bubble_frame.setMaximumWidth(max_width)
            message_bubble_frame.setStyleSheet(
                """
                QFrame {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 20px;
                    padding: 0;
                    margin: 0;
                }
            """
            )

            bubble_layout: QVBoxLayout = QVBoxLayout(message_bubble_frame)
            bubble_layout.setContentsMargins(12, 16, 12, 16)  # 패딩 줄임
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
            button_container_layout.setContentsMargins(
                0, 8, 0, 0
            )  # 위쪽에만 약간의 여백
            button_container_layout.addStretch()

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
                    color: #1F2937;
                }
                QPushButton:pressed {
                    background-color: #D1D5DB;
                    border-color: #6B7280;
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
                    color: #1F2937;
                }
                QPushButton:pressed {
                    background-color: #D1D5DB;
                    border-color: #6B7280;
                }
            """
            )
            self.copy_button.clicked.connect(self.copy_content)

            # 처음에는 버튼들 숨김 (스트리밍 완료 후 표시)
            self.toggle_button.hide()
            self.copy_button.hide()

            # 버튼들을 컨테이너에 추가 (약간의 간격을 두고)
            button_container_layout.addWidget(self.copy_button)
            button_container_layout.addSpacing(4)  # 버튼 사이 간격
            button_container_layout.addWidget(self.toggle_button)
            bubble_layout.addWidget(button_container)

            # Markdown 렌더링
            text_browser: QTextBrowser = QTextBrowser()
            # 텍스트 브라우저도 최대 너비 설정 (패딩 최소화)
            text_browser.setMaximumWidth(
                max_width - 16
            )  # 패딩을 최소화하여 16px만 빼기

            try:
                # MarkdownManager를 사용하여 문법 하이라이트 적용
                md = MarkdownManager()
                html_content, _ = md.convert_with_syntax_highlighting(
                    self.message)

                # HTML이 원본과 거의 동일하면 단순 텍스트로 처리
                simple_html = f"<p>{self.message.strip()}</p>"
                if html_content.strip() == simple_html:
                    html_content = self.message.replace("\n", "<br>")

            except Exception as exception:
                logger.warning(
                    "Enhanced markdown conversion failed, using fallback: %s", str(
                        exception)
                )
                # 기본 마크다운 변환
                html_content = markdown.markdown(
                    self.message,
                    extensions=[
                        "markdown.extensions.tables",
                        "markdown.extensions.fenced_code",
                        "markdown.extensions.nl2br",
                    ],
                )
                md = MarkdownManager()
                html_content = md.apply_table_styles(html_content)

            # HTML 스타일링 추가 (설정값 사용)
            font_family, font_size = self.get_font_config()

            styled_html: str = f"""
            <div style="font-family: '{font_family}';
                        font-size: {font_size}px;
                        line-height: 1.6;
                        color: #1F2937;">
                {html_content}
            </div>
            """

            text_browser.setHtml(styled_html)

            # 분리된 메서드를 사용하여 마크다운 스타일시트 적용
            text_browser.setStyleSheet(self._get_markdown_stylesheet())

            text_browser.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            text_browser.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            text_browser.setOpenExternalLinks(True)
            # 워드랩 활성화하여 텍스트가 너비에 맞게 줄바꿈되도록 설정
            text_browser.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

            # 동적 높이 조정
            text_browser.document().documentLayout().documentSizeChanged.connect(
                lambda: self.adjust_browser_height(text_browser)
            )


            bubble_layout.addWidget(text_browser)

            # 즉시 높이 조정 (초기 설정)
            self.adjust_browser_height(text_browser)

            # 텍스트 브라우저를 인스턴스 변수로 저장 (토글용)
            self.text_browser = text_browser

            # 버블을 컨테이너에 추가
            bubble_container_layout.addWidget(message_bubble_frame)
            # 버블 컨테이너에 stretch factor 1을 주어 충분히 확장되도록 함
            layout.addWidget(bubble_container, 1)

            logger.debug("AI bubble setup completed successfully")

        except Exception as exception:
            logger.error("Failed to setup AI bubble: %s", str(exception))
            raise RuntimeError("AI bubble setup failed") from exception

    def adjust_browser_height(self, browser: QTextBrowser) -> None:
        """AI 채팅 버블 브라우저 높이 조정 - 재귀 방지"""
        try:
            # 현재 문서 크기로 직접 계산
            current_doc_size = browser.document().size()
            doc_height = int(current_doc_size.height())

            # 안전한 높이 계산
            if doc_height <= 0:
                doc_height = 50  # 최소 높이

            adjusted_height = doc_height + 30
            final_height = min(adjusted_height, 800)  # 최대 800px

            # 브라우저 높이만 설정 (다른 메서드 호출 없음)
            browser.setFixedHeight(final_height)

            logger.debug(
                "AI 버블 안전 높이 조정: %dpx → %dpx", doc_height, final_height
            )

        except Exception as exception:
            logger.error("AI 버블 높이 조정 실패 (안전 모드): %s", str(exception))
            browser.setFixedHeight(100)

    def _get_markdown_stylesheet(self) -> str:
        """마크다운 모드용 스타일시트 반환"""
        font_family, font_size = self.get_font_config()
        code_font_size: int = max(font_size - 1, 12)
        reasoning_font_size: int = max(font_size - 2, 10)  # 추론 영역용 작은 글씨

        return f"""
            QTextBrowser {{
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
                font-family: '{font_family}';
                font-size: {font_size}px;
            }}
            QTextBrowser code {{
                background-color: #F1F5F9;
                padding: 3px 6px;
                border-radius: 6px;
                font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
                font-size: {code_font_size}px;
                color: #475569;
            }}
            QTextBrowser pre {{
                background-color: #1E293B;
                color: #F8FAFC;
                padding: 16px;
                border-radius: 12px;
                overflow-x: auto;
                font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
                font-size: {code_font_size}px;
                line-height: 1.4;
            }}
            QTextBrowser blockquote {{
                border-left: 4px solid #D0D7DE;
                padding: 0 16px;
                margin: 16px 0;
                color: #656D76;
                background-color: #F6F8FA;
                border-radius: 0 6px 6px 0;
            }}
            QTextBrowser h1, h2, h3, h4, h5, h6 {{
                color: #24292F;
                margin: 24px 0 16px 0;
                font-weight: 600;
                line-height: 1.25;
                padding-bottom: 8px;
            }}
            QTextBrowser h1 {{
                font-size: 24px;
                border-bottom: 2px solid #D0D7DE;
            }}
            QTextBrowser h2 {{
                font-size: 20px;
                border-bottom: 1px solid #D0D7DE;
            }}
            QTextBrowser h3 {{
                font-size: 18px;
            }}
            QTextBrowser a {{
                color: #0969DA;
                text-decoration: none;
            }}
            QTextBrowser a:hover {{
                text-decoration: underline;
            }}
            QTextBrowser strong, QTextBrowser b {{
                font-weight: 600;
                color: #24292F;
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
                border: 1px solid #D0D7DE;
                border-radius: 6px;
                overflow: hidden;
            }}
            QTextBrowser th, td {{
                border: 1px solid #D0D7DE;
                padding: 8px 13px;
                text-align: left;
                vertical-align: top;
            }}
            QTextBrowser th {{
                background-color: #F6F8FA;
                font-weight: 600;
                color: #24292F;
                border-bottom: 2px solid #D0D7DE;
            }}
            QTextBrowser tr:nth-child(even) {{
                background-color: #F6F8FA;
            }}
            QTextBrowser tr:hover {{
                background-color: #F1F5F9;
            }}
            /* 추론 영역에 대한 스타일 추가 */
            QTextBrowser details {{
                margin-bottom: 16px;
                border: 1px solid #F59E0B;
                border-radius: 8px;
                padding: 12px;
                background-color: #FFFBEB;
            }}
            QTextBrowser summary {{
                cursor: pointer;
                font-size: {reasoning_font_size}px;
                color: #F59E0B;
                font-weight: 500;
                margin-bottom: 8px;
                user-select: none;
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            QTextBrowser details > div {{
                font-size: {reasoning_font_size}px;
                color: #6B7280;
                background-color: #F9FAFB;
                padding: 12px;
                border-radius: 6px;
                margin-top: 8px;
                border-left: 3px solid #F59E0B;
            }}
            /* 추론 영역 내부의 텍스트 요소들 */
            QTextBrowser details > div p {{
                font-size: {reasoning_font_size}px;
                color: #6B7280;
                margin: 8px 0;
                line-height: 1.4;
            }}
            QTextBrowser details > div h1,
            QTextBrowser details > div h2,
            QTextBrowser details > div h3,
            QTextBrowser details > div h4,
            QTextBrowser details > div h5,
            QTextBrowser details > div h6 {{
                font-size: {reasoning_font_size + 2}px;
                color: #4B5563;
                margin: 16px 0 8px 0;
                font-weight: 600;
            }}
            QTextBrowser details > div ul,
            QTextBrowser details > div ol {{
                font-size: {reasoning_font_size}px;
                color: #6B7280;
                margin: 8px 0;
            }}
            QTextBrowser details > div li {{
                font-size: {reasoning_font_size}px;
                color: #6B7280;
                margin: 2px 0;
                line-height: 1.4;
            }}
            QTextBrowser details > div code {{
                font-size: {max(reasoning_font_size - 1, 9)}px;
                color: #6B7280;
                background-color: #E5E7EB;
            }}
            QTextBrowser details > div pre {{
                font-size: {max(reasoning_font_size - 1, 9)}px;
                color: #F8FAFC;
                background-color: #374151;
            }}
        """

    def _apply_markdown_content(self) -> str:
        """마크다운 콘텐츠를 HTML로 변환하고 적용"""
        html_content = ""  # 변수 초기화
        try:
            original_message_length = len(
                self.original_message) if self.original_message else 0
            logger.debug(
                f"_apply_markdown_content 호출 - original_message 길이: {original_message_length}"
            )

            # original_message가 비어있으면 self.message 사용
            content_to_convert = self.original_message or self.message or ""

            if not content_to_convert:
                logger.warning("_apply_markdown_content - 변환할 콘텐츠가 없음")
                return "<div>콘텐츠가 없습니다.</div>"

            # MCP Tool 관련 메시지들을 더 잘 표시하기 위한 전처리
            enhanced_content = self._enhance_tool_messages(content_to_convert)

            # MarkdownManager를 사용하여 문법 하이라이트 적용
            md = MarkdownManager()
            html_content, _ = md.convert_with_syntax_highlighting(enhanced_content)

            # HTML이 원본과 거의 동일하면 단순 텍스트로 처리
            simple_html = f"<p>{enhanced_content.strip()}</p>"
            if html_content.strip() == simple_html:
                html_content = enhanced_content.replace("\n", "<br>")

        except Exception as exception:
            logger.warning(
                "Markdown conversion failed, using plain text: %s", str(
                    exception)
            )
            content_to_convert = self.original_message or self.message or ""
            html_content = content_to_convert.replace("\n", "<br>")

        # HTML 스타일링 추가
        font_family, font_size = self.get_font_config()
        styled_html: str = f"""
        <div style="font-family: '{font_family}';
                    font-size: {font_size}px;
                    line-height: 1.6;
                    color: #1F2937;">
            {html_content}
        </div>
        """

        logger.debug(
            f"_apply_markdown_content 완료 - HTML 길이: {len(styled_html)}")
        return styled_html

    def _enhance_tool_messages(self, content: str) -> str:
        """MCP Tool 관련 메시지들을 더 잘 표시하기 위해 마크다운 형식으로 개선"""
        try:
            lines = content.split('\n')
            enhanced_lines = []
            
            for line in lines:
                original_line = line
                
                # 도구 호출 메시지를 더 눈에 띄게 표시
                if '🔧 도구 호출' in line:
                    # 도구 호출을 강조 표시
                    enhanced_line = f"**{line.strip()}**"
                    enhanced_lines.append(enhanced_line)
                    
                elif '📝 인수:' in line:
                    # 도구 인수를 코드 블록으로 표시
                    args_part = line.split('📝 인수:')[-1].strip()
                    enhanced_line = f"   📝 **인수:** `{args_part}`"
                    enhanced_lines.append(enhanced_line)
                    
                elif '📊' in line and '결과:' in line:
                    # 도구 결과를 접이식으로 표시
                    parts = line.split('결과:')
                    if len(parts) >= 2:
                        tool_part = parts[0].strip()
                        result_part = parts[1].strip()
                        enhanced_line = f"**{tool_part}결과:**\n> {result_part}"
                        enhanced_lines.append(enhanced_line)
                    else:
                        enhanced_lines.append(original_line)
                        
                elif '✅' in line and ('실행 완료' in line or 'AI 모델 응답 완료' in line):
                    # 완료 메시지를 강조
                    enhanced_line = f"**{line.strip()}**"
                    enhanced_lines.append(enhanced_line)
                    
                elif '🏁 에이전트 실행 완료' in line:
                    # 최종 완료 메시지를 더 강조
                    enhanced_line = f"### {line.strip()}"
                    enhanced_lines.append(enhanced_line)
                    
                elif line.startswith('🤖') or line.startswith('🔗') or line.startswith('📡') or line.startswith('🚀'):
                    # 상태 메시지들을 약간 강조
                    enhanced_line = f"*{line.strip()}*"
                    enhanced_lines.append(enhanced_line)
                    
                elif '💭 사용자 요청 분석 중:' in line:
                    # 사용자 요청 분석을 인용구로 표시
                    request_part = line.split('💭 사용자 요청 분석 중:')[-1].strip()
                    enhanced_line = f"💭 **사용자 요청 분석 중:**\n> {request_part}"
                    enhanced_lines.append(enhanced_line)
                    
                elif '🤔 AI 분석:' in line:
                    # AI 분석 과정을 코드 블록으로 표시
                    analysis_part = line.split('🤔 AI 분석:')[-1].strip()
                    enhanced_line = f"🤔 **AI 분석:** `{analysis_part}`"
                    enhanced_lines.append(enhanced_line)
                    
                else:
                    # 기본 라인은 그대로 유지
                    enhanced_lines.append(original_line)
            
            return '\n'.join(enhanced_lines)
            
        except Exception as e:
            logger.warning(f"도구 메시지 개선 실패: {e}")
            return content

    def toggle_raw_mode(self) -> None:
        """Raw 보기 모드 토글"""
        try:
            if self.text_browser is None or self.toggle_button is None:
                return

            self.raw_mode = not self.raw_mode

            if self.raw_mode:
                # Raw 모드: 원본 텍스트 표시 + 도구 정보 숨김
                self.toggle_button.setText("🎨")
                self.toggle_button.setToolTip("Markdown 전환")

                # 디버깅: original_message 내용 확인
                logger.debug(
                    f"Raw 모드 - original_message 길이: {len(self.original_message) if self.original_message else 0}"
                )
                logger.debug(
                    f"Raw 모드 - original_message 내용: {self.original_message[:100] if self.original_message else 'None'}..."
                )

                # Raw 텍스트 준비
                raw_text = ""

                # 추론 모델인 경우 추론 과정과 최종 답변을 구분해서 표시
                if self.is_reasoning_model and self.reasoning_content:
                    raw_parts = []
                    if self.reasoning_content:
                        raw_parts.append(
                            f"<think>\n{self.reasoning_content}\n</think>")
                    if self.final_answer:
                        raw_parts.append(f"\n{self.final_answer}")
                    raw_text = "\n".join(raw_parts)
                    logger.debug(f"추론 모델 Raw 텍스트 구성: {len(raw_text)}자")
                elif self.original_message:
                    raw_text = self.original_message
                else:
                    # HTML에서 플레인 텍스트 추출 (더 정확한 방법)
                    current_plain_text = self.text_browser.toPlainText()
                    if (
                        current_plain_text and current_plain_text != "▌"
                    ):  # 커서 문자 제외
                        raw_text = current_plain_text
                        # original_message도 업데이트 (다음 번 토글을 위해)
                        self.original_message = current_plain_text
                        logger.debug(
                            f"original_message가 비어있음, 현재 텍스트로 업데이트: {len(raw_text)}자"
                        )
                    else:
                        # self.message도 확인
                        if self.message and self.message != "▌":
                            raw_text = self.message
                            self.original_message = self.message
                            logger.debug(f"self.message 사용: {len(raw_text)}자")

                self.text_browser.setPlainText(raw_text)

                # 도구 정보 컨테이너 숨김
                if hasattr(self, "tools_container") and self.tools_container:
                    self.tools_container.hide()

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
                        color: #1F2937;
                        line-height: 1.4;
                    }}
                """
                )
            else:
                # Markdown 모드: HTML 렌더링 표시 + 도구 정보 다시 표시
                self.toggle_button.setText("📝")
                self.toggle_button.setToolTip("RAW 전환")

                # 도구 정보 컨테이너 다시 표시
                if hasattr(self, "tools_container") and self.tools_container:
                    self.tools_container.show()

                # original_message가 없으면 현재 플레인 텍스트를 사용
                if not self.original_message:
                    current_text = self.text_browser.toPlainText()
                    if current_text:
                        self.original_message = current_text
                        logger.debug(
                            f"Markdown 모드 - original_message를 현재 텍스트로 설정: {len(current_text)}자"
                        )

                # 추론 모델인 경우 추론 콘텐츠 적용, 아니면 일반 마크다운 적용
                styled_html = self._apply_reasoning_content()
                self.text_browser.setHtml(styled_html)

                # 분리된 메서드를 사용하여 마크다운 스타일시트 적용
                self.text_browser.setStyleSheet(
                    self._get_markdown_stylesheet())
            # 높이 재조정
            self.adjust_browser_height(self.text_browser)

            # 위젯 업데이트 강제 실행
            self.text_browser.update()
            self.update()

        except Exception as exception:
            logger.error("Failed to toggle raw mode: %s", str(exception))

    def show_raw_button(self) -> None:
        """Raw 보기 버튼과 Copy 버튼 표시 (스트리밍 완료 후 호출)"""
        try:
            if self.toggle_button is not None:
                self.toggle_button.show()
                logger.debug("Raw button is now visible")
            if self.copy_button is not None:
                self.copy_button.show()
                logger.debug("Copy button is now visible")
        except Exception as exception:
            logger.error("Failed to show buttons: %s", str(exception))

    def copy_content(self) -> None:
        """현재 모드에 따라 내용을 클립보드에 복사"""
        try:
            clipboard = QApplication.clipboard()

            if self.raw_mode:
                # Raw 모드: 원본 텍스트 복사
                raw_text = ""

                # 추론 모델인 경우 추론 과정과 최종 답변을 구분해서 복사
                if self.is_reasoning_model and self.reasoning_content:
                    raw_parts = []
                    if self.reasoning_content:
                        raw_parts.append(
                            f"<think>\n{self.reasoning_content}\n</think>")
                    if self.final_answer:
                        raw_parts.append(f"\n{self.final_answer}")
                    raw_text = "\n".join(raw_parts)
                elif self.original_message:
                    raw_text = self.original_message
                else:
                    # 현재 표시된 플레인 텍스트 복사
                    raw_text = self.text_browser.toPlainText() if self.text_browser else ""

                clipboard.setText(raw_text)
                logger.debug(
                    f"Raw content copied to clipboard: {len(raw_text)} characters")
            else:
                # Markdown 모드: 렌더링된 마크다운 텍스트 복사
                markdown_text = self.original_message or self.message or ""
                clipboard.setText(markdown_text)
                logger.debug(
                    f"Markdown content copied to clipboard: {len(markdown_text)} characters")

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

    def set_used_tools(self, used_tools) -> None:
        """사용된 도구 정보 설정 및 UI 업데이트"""
        try:
            self.used_tools = used_tools
            if used_tools:
                self._update_tools_display()
                logger.debug(
                    f"Set used tools: {[tool.get('name', '') for tool in used_tools]}"
                )
        except Exception as exception:
            logger.error("Failed to set used tools: %s", str(exception))

    def _update_tools_display(self) -> None:
        """도구 정보 표시 UI 업데이트"""
        try:
            if not self.used_tools:
                return

            # 기존 도구 정보 컨테이너가 있다면 제거
            if hasattr(self, "tools_container") and self.tools_container:
                self.tools_container.setParent(None)
                self.tools_container.deleteLater()

            # 도구 정보 컨테이너 생성
            self.tools_container = QFrame()
            self.tools_container.setStyleSheet(
                """
                QFrame {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                    margin: 8px 0;
                    padding: 0;
                }
            """
            )

            tools_layout = QVBoxLayout(self.tools_container)
            tools_layout.setContentsMargins(12, 8, 12, 8)
            tools_layout.setSpacing(4)

            # 도구 사용 헤더
            header_label = QLabel("🔧 사용된 도구")
            header_label.setStyleSheet(
                f"""
                QLabel {{
                    color: #374151;
                    font-weight: 600;
                    font-size: {max(self.ui_config.get('font_size', 14) - 2, 11)}px;
                    font-family: '{self.ui_config.get('font_family', 'system-ui')}';
                    margin-bottom: 4px;
                    border: none;
                    background: transparent;
                }}
            """
            )
            tools_layout.addWidget(header_label)

            # 각 도구 정보 표시
            for tool in self.used_tools:
                tool_frame = self._create_tool_item(tool)
                tools_layout.addWidget(tool_frame)

            # 메시지 버블 레이아웃의 첫 번째 자식 찾기 (메시지 내용 앞에 삽입)
            bubble_frame = self.findChild(QFrame)
            if bubble_frame:
                bubble_layout = bubble_frame.layout()
                if bubble_layout and bubble_layout.count() > 0:
                    # QVBoxLayout으로 캐스팅해서 insertWidget 사용
                    if isinstance(bubble_layout, QVBoxLayout):
                        bubble_layout.insertWidget(0, self.tools_container)

        except Exception as exception:
            logger.error("Failed to update tools display: %s", str(exception))

    def _create_tool_item(self, tool: dict) -> QFrame:
        """개별 도구 정보 아이템 생성"""
        try:
            tool_frame = QFrame()
            tool_frame.setStyleSheet(
                """
                QFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #D1D5DB;
                    border-radius: 8px;
                    padding: 8px;
                    margin: 2px 0;
                }
                QFrame:hover {
                    background-color: #F9FAFB;
                    border-color: #9CA3AF;
                }
            """
            )

            tool_layout = QHBoxLayout(tool_frame)
            tool_layout.setContentsMargins(8, 6, 8, 6)
            tool_layout.setSpacing(8)

            # 도구 아이콘
            icon_label = QLabel("🛠️")
            icon_label.setStyleSheet(
                """
                QLabel {
                    font-size: 14px;
                    border: none;
                    background: transparent;
                }
            """
            )
            tool_layout.addWidget(icon_label)

            # 도구 정보
            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)

            # 도구 이름
            name_label = QLabel(tool.get("name", "알 수 없는 도구"))
            name_label.setStyleSheet(
                f"""
                QLabel {{
                    color: #1F2937;
                    font-weight: 600;
                    font-size: {max(self.ui_config.get('font_size', 14) - 2, 11)}px;
                    font-family: '{self.ui_config.get('font_family', 'system-ui')}';
                    border: none;
                    background: transparent;
                }}
            """
            )
            info_layout.addWidget(name_label)

            # 도구 설명 (있는 경우)
            description = tool.get("description", "")
            if description:
                desc_label = QLabel(description)
                desc_label.setStyleSheet(
                    f"""
                    QLabel {{
                        color: #6B7280;
                        font-size: {max(self.ui_config.get('font_size', 14) - 3, 10)}px;
                        font-family: '{self.ui_config.get('font_family', 'system-ui')}';
                        border: none;
                        background: transparent;
                    }}
                """
                )
                desc_label.setWordWrap(True)
                info_layout.addWidget(desc_label)

            tool_layout.addLayout(info_layout)
            tool_layout.addStretch()

            # 상태 표시
            status_label = QLabel("✅")
            status_label.setStyleSheet(
                """
                QLabel {
                    font-size: 12px;
                    border: none;
                    background: transparent;
                }
            """
            )
            tool_layout.addWidget(status_label)

            return tool_frame

        except Exception as exception:
            logger.error("Failed to create tool item: %s", str(exception))
            # 오류 시 기본 프레임 반환
            error_frame = QFrame()
            error_label = QLabel("도구 정보 표시 오류")
            error_layout = QHBoxLayout(error_frame)
            error_layout.addWidget(error_label)
            return error_frame

    def update_message_content(self, new_content: str) -> None:
        """메시지 내용 업데이트 (스트리밍 완료 후 사용)"""
        try:
            # 원본 메시지 업데이트
            self.original_message = new_content
            self.message = new_content

            logger.debug(f"메시지 내용 업데이트: {len(new_content)}자")

            # 현재 Raw 모드가 아닌 경우에만 UI 업데이트
            if not self.raw_mode and self.text_browser:
                styled_html = self._apply_reasoning_content()
                self.text_browser.setHtml(styled_html)
                self.adjust_browser_height(self.text_browser)

        except Exception as exception:
            logger.error("Failed to update message content: %s",
                         str(exception))

    def set_reasoning_info(
        self,
        is_reasoning_model: bool,
        reasoning_content: str = "",
        final_answer: str = "",
    ) -> None:
        """추론 관련 정보 설정 및 UI 업데이트"""
        try:
            self.is_reasoning_model = is_reasoning_model
            self.reasoning_content = reasoning_content
            self.final_answer = final_answer

            # 추론 정보가 있으면, original_message를 최종 답변으로 업데이트
            if is_reasoning_model and final_answer:
                self.original_message = final_answer

            logger.debug(
                f"추론 정보 설정 - is_reasoning: {is_reasoning_model}, "
                f"reasoning_content: {len(reasoning_content)}자, "
                f"final_answer: {len(final_answer)}자"
            )

            # UI 업데이트
            if not self.raw_mode and self.text_browser:
                styled_html = self._apply_reasoning_content()
                self.text_browser.setHtml(styled_html)
                self.adjust_browser_height(self.text_browser)

        except Exception as exception:
            logger.error("Failed to set reasoning info: %s", str(exception))

    def _apply_reasoning_content(self) -> str:
        """추론 콘텐츠를 적절한 HTML로 변환"""
        try:
            if not self.is_reasoning_model or not self.reasoning_content:
                # 추론 모델이 아니거나 추론 콘텐츠가 없으면 일반 마크다운 적용
                return self._apply_markdown_content()

            logger.debug(
                f"추론 콘텐츠 적용 - reasoning: {len(self.reasoning_content)}자, final: {len(self.final_answer)}자"
            )

            # 폰트 크기 설정
            font_family, font_size = self.get_font_config()
            reasoning_font_size = max(font_size - 2, 10)

            # 추론 콘텐츠를 마크다운으로 변환 (문법 하이라이트 적용)
            md = MarkdownManager()
            reasoning_html, _ = md.convert_with_syntax_highlighting(
                self.reasoning_content)

            # 추론 영역 HTML에 강제 스타일 적용
            reasoning_html = self._apply_reasoning_styles(
                reasoning_html, reasoning_font_size
            )

            # 최종 답변 HTML 생성 (문법 하이라이트 적용)
            final_html = ""
            if self.final_answer:
                final_html, _ = md.convert_with_syntax_highlighting(
                    self.final_answer)

            # HTML 구조 생성 (QTextBrowser 호환 구조, 인라인 스타일로 명시)

            styled_html = f"""
            <div style="font-family: '{font_family}'; font-size: {font_size}px; line-height: 1.6; color: #1F2937;">
                <div style="margin-bottom: 16px; border: 1px solid #F59E0B; border-radius: 8px; padding: 12px; background-color: #FFFBEB;">
                    <div style="font-size: {reasoning_font_size}px; color: #F59E0B; font-weight: 500; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 14px;">🤔</span>
                        <span>&lt;think&gt; 추론 과정</span>
                    </div>
                    <div style="font-size: {reasoning_font_size}px; color: #6B7280; background-color: #F9FAFB; padding: 12px; border-radius: 6px; border-left: 3px solid #F59E0B;">
                        <div style="font-size: {reasoning_font_size}px; color: #6B7280; line-height: 1.4;">
                            {reasoning_html}
                        </div>
                    </div>
                </div>
                {final_html}
            </div>
            """

            logger.debug(f"추론 HTML 생성 완료 - 길이: {len(styled_html)}")
            return styled_html

        except Exception as exception:
            logger.error("Failed to apply reasoning content: %s",
                         str(exception))
            # 오류 시 일반 마크다운 적용
            return self._apply_markdown_content()

    def _apply_reasoning_styles(self, html: str, reasoning_font_size: int) -> str:
        """추론 영역 HTML에 강제 스타일 적용"""
        try:
            # p 태그에 스타일 적용
            html = re.sub(
                r"<p>",
                f'<p style="font-size: {reasoning_font_size}px; color: #6B7280; margin: 8px 0; line-height: 1.4;">',
                html,
            )

            # h1-h6 태그에 스타일 적용
            for i in range(1, 7):
                html = re.sub(
                    f"<h{i}>",
                    f'<h{i} style="font-size: {reasoning_font_size + 2}px; color: #4B5563; margin: 16px 0 8px 0; font-weight: 600;">',
                    html,
                )

            # ul, ol 태그에 스타일 적용
            html = re.sub(
                r"<ul>",
                f'<ul style="font-size: {reasoning_font_size}px; color: #6B7280; margin: 8px 0;">',
                html,
            )
            html = re.sub(
                r"<ol>",
                f'<ol style="font-size: {reasoning_font_size}px; color: #6B7280; margin: 8px 0;">',
                html,
            )

            # li 태그에 스타일 적용
            html = re.sub(
                r"<li>",
                f'<li style="font-size: {reasoning_font_size}px; color: #6B7280; margin: 2px 0; line-height: 1.4;">',
                html,
            )

            # code 태그에 스타일 적용 (인라인)
            html = re.sub(
                r"<code>",
                f'<code style="font-size: {max(reasoning_font_size - 1, 9)}px; color: #6B7280; background-color: #E5E7EB; padding: 2px 4px; border-radius: 3px;">',
                html,
            )

            # pre 태그에 스타일 적용 (코드 블록)
            html = re.sub(
                r"<pre>",
                f'<pre style="font-size: {max(reasoning_font_size - 1, 9)}px; color: #F8FAFC; background-color: #374151; padding: 12px; border-radius: 6px; margin: 8px 0;">',
                html,
            )

            # strong, b 태그에 스타일 적용
            html = re.sub(
                r"<strong>",
                f'<strong style="font-size: {reasoning_font_size}px; color: #4B5563; font-weight: 600;">',
                html,
            )
            html = re.sub(
                r"<b>",
                f'<b style="font-size: {reasoning_font_size}px; color: #4B5563; font-weight: 600;">',
                html,
            )

            # em, i 태그에 스타일 적용
            html = re.sub(
                r"<em>",
                f'<em style="font-size: {reasoning_font_size}px; color: #6B7280; font-style: italic;">',
                html,
            )
            html = re.sub(
                r"<i>",
                f'<i style="font-size: {reasoning_font_size}px; color: #6B7280; font-style: italic;">',
                html,
            )

            return html

        except Exception as exception:
            logger.error("Failed to apply reasoning styles: %s",
                         str(exception))
            return html

    def update_styles(self) -> None:
        """스타일 업데이트 - AI 버블 전용"""
        try:
            font_family, font_size = self.get_font_config()
            max_width = self.get_max_width()

            logger.debug(
                f"AI 버블 스타일 업데이트 시작: 폰트={font_family}, 크기={font_size}px, 최대너비={max_width}px"
            )

            # 텍스트 브라우저 업데이트
            if hasattr(self, "text_browser") and self.text_browser:
                logger.debug("AI 버블 텍스트 브라우저 업데이트 중...")

                # 현재 모드에 따라 콘텐츠 다시 적용
                if self.raw_mode:
                    # Raw 모드인 경우 원본 텍스트로 설정
                    self.text_browser.setPlainText(self.original_message)
                    self.text_browser.setStyleSheet(
                        f"""
                        QTextBrowser {{
                            background-color: #F8FAFC;
                            border: none;
                            color: #374151;
                            font-size: {font_size}px;
                            font-family: 'Monaco', 'Menlo', monospace;
                            padding: 0;
                            margin: 0;
                            line-height: 1.5;
                        }}
                    """
                    )
                    logger.debug("Raw 모드 스타일 적용 완료")
                else:
                    # 마크다운 모드인 경우 HTML 다시 적용
                    logger.debug("마크다운 모드 HTML 재생성 중...")
                    styled_html = self._apply_reasoning_content()
                    self.text_browser.setHtml(styled_html)
                    self.text_browser.setStyleSheet(
                        self._get_markdown_stylesheet())
                    logger.debug("마크다운 모드 스타일 적용 완료")

                # 크기 재조정 - 간단하고 안전한 방식
                self.text_browser.setMaximumWidth(max_width - 16)
                self.text_browser.document().setTextWidth(max_width - 16)
                self.text_browser.document().adjustSize()

                # 높이를 직접 계산해서 설정 (무한 재귀 방지)
                doc_height = int(self.text_browser.document().size().height())
                adjusted_height = doc_height + 30
                max_height = min(adjusted_height, 800)
                self.text_browser.setFixedHeight(max_height)

                logger.debug(
                    f"AI 버블 직접 크기 조정: 문서높이={doc_height}, 설정높이={max_height}"
                )

                logger.debug("AI 버블 텍스트 브라우저 크기 조정 완료")

            # 버블 프레임들 크기 업데이트
            bubble_frames = self.findChildren(QFrame)
            frame_count = 0
            for frame in bubble_frames:
                if frame.styleSheet() and (
                    "background-color: #F8FAFC" in frame.styleSheet()
                    or "border: 1px solid #E2E8F0" in frame.styleSheet()
                ):
                    frame.setMaximumWidth(max_width)
                    frame_count += 1

            logger.debug(
                f"AI 버블 프레임 {frame_count}개 크기 업데이트 완료: {max_width}px"
            )

            # 부모 레이아웃에 업데이트 알림
            self.updateGeometry()
            self.update()

            logger.debug("AI 버블 스타일 업데이트 완료")

        except Exception as exception:
            logger.error("Failed to update AI bubble styles: %s",
                         str(exception))

    @staticmethod
    def create_github_bubble(
        message: str,
        ui_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QFrame] = None,
    ) -> "AIChatBubble":
        """GitHub webhook 메시지용 채팅 버블 생성"""
        # GitHub 아이콘 경로 설정 (여러 가능한 경로 시도)
        possible_paths = [
            # 현재 파일 기준으로 계산된 경로
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "application", "resources", "github-mark.png"
            ),
            # 작업 디렉토리 기준 경로들
            "application/resources/github-mark.png",
            "./application/resources/github-mark.png",
            os.path.join(os.getcwd(), "application", "resources", "github-mark.png"),
            # 절대 경로로 시도 (Windows 경로 정규화)
            os.path.abspath("application/resources/github-mark.png"),
        ]
        
        github_icon_path = None
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            logger.debug(f"GitHub 아이콘 경로 확인: {abs_path}")
            if os.path.exists(abs_path):
                github_icon_path = abs_path
                logger.info(f"GitHub 아이콘 파일 발견: {abs_path}")
                break
        
        if github_icon_path is None:
            # 현재 디렉토리 구조 확인용 로그
            current_dir = os.getcwd()
            logger.warning(f"현재 작업 디렉토리: {current_dir}")
            
            # application/resources 디렉토리 확인
            app_resources_dir = os.path.join(current_dir, "application", "resources")
            if os.path.exists(app_resources_dir):
                files_in_resources = os.listdir(app_resources_dir)
                logger.warning(f"application/resources 디렉토리 내용: {files_in_resources}")
            else:
                logger.warning(f"application/resources 디렉토리가 존재하지 않음: {app_resources_dir}")
            
            # 모든 경로에서 파일을 찾지 못하면 GitHub 이모지 사용
            logger.warning("GitHub 아이콘 파일을 찾을 수 없어 이모지를 사용합니다.")
            return AIChatBubble(
                message=message,
                ui_config=ui_config,
                parent=parent,
                avatar_icon="🐱",  # GitHub 고양이 이모지
            )
        
        logger.info(f"GitHub 아이콘으로 버블 생성: {github_icon_path}")
        return AIChatBubble(
            message=message,
            ui_config=ui_config,
            parent=parent,
            avatar_image_path=github_icon_path,
        )


