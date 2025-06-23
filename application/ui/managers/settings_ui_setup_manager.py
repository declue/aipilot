from __future__ import annotations

from typing import Any, cast

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class UISetupManager:
    """UI 설정 관리 클래스"""

    def __init__(self, parent: QMainWindow):
        self.parent = cast(Any, parent)

    def setup_ui(self) -> None:
        """UI 설정"""
        central_widget = QWidget()
        self.parent.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 헤더
        self.setup_header(layout)

        # 탭 위젯
        self.setup_tabs(layout)

        # 버튼 영역
        self.setup_buttons(layout)

    def setup_header(self, layout: QVBoxLayout) -> None:
        """헤더 설정"""
        header_label = QLabel("⚙️ 설정")
        header_label.setStyleSheet(
            """
            QLabel {
                color: #111827;
                font-size: 18px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin-bottom: 8px;
            }
        """
        )
        layout.addWidget(header_label)

        desc_label = QLabel("DS Pilot의 LLM 연결 설정과 UI 설정을 구성하세요.")
        desc_label.setStyleSheet(
            """
            QLabel {
                color: #6B7280;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin-bottom: 12px;
            }
        """
        )
        layout.addWidget(desc_label)

    def setup_tabs(self, layout: QVBoxLayout) -> None:
        """탭 위젯 설정"""
        self.parent.tab_widget = QTabWidget()
        self.parent.tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                background-color: #FFFFFF;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #F9FAFB;
                color: #6B7280;
                border: 1px solid #E5E7EB;
                padding: 8px 16px;
                margin-right: 2px;
                font-weight: 500;
                font-size: 11px;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #2563EB;
                border-bottom: 1px solid #FFFFFF;
                font-weight: 600;
            }
            QTabBar::tab:hover {
                background-color: #F3F4F6;
                color: #374151;
            }
        """
        )

        # 탭 추가
        self.parent.llm_tab = self.parent.llm_tab_manager.create_llm_tab()
        self.parent.tab_widget.addTab(self.parent.llm_tab, "🤖 LLM 설정")

        self.parent.ui_tab = self.parent.ui_tab_manager.create_ui_tab()
        self.parent.tab_widget.addTab(self.parent.ui_tab, "🎨 UI 설정")

        self.parent.mcp_tab = self.parent.mcp_tab_manager.create_mcp_tab()
        self.parent.tab_widget.addTab(self.parent.mcp_tab, "🔧 MCP 설정")

        self.parent.github_tab = self.parent.github_tab_manager.create_github_tab()
        self.parent.tab_widget.addTab(self.parent.github_tab, "🐙 GitHub 설정")

        self.parent.task_tab = self.parent.task_tab_manager.create_task_tab()
        self.parent.tab_widget.addTab(self.parent.task_tab, "⏰ 작업 스케줄")

        layout.addWidget(self.parent.tab_widget)

    def setup_buttons(self, layout: QVBoxLayout) -> None:
        """버튼 영역 설정"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # 테스트 버튼 (LLM 탭에서만)
        self.parent.test_button = QPushButton("🧪 연결 테스트")
        self.parent.test_button.setStyleSheet(
            """
            QPushButton {
                background-color: #F59E0B;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #D97706;
            }
            QPushButton:pressed {
                background-color: #B45309;
            }
        """
        )
        self.parent.test_button.clicked.connect(self.parent.llm_tab_manager.test_connection)

        # 기본값 복원 버튼
        reset_button = QPushButton("🔄 기본값 복원")
        reset_button.setStyleSheet(
            """
            QPushButton {
                background-color: #9CA3AF;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #6B7280;
            }
            QPushButton:pressed {
                background-color: #4B5563;
            }
        """
        )
        reset_button.clicked.connect(self.parent.settings_manager.reset_to_defaults)

        # 취소 버튼
        cancel_button = QPushButton("취소")
        cancel_button.setStyleSheet(
            """
            QPushButton {
                background-color: #6B7280;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 8px 16px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
            QPushButton:pressed {
                background-color: #374151;
            }
        """
        )
        cancel_button.clicked.connect(self.parent.close)

        # 저장 버튼
        save_button = QPushButton("💾 저장")
        save_button.setStyleSheet(
            """
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 8px 16px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """
        )
        save_button.clicked.connect(self.parent.settings_manager.save_settings)

        # 탭 변경 시 테스트 버튼 표시/숨기기
        self.parent.tab_widget.currentChanged.connect(self.parent.on_tab_changed)

        button_layout.addWidget(self.parent.test_button)
        button_layout.addWidget(reset_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

    def update_theme(self) -> None:
        """테마 업데이트"""
        try:
            if hasattr(self.parent, "theme_manager"):
                colors = self.parent.theme_manager.get_theme_colors()

                # 헤더 라벨들 업데이트
                self._update_header_theme(colors)

                # 탭 위젯 테마 업데이트
                self._update_tab_widget_theme(colors)

                # 버튼들 테마 업데이트
                self._update_buttons_theme(colors)

        except Exception as e:
            print(f"설정창 테마 업데이트 실패: {e}")

    def _update_header_theme(self, colors: dict[str, str]) -> None:
        """헤더 영역 테마 업데이트"""
        # 헤더 라벨 스타일은 setup_header에서 직접 참조하는 위젯이 없으므로
        # 필요시 위젯 참조를 저장해서 업데이트

    def _update_tab_widget_theme(self, colors: dict[str, str]) -> None:
        """탭 위젯 테마 업데이트"""
        if hasattr(self.parent, "tab_widget"):
            self.parent.tab_widget.setStyleSheet(
                f"""
                QTabWidget::pane {{
                    border: 1px solid {colors['border']};
                    border-radius: 6px;
                    background-color: {colors['background']};
                }}
                QTabWidget::tab-bar {{
                    alignment: left;
                }}
                QTabBar::tab {{
                    background-color: {colors['surface']};
                    color: {colors['text_secondary']};
                    border: 1px solid {colors['border']};
                    padding: 8px 16px;
                    margin-right: 2px;
                    font-weight: 500;
                    font-size: 11px;
                    border-bottom: none;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                }}
                QTabBar::tab:selected {{
                    background-color: {colors['background']};
                    color: {colors['primary']};
                    border-bottom: 1px solid {colors['background']};
                    font-weight: 600;
                }}
                QTabBar::tab:hover {{
                    background-color: {colors['button_hover']};
                    color: {colors['text']};
                }}
            """
            )

    def _update_buttons_theme(self, colors: dict[str, str]) -> None:
        """버튼들 테마 업데이트"""
        try:
            # 테스트 버튼
            if hasattr(self.parent, "test_button"):
                self.parent.test_button.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {colors['warning']};
                        color: white;
                        border: none;
                        border-radius: 6px;
                        font-weight: 600;
                        font-size: 11px;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        padding: 8px 16px;
                        min-width: 100px;
                    }}
                    QPushButton:hover {{
                        background-color: {colors.get('warning_hover', colors['warning'])};
                    }}
                    QPushButton:pressed {{
                        background-color: {colors.get('warning_pressed', colors['warning'])};
                    }}
                """
                )
        except Exception as e:
            print(f"버튼 테마 업데이트 실패: {e}")
