"""설정창 메인 모듈"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMainWindow, QWidget

from application.config.config_manager import ConfigManager
from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager
from application.ui.managers import (
    GitHubTabManager,
    LLMTabManager,
    MCPTabManager,
    SettingsManager,
    TaskTabManager,
    UISetupManager,
    UITabManager,
)


class SettingsWindow(QMainWindow):
    """설정창 (탭 구조 - LLM 설정, UI 설정) - DPI 스케일링 대응"""

    settings_changed = Signal()  # 설정 변경 시그널

    def __init__(
        self, 
        config_manager: ConfigManager, 
        parent: Optional[QWidget] = None, 
        mcp_manager: Optional[MCPManager] = None, 
        mcp_tool_manager: Optional[MCPToolManager] = None
    ) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("설정")

        # MCP 관리자 초기화 (전달받거나 새로 생성)
        self.mcp_manager = mcp_manager or MCPManager(config_manager)
        self.mcp_tool_manager = mcp_tool_manager

        # 관리자 클래스들 초기화
        self.ui_setup_manager = UISetupManager(self)
        self.llm_tab_manager = LLMTabManager(self)
        self.ui_tab_manager = UITabManager(self)
        self.mcp_tab_manager = MCPTabManager(
            self, self.mcp_manager, self.mcp_tool_manager
        )
        self.github_tab_manager = GitHubTabManager(self)
        self.task_tab_manager = TaskTabManager(self)
        self.settings_manager = SettingsManager(self)

        # DPI 스케일링에 대응한 크기 설정 (크기 조절 가능)
        self.setMinimumSize(800, 600)
        self.resize(900, 700)  # 더 큰 기본 크기로 설정
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # 윈도우 스타일 설정
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #FFFFFF;
                color: #1F2937;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 12px;
            }
        """
        )

        self.ui_setup_manager.setup_ui()
        self.settings_manager.load_current_settings()

    def on_tab_changed(self, index: int) -> None:
        """탭 변경 시 호출"""
        # LLM 탭(0)에서만 테스트 버튼 표시
        self.test_button.setVisible(index == 0)
