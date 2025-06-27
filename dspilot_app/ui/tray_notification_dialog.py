from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class TrayNotificationDialog(QWidget):
    """트레이 아이콘 근처에 뜨는 커스텀 알림 창 (HTML 지원)"""

    def __init__(
        self,
        title="알림",
        message="메시지",
        html_message=None,
        notification_type="info",
        width=350,
        height=150,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # 창 크기 설정 (동적 크기 지원)
        self.setFixedSize(width, height)

        # 알림 타입별 색상 설정
        colors = {
            "info": {"border": "#0078d4", "button": "#0078d4"},
            "warning": {"border": "#ff8c00", "button": "#ff8c00"},
            "error": {"border": "#dc3545", "button": "#dc3545"},
            "confirm": {"border": "#28a745", "button": "#28a745"},
            "auto": {"border": "#6c757d", "button": "#6c757d"},
        }

        color_scheme = colors.get(notification_type, colors["info"])

        # 스타일링
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: #2b2b2b;
                border: 2px solid {color_scheme["border"]};
                border-radius: 8px;
                color: white;
            }}
            QLabel {{
                color: white;
                font-size: 12px;
                background: transparent;
                border: none;
            }}
            QTextBrowser {{
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 4px;
                color: white;
                font-size: 12px;
                padding: 5px;
            }}
            QPushButton {{
                background-color: {color_scheme["button"]};
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 11px;
                padding: 6px 16px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color_scheme["button"])};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color_scheme["button"], 0.3)};
            }}
        """
        )

        # 레이아웃 설정
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 제목 라벨 (타입별 이모지 추가)
        type_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "confirm": "✅",
            "auto": "📢",
        }

        title_text = f"{type_emoji.get(notification_type, '📢')} {title}"
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title_label)

        # 메시지 영역 (HTML 지원)
        if html_message:
            # HTML 메시지가 있으면 QTextBrowser 사용
            self.message_browser = QTextBrowser()
            self.message_browser.setHtml(html_message)
            self.message_browser.setOpenExternalLinks(True)  # 외부 링크 열기 허용

            # 스크롤바 스타일링
            self.message_browser.setStyleSheet(
                self.message_browser.styleSheet()
                + """
                QScrollBar:vertical {
                    background-color: #444444;
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background-color: #666666;
                    border-radius: 4px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #888888;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """
            )

            layout.addWidget(self.message_browser)
        else:
            # 일반 텍스트 메시지
            message_label = QLabel(message)
            message_label.setWordWrap(True)
            layout.addWidget(message_label)

        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 확인 버튼
        ok_button = QPushButton("확인")
        ok_button.clicked.connect(self.close)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

        # 트레이 근처 위치로 이동
        self.move_to_tray_area()

    def _darken_color(self, hex_color: str, factor: float = 0.2) -> str:
        """색상을 어둡게 만드는 헬퍼 함수"""
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        darker_rgb = tuple(int(c * (1 - factor)) for c in rgb)
        return f"#{darker_rgb[0]:02x}{darker_rgb[1]:02x}{darker_rgb[2]:02x}"

    def move_to_tray_area(self):
        """트레이 영역 근처로 창 이동"""
        # 기본 화면 정보 가져오기
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # 화면 우측 하단에 위치 (트레이 영역 근처)
        pos_x = screen_geometry.right() - self.width() - 20
        pos_y = screen_geometry.bottom() - self.height() - 50

        self.move(pos_x, pos_y)

    def show_notification(self):
        """알림 창 표시"""
        self.show()
        self.raise_()
        self.activateWindow()

    def set_html_content(self, html_content: str):
        """HTML 컨텐츠를 설정하는 메서드"""
        if hasattr(self, "message_browser"):
            self.message_browser.setHtml(html_content)
        else:
            # 기존 메시지 위젯을 HTML 브라우저로 교체
            layout = self.layout()

            # 기존 메시지 라벨 찾아서 제거
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, QLabel) and not widget.text().startswith(
                        ("ℹ️", "⚠️", "❌", "✅", "📢")
                    ):
                        layout.removeWidget(widget)
                        widget.deleteLater()
                        break

            # HTML 브라우저 생성 및 추가
            self.message_browser = QTextBrowser()
            self.message_browser.setHtml(html_content)
            self.message_browser.setOpenExternalLinks(True)

            # 스크롤바 스타일링
            self.message_browser.setStyleSheet(
                """
                QTextBrowser {
                    background-color: #333333;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    color: white;
                    font-size: 12px;
                    padding: 5px;
                }
                QScrollBar:vertical {
                    background-color: #444444;
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background-color: #666666;
                    border-radius: 4px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #888888;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                """
            )

            # 버튼 레이아웃 앞에 추가
            from typing import cast

            vbox_layout = cast(QVBoxLayout, layout)
            vbox_layout.insertWidget(vbox_layout.count() - 1, self.message_browser)
