from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)


class MCPUIBuilder:
    """MCP UI 생성을 담당하는 클래스"""

    def __init__(self):
        self.light_style = self._get_light_theme_style()

    def create_main_tab(self):
        """메인 MCP 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 상단 헤더 및 컨트롤
        header_layout, refresh_button = self._create_header_section()
        layout.addLayout(header_layout)

        # 메인 콘텐츠 영역 (Splitter로 분할)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)  # 패널이 완전히 접히지 않도록

        # 왼쪽: 서버 상태 패널
        server_panel, server_status_tree = self._create_server_status_panel()
        splitter.addWidget(server_panel)

        # 오른쪽: 도구 및 세부정보 패널
        tools_panel, tools_tree, tool_details_text, logs_text = self._create_tools_panel()
        splitter.addWidget(tools_panel)

        # 비율 설정을 더 유연하게 (35:65로 조정)
        splitter.setSizes([350, 650])
        splitter.setStretchFactor(0, 1)  # 왼쪽 패널 stretch factor
        splitter.setStretchFactor(1, 2)  # 오른쪽 패널이 더 많이 늘어나게
        layout.addWidget(splitter)

        # 하단 상태바
        status_layout, status_label, progress_bar = self._create_status_section()
        layout.addLayout(status_layout)

        # 밝은 테마 강제 적용
        self._apply_light_theme(tab)

        return {
            "tab": tab,
            "refresh_button": refresh_button,
            "server_status_tree": server_status_tree,
            "tools_tree": tools_tree,
            "tool_details_text": tool_details_text,
            "logs_text": logs_text,
            "status_label": status_label,
            "progress_bar": progress_bar,
        }

    def _create_header_section(self):
        """헤더 섹션 생성"""
        layout = QHBoxLayout()

        # 제목
        title_label = QLabel("MCP 서버 관리")
        title_label.setStyleSheet(
            """
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2563eb;
                margin-bottom: 5px;
            }
        """
        )
        layout.addWidget(title_label)

        layout.addStretch()

        # 새로고침 버튼
        refresh_button = QPushButton("새로고침")
        refresh_button.setStyleSheet(
            """
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """
        )
        layout.addWidget(refresh_button)

        return layout, refresh_button

    def _create_server_status_panel(self):
        """서버 상태 패널 생성"""
        group = QGroupBox("MCP 서버 상태")
        group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )

        layout = QVBoxLayout(group)

        # 서버 상태 트리
        server_status_tree = QTreeWidget()
        server_status_tree.setHeaderLabels(["서버명", "상태", "도구 수"])
        server_status_tree.setAlternatingRowColors(True)
        server_status_tree.setMinimumHeight(200)  # 최소 높이 설정
        server_status_tree.setStyleSheet(
            """
            QTreeWidget {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f3f4f6;
            }
            QTreeWidget::item:selected {
                background-color: #3b82f6;
                color: white;
            }
        """
        )

        layout.addWidget(server_status_tree)

        return group, server_status_tree

    def _create_tools_panel(self):
        """도구 패널 생성"""
        # 탭 위젯으로 도구 정보를 분류
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f9fafb;
                border: 1px solid #d1d5db;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #3b82f6;
                color: white;
            }
        """
        )

        # 도구 목록 탭
        tools_tab, tools_tree = self._create_tools_list_tab()
        tab_widget.addTab(tools_tab, "사용 가능한 도구")

        # 도구 세부정보 탭
        details_tab, tool_details_text = self._create_tool_details_tab()
        tab_widget.addTab(details_tab, "도구 세부정보")

        # 실시간 로그 탭
        logs_tab, logs_text = self._create_logs_tab()
        tab_widget.addTab(logs_tab, "실시간 로그")

        return tab_widget, tools_tree, tool_details_text, logs_text

    def _create_tools_list_tab(self):
        """도구 목록 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 도구 트리
        tools_tree = QTreeWidget()
        tools_tree.setHeaderLabels(["도구명", "설명", "서버"])
        tools_tree.setAlternatingRowColors(True)
        tools_tree.setRootIsDecorated(True)
        tools_tree.setMinimumHeight(300)  # 최소 높이 설정
        tools_tree.setStyleSheet(
            """
            QTreeWidget {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f3f4f6;
            }
            QTreeWidget::item:selected {
                background-color: #3b82f6;
                color: white;
            }
        """
        )

        layout.addWidget(tools_tree)

        return widget, tools_tree

    def _create_tool_details_tab(self):
        """도구 세부정보 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 세부정보 표시 영역
        tool_details_text = QTextEdit()
        tool_details_text.setReadOnly(True)
        tool_details_text.setMinimumHeight(300)  # 최소 높이 설정
        tool_details_text.setStyleSheet(
            """
            QTextEdit {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: #f9fafb;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 10px;
            }
        """
        )
        tool_details_text.setPlainText("도구를 선택하면 세부정보가 여기에 표시됩니다.")

        layout.addWidget(tool_details_text)

        return widget, tool_details_text

    def _create_logs_tab(self):
        """실시간 로그 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 로그 표시 영역
        logs_text = QTextEdit()
        logs_text.setReadOnly(True)
        logs_text.setMinimumHeight(300)  # 최소 높이 설정
        logs_text.setStyleSheet(
            """
            QTextEdit {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: #1e293b;
                color: #e2e8f0;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 10px;
            }
        """
        )
        logs_text.setPlainText("MCP 서버 활동 로그가 여기에 표시됩니다...")

        # 로그 지우기 버튼
        clear_button = QPushButton("로그 지우기")
        clear_button.setStyleSheet(
            """
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """
        )
        clear_button.clicked.connect(logs_text.clear)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(clear_button)

        layout.addWidget(logs_text)
        layout.addLayout(button_layout)

        return widget, logs_text

    def _create_status_section(self):
        """상태 섹션 생성"""
        layout = QHBoxLayout()

        # 상태 레이블
        status_label = QLabel("준비됨")
        status_label.setStyleSheet(
            """
            QLabel {
                color: #059669;
                font-weight: 500;
                padding: 4px 8px;
                background-color: #d1fae5;
                border-radius: 4px;
            }
        """
        )
        layout.addWidget(status_label)

        layout.addStretch()

        # 진행률 표시
        progress_bar = QProgressBar()
        progress_bar.setVisible(False)
        progress_bar.setMaximumWidth(200)
        progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """
        )
        layout.addWidget(progress_bar)

        return layout, status_label, progress_bar

    def _apply_light_theme(self, widget):
        """MCP 탭에 밝은 테마 강제 적용"""
        widget.setStyleSheet(self.light_style)

    def _get_light_theme_style(self):
        """밝은 테마 스타일 반환"""
        return """
            QWidget {
                background-color: #ffffff;
                color: #1f2937;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #ffffff;
                color: #1f2937;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #1f2937;
            }
            QTreeWidget {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: #ffffff;
                color: #1f2937;
                alternate-background-color: #f9fafb;
            }
            QTreeWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f3f4f6;
                color: #1f2937;
            }
            QTreeWidget::item:selected {
                background-color: #3b82f6;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #eff6ff;
                color: #1f2937;
            }
            QTabWidget::pane {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f9fafb;
                border: 1px solid #d1d5db;
                padding: 8px 16px;
                margin-right: 2px;
                color: #1f2937;
            }
            QTabBar::tab:selected {
                background-color: #3b82f6;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #e5e7eb;
                color: #1f2937;
            }
            QTextEdit {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: #ffffff;
                color: #1f2937;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
                color: #ffffff;
            }
            QLabel {
                color: #1f2937;
            }
            QProgressBar {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                text-align: center;
                background-color: #f3f4f6;
                color: #1f2937;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """
