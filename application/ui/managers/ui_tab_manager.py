"""UI 탭 관리 모듈"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFontComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .style_manager import StyleManager


class UITabManager:
    """UI 탭 관리 클래스"""

    def __init__(self, parent):
        self.parent = parent

    def create_ui_tab(self):
        """UI 설정 탭 생성"""
        tab = QWidget()

        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #F3F4F6;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #D1D5DB;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #9CA3AF;
            }
        """
        )

        # 스크롤 내용 위젯
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 폰트 설정 그룹박스
        font_group = QGroupBox("폰트 설정")
        font_group.setStyleSheet(StyleManager.get_group_box_style())

        font_layout = QFormLayout(font_group)
        font_layout.setContentsMargins(12, 12, 12, 12)
        font_layout.setSpacing(10)

        # 폰트 패밀리 선택
        self.parent.font_family_combo = QFontComboBox()
        self.parent.font_family_combo.setStyleSheet(self.get_font_combo_style())
        self.parent.font_family_combo.setMaximumHeight(32)
        self.parent.font_family_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        font_family_label = QLabel("🔤 폰트:")
        StyleManager.style_label(font_family_label)
        font_layout.addRow(font_family_label, self.parent.font_family_combo)

        # 폰트 크기 슬라이더
        font_size_container = QWidget()
        font_size_layout = QHBoxLayout(font_size_container)
        font_size_layout.setContentsMargins(0, 0, 0, 0)

        self.parent.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.parent.font_size_slider.setRange(10, 24)
        self.parent.font_size_slider.setValue(14)
        self.parent.font_size_slider.setStyleSheet(self.get_slider_style())

        self.parent.font_size_label = QLabel("14px")
        self.parent.font_size_label.setStyleSheet(self.get_size_label_style())
        self.parent.font_size_slider.valueChanged.connect(
            lambda v: self.parent.font_size_label.setText(f"{v}px")
        )

        font_size_layout.addWidget(self.parent.font_size_slider)
        font_size_layout.addWidget(self.parent.font_size_label)

        font_size_main_label = QLabel("📏 글꼴 크기:")
        StyleManager.style_label(font_size_main_label)
        font_layout.addRow(font_size_main_label, font_size_container)

        layout.addWidget(font_group)

        # 채팅 UI 설정 그룹박스
        chat_group = QGroupBox("채팅 UI 설정")
        chat_group.setStyleSheet(StyleManager.get_group_box_style())

        chat_layout = QFormLayout(chat_group)
        chat_layout.setContentsMargins(12, 12, 12, 12)
        chat_layout.setSpacing(10)

        # 채팅 버블 최대 너비
        bubble_width_container = QWidget()
        bubble_width_layout = QHBoxLayout(bubble_width_container)
        bubble_width_layout.setContentsMargins(0, 0, 0, 0)

        self.parent.bubble_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.parent.bubble_width_slider.setRange(400, 800)
        self.parent.bubble_width_slider.setValue(600)
        self.parent.bubble_width_slider.setStyleSheet(self.get_slider_style())

        self.parent.bubble_width_label = QLabel("600px")
        self.parent.bubble_width_label.setStyleSheet(self.get_size_label_style())
        self.parent.bubble_width_slider.valueChanged.connect(
            lambda v: self.parent.bubble_width_label.setText(f"{v}px")
        )

        bubble_width_layout.addWidget(self.parent.bubble_width_slider)
        bubble_width_layout.addWidget(self.parent.bubble_width_label)

        bubble_width_main_label = QLabel("💬 채팅 버블 최대 너비:")
        StyleManager.style_label(bubble_width_main_label)
        chat_layout.addRow(bubble_width_main_label, bubble_width_container)

        layout.addWidget(chat_group)

        # 미리보기
        preview_group = QGroupBox("미리보기")
        preview_group.setStyleSheet(StyleManager.get_group_box_style())

        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(12, 12, 12, 12)

        self.parent.preview_label = QLabel("이것은 설정된 폰트의 미리보기입니다.")
        self.parent.preview_label.setStyleSheet(
            """
            QLabel {
                color: #1F2937;
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 12px;
                font-size: 11px;
            }
        """
        )
        preview_layout.addWidget(self.parent.preview_label)

        layout.addWidget(preview_group)

        # 설정 변경 시 미리보기 업데이트
        self.parent.font_family_combo.currentFontChanged.connect(self.update_preview)
        self.parent.font_size_slider.valueChanged.connect(self.update_preview)

        layout.addStretch()

        scroll_area.setWidget(scroll_content)

        # 탭 레이아웃
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)

        return tab

    def update_preview(self):
        """미리보기 업데이트"""
        font_family = self.parent.font_family_combo.currentFont().family()
        font_size = self.parent.font_size_slider.value()

        self.parent.preview_label.setStyleSheet(
            f"""
            QLabel {{
                color: #1F2937;
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 12px;
                font-family: '{font_family}', -apple-system, BlinkMacSystemFont, 
                'Segoe UI', Roboto, sans-serif;
                font-size: {font_size}px;
            }}
        """
        )

    def get_font_combo_style(self):
        """폰트 콤보박스 스타일"""
        return """
            QFontComboBox {
                border: 2px solid #E5E7EB;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
                background-color: #FFFFFF;
                color: #1F2937;
                min-height: 16px;
                max-height: 24px;
            }
            QFontComboBox:focus {
                border-color: #2563EB;
                outline: none;
            }
            QFontComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: #E5E7EB;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #F9FAFB;
            }
            QFontComboBox::down-arrow {
                image: none;
                border: 2px solid #6B7280;
                width: 6px;
                height: 6px;
                border-top: none;
                border-right: none;
                transform: rotate(45deg);
            }
            QFontComboBox QAbstractItemView {
                border: 1px solid #E5E7EB;
                background-color: #FFFFFF;
                selection-background-color: #EBF4FF;
                selection-color: #1F2937;
                font-size: 11px;
                min-height: 200px;
                max-height: 300px;
                outline: none;
            }
            QFontComboBox QAbstractItemView::item {
                height: 24px;
                padding: 4px 8px;
                border: none;
                font-size: 11px;
            }
            QFontComboBox QAbstractItemView::item:selected {
                background-color: #EBF4FF;
                color: #1F2937;
            }
            QFontComboBox QAbstractItemView::item:hover {
                background-color: #F3F4F6;
            }
        """

    def get_slider_style(self):
        """슬라이더 스타일"""
        return """
            QSlider::groove:horizontal {
                border: 1px solid #E5E7EB;
                height: 6px;
                background-color: #F3F4F6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #2563EB;
                border: 1px solid #1D4ED8;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #1D4ED8;
            }
        """

    def get_size_label_style(self):
        """크기 라벨 스타일"""
        return """
            QLabel {
                color: #2563EB;
                font-weight: 600;
                font-size: 11px;
                min-width: 32px;
            }
        """
