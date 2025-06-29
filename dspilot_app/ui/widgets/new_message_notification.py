import logging

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from dspilot_core.util.logger import setup_logger

logger: logging.Logger = setup_logger("ui") or logging.getLogger("ui")


class NewMessageNotification(QFrame):
    """새 메시지 알림 위젯 - 메신저 앱 스타일"""

    # 시그널 정의
    scroll_to_bottom_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.hide()  # 기본적으로 숨김

    def setup_ui(self):
        """UI 설정"""
        self.setFixedSize(200, 40)
        self.setStyleSheet(
            """
            QFrame {
                background-color: rgba(59, 130, 246, 0.95);
                border: 1px solid #3B82F6;
                border-radius: 20px;
                padding: 0;
            }
            QFrame:hover {
                background-color: rgba(37, 99, 235, 0.95);
                border-color: #2563EB;
            }
        """
        )

        # 그림자 효과
        self.setGraphicsEffect(self._create_shadow_effect())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 아이콘
        icon_label = QLabel("💬")
        icon_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                font-size: 14px;
            }
        """
        )
        layout.addWidget(icon_label)

        # 텍스트
        text_label = QLabel("새 메시지")
        text_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                color: white;
                font-size: 12px;
                font-weight: 500;
            }
        """
        )
        layout.addWidget(text_label)

        layout.addStretch()

        # 닫기 버튼
        close_button = QPushButton("✕")
        close_button.setFixedSize(20, 20)
        close_button.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """
        )
        close_button.clicked.connect(self.hide)
        layout.addWidget(close_button)

        # 전체 위젯을 클릭 가능하게 만들기
        self.mousePressEvent = self._handle_click

    def _create_shadow_effect(self):
        """그림자 효과 생성"""
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QGraphicsDropShadowEffect

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 80))
        return shadow

    def _handle_click(self, event):
        """클릭 이벤트 처리"""
        if event.button() == Qt.MouseButton.LeftButton:
            logger.debug("새 메시지 알림 클릭됨 - 스크롤 요청")
            self.scroll_to_bottom_requested.emit()
            self.hide()

    def show_notification(self):
        """알림 표시"""
        logger.debug("새 메시지 알림 표시")
        self.show()

        # 자동 숨김 타이머 (10초 후)
        QTimer.singleShot(10000, self.hide)

    def position_on_parent(self):
        """부모 위젯 내에서 위치 조정"""
        if self.parent():
            parent_rect = self.parent().rect()
            # 우측 하단에서 약간 위쪽에 위치
            x = parent_rect.width() - self.width() - 20
            y = parent_rect.height() - self.height() - 80  # 입력창 위쪽
            self.move(x, y)
            logger.debug(f"알림 위치 조정: ({x}, {y})")
