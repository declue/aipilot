"""설정창 메인 모듈"""

import logging
from textwrap import dedent
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMainWindow, QPushButton, QWidget

from dspilot_app.ui.common.theme_manager import ThemeManager
from dspilot_app.ui.managers import (
    GitHubTabManager,
    LLMTabManager,
    MCPTabManager,
    SettingsManager,
    TaskTabManager,
    UISetupManager,
    UITabManager,
)
from dspilot_core.config.config_manager import ConfigManager
from dspilot_core.llm.mcp.mcp_manager import MCPManager
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager

logger = logging.getLogger(__name__)

class SettingsWindow(QMainWindow):
    """설정창 (탭 구조 - LLM 설정, UI 설정) - DPI 스케일링 대응"""

    settings_changed: Signal = Signal()  # 설정 변경 시그널
    test_button: QPushButton  # 설정 UISetupManager가 생성합니다.

    def __init__(
        self,
        config_manager: ConfigManager,
        parent: Optional[QWidget] = None,
        mcp_manager: Optional[MCPManager] = None,
        mcp_tool_manager: Optional[MCPToolManager] = None,
    ) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("설정")

        # MCP 관리자 초기화 (전달받거나 새로 생성)
        self.mcp_manager = mcp_manager or MCPManager(config_manager)
        # mcp_tool_manager는 항상 존재하도록 설정
        self.mcp_tool_manager: MCPToolManager = (
            mcp_tool_manager or MCPToolManager(self.mcp_manager, config_manager)
        )

        # 테마 매니저 초기화
        self.theme_manager = ThemeManager(config_manager)

        # 관리자 클래스들 초기화
        self.ui_setup_manager = UISetupManager(self)
        self.llm_tab_manager = LLMTabManager(self)
        self.ui_tab_manager = UITabManager(self)
        self.mcp_tab_manager = MCPTabManager(self, self.mcp_manager, self.mcp_tool_manager)
        self.github_tab_manager = GitHubTabManager(self)
        self.task_tab_manager = TaskTabManager(self)
        self.settings_manager = SettingsManager(self)

        # DPI 스케일링에 대응한 크기 설정 (크기 조절 가능)
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # 테마 적용
        self._apply_theme()

        # UI 구성 및 초기 설정 로드
        self.ui_setup_manager.setup_ui()
        self.settings_manager.load_current_settings()

    def on_tab_changed(self, index: int) -> None:
        """탭 변경 시 호출"""
        # LLM 탭(0)에서만 테스트 버튼 표시
        self.test_button.setVisible(index == 0)

    def _apply_theme(self) -> None:
        """현재 테마를 설정창에 적용합니다."""
        colors = self.theme_manager.get_theme_colors()
        stylesheet = dedent(f"""
            QMainWindow {{
                background-color: {colors['background']};
                color: {colors['text']};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                    Roboto, sans-serif;
                font-size: 12px;
            }}
        """)
        self.setStyleSheet(stylesheet)

    def update_theme(self) -> None:
        """테마 업데이트 - 메인 윈도우에서 호출됩니다."""
        self._apply_theme()
        self._update_all_tab_themes()
        self.ui_setup_manager.update_theme()

    def _update_all_tab_themes(self) -> None:
        """모든 탭 매니저들의 테마를 업데이트합니다."""
        try:
            if hasattr(self, "ui_tab_manager"):
                self.ui_tab_manager.update_theme()
            if hasattr(self, "llm_tab_manager"):
                self.llm_tab_manager.update_theme()
            if hasattr(self, "github_tab_manager"):
                self.github_tab_manager.update_theme()
            if hasattr(self, "mcp_tab_manager"):
                self.mcp_tab_manager.update_theme()
            if hasattr(self, "task_tab_manager"):
                self.task_tab_manager.update_theme()
        except Exception:
            logger.exception("탭 테마 업데이트 실패")
