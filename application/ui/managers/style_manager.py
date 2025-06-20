class StyleManager:
    """스타일 관리 클래스"""

    @staticmethod
    def style_input(input_widget):
        """입력 위젯 스타일링 (QLineEdit와 QComboBox 지원)"""
        if input_widget.__class__.__name__ == "QComboBox":
            input_widget.setStyleSheet(
                """
                QComboBox {
                    border: 2px solid #E5E7EB;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 11px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #FFFFFF;
                    color: #1F2937;
                    min-height: 16px;
                }
                QComboBox:focus {
                    border-color: #2563EB;
                    outline: none;
                }
                QComboBox::drop-down {
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
                QComboBox::down-arrow {
                    image: none;
                    border: 2px solid #6B7280;
                    width: 6px;
                    height: 6px;
                    border-top: none;
                    border-right: none;
                    transform: rotate(45deg);
                }
                QComboBox QAbstractItemView {
                    border: 1px solid #E5E7EB;
                    background-color: #FFFFFF;
                    selection-background-color: #EBF4FF;
                    selection-color: #1F2937;
                    font-size: 11px;
                    outline: none;
                }
                QComboBox QAbstractItemView::item {
                    height: 24px;
                    padding: 4px 8px;
                    border: none;
                    font-size: 11px;
                }
                QComboBox QAbstractItemView::item:selected {
                    background-color: #EBF4FF;
                    color: #1F2937;
                }
                QComboBox QAbstractItemView::item:hover {
                    background-color: #F3F4F6;
                }
            """
            )
        else:
            input_widget.setStyleSheet(
                """
                QLineEdit {
                    border: 2px solid #E5E7EB;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 11px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #FFFFFF;
                    color: #1F2937;
                }
                QLineEdit:focus {
                    border-color: #2563EB;
                    outline: none;
                }
                QLineEdit::placeholder {
                    color: #9CA3AF;
                }
            """
            )
        input_widget.setMinimumHeight(32)

    @staticmethod
    def style_label(label):
        """라벨 스타일링"""
        label.setStyleSheet(
            """
            QLabel {
                color: #374151;
                font-size: 11px;
                font-weight: 500;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """
        )

    @staticmethod
    def style_button(button):
        """버튼 스타일 적용"""
        button.setStyleSheet(
            """
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
            QPushButton:disabled {
                background-color: #9CA3AF;
                color: #6B7280;
            }
        """
        )

    @staticmethod
    def get_group_box_style():
        """그룹박스 공통 스타일"""
        return """
            QGroupBox {
                font-weight: 600;
                font-size: 12px;
                color: #374151;
                border: 2px solid #E5E7EB;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 8px 0 8px;
                background-color: #FFFFFF;
            }
        """
