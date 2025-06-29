import logging
import os
import sys
from typing import Any, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from dspilot_app.api.api_server import APIServer
from dspilot_app.api.fastapi_thread import FastAPIThread
from dspilot_app.services.execution_manager import ExecutionManager
from dspilot_app.services.planning_service import PlanningService
from dspilot_app.ui.main_window import MainWindow
from dspilot_app.ui.theme_manager import ThemeManager, ThemeType
from dspilot_app.ui.tray_app import TrayApp
from dspilot_core.config.config_manager import ConfigManager
from dspilot_core.llm.mcp.mcp_manager import MCPManager
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager
from dspilot_core.util.logger import setup_logger

# Windows에서 작업 표시줄 아이콘을 위한 설정
if sys.platform == "win32":
    try:
        import ctypes

        # Windows AppUserModel ID 설정 (작업 표시줄 그룹화 방지)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("dspilot.ai.chat.1.0")
    except Exception:
        pass  # 실패해도 계속 진행

logger: logging.Logger = setup_logger("ui") or logging.getLogger("ui")


class QtApp:
    """QT 애플리케이션 관련 로직을 담당하는 클래스"""

    def __init__(
        self,
        mcp_manager: MCPManager,
        mcp_tool_manager: MCPToolManager,
        api_app_instance: APIServer,
        planning_service: PlanningService,
        execution_manager: ExecutionManager,
        main_app_instance: Any = None,  # 메인 App 클래스 인스턴스
    ):
        self.mcp_manager = mcp_manager
        self.mcp_tool_manager = mcp_tool_manager
        self.api_app_instance = api_app_instance
        self.planning_service = planning_service
        self.execution_manager = execution_manager
        self.main_app_instance = main_app_instance
        self.config_manager = ConfigManager()
        self.app: Optional[QApplication] = None
        self.main_window: Optional[MainWindow] = None
        self.tray_app: Optional[TrayApp] = None
        self.fastapi_thread: Optional[FastAPIThread] = None
        self.theme_manager = ThemeManager()

    def setup_qt_environment(self) -> None:
        """QT 환경 설정"""
        # DPI 스케일링 제어 설정 (간소화된 방법)
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
        os.environ["QT_SCALE_FACTOR"] = "1"
        os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"

    def set_application_icon(self) -> None:
        """애플리케이션 아이콘 설정"""
        if not self.app:
            return

        try:
            # logo.png 파일을 애플리케이션 아이콘으로 설정
            logo_path = "logo.png"
            if os.path.exists(logo_path):
                app_icon = QIcon(logo_path)
                if not app_icon.isNull():
                    # 다양한 크기의 아이콘 추가 (Windows 작업 표시줄 대응)
                    app_icon.addFile(logo_path, QSize(16, 16))
                    app_icon.addFile(logo_path, QSize(24, 24))
                    app_icon.addFile(logo_path, QSize(32, 32))
                    app_icon.addFile(logo_path, QSize(48, 48))
                    app_icon.addFile(logo_path, QSize(64, 64))
                    app_icon.addFile(logo_path, QSize(96, 96))
                    app_icon.addFile(logo_path, QSize(128, 128))
                    app_icon.addFile(logo_path, QSize(256, 256))

                    # 애플리케이션 전체 아이콘 설정
                    self.app.setWindowIcon(app_icon)

                    logger.debug("애플리케이션 아이콘을 logo.png로 설정 완료 (다중 크기)")
                else:
                    logger.warning("logo.png 파일을 아이콘으로 로드할 수 없습니다")
            else:
                logger.warning("logo.png 파일을 찾을 수 없습니다")
        except Exception as e:
            logger.error("애플리케이션 아이콘 설정 실패: %s", e)

    def create_qt_application(self) -> None:
        """QT 애플리케이션 생성 및 설정"""
        self.app = QApplication(sys.argv)

        # 애플리케이션 정보 설정 (Windows 작업 표시줄용)
        self.app.setApplicationName("DSPilot")
        self.app.setApplicationDisplayName("DS Pilot - AI 채팅 도구")
        self.app.setApplicationVersion("1.0.0")
        self.app.setOrganizationName("Clue")
        self.app.setOrganizationDomain("dspilot.ai")

        # 애플리케이션 아이콘 설정
        self.set_application_icon()

        # 더 안전한 DPI 제어 방법
        try:
            self.app.setAttribute(Qt.ApplicationAttribute.AA_DisableHighDpiScaling, True)
        except AttributeError:
            # PySide6에서 지원하지 않는 경우 무시
            logger.debug("일부 DPI 설정을 사용할 수 없지만, 환경변수로 제어됩니다.")

        # 테마 매니저를 통한 스타일 적용
        self.apply_theme()

        # 윈도우에서는 트레이 아이콘만 켜져 있어도 앱이 살아있도록 설정해야 합니다.
        self.app.setQuitOnLastWindowClosed(False)

        self.main_window = MainWindow(
            mcp_manager=self.mcp_manager,
            mcp_tool_manager=self.mcp_tool_manager,
            app_instance=self.main_app_instance,
            planning_service=self.planning_service,
            execution_manager=self.execution_manager,
        )
        self.main_window.set_app_reference(self)
        self.main_window.show()

        logger.info("QT 애플리케이션 생성 완료")
        self.apply_theme(self.theme_manager.get_current_theme())

    def apply_theme(self, theme_type: Optional[ThemeType] = None) -> None:
        """테마 적용"""
        if theme_type is None:
            theme_type = self.theme_manager.get_current_theme()
        
        self.theme_manager.set_theme(theme_type)
        self.theme_manager.apply_theme_to_application(self.app)

    def set_light_theme(self) -> None:
        """라이트 테마로 변경"""
        self.apply_theme(ThemeType.LIGHT)

    def set_dark_theme(self) -> None:
        """다크 테마로 변경"""
        self.apply_theme(ThemeType.DARK)

    def toggle_theme(self) -> None:
        """현재 테마를 토글 (라이트 ↔ 다크)"""
        current = self.theme_manager.get_current_theme()
        if current == ThemeType.LIGHT:
            self.set_dark_theme()
        else:
            self.set_light_theme()

    def get_current_theme(self) -> ThemeType:
        """현재 테마 반환"""
        return self.theme_manager.get_current_theme()

    def get_theme_colors(self) -> dict:
        """현재 테마의 색상 정보 반환"""
        return self.theme_manager.get_theme_colors()

    def get_theme_manager(self) -> ThemeManager:
        """테마 매니저 반환 (다른 컴포넌트에서 사용 가능)"""
        return self.theme_manager

    def create_tray_app(self) -> None:
        """트레이 애플리케이션 생성"""
        self.tray_app = TrayApp(
            self.app,
            self.mcp_manager,
            self.mcp_tool_manager,
            self.planning_service,
            self.execution_manager,
            self.main_app_instance,
            self.theme_manager,
        )

    def run(self) -> int:
        """QT 애플리케이션 실행"""
        if not self.app:
            raise RuntimeError("QT 애플리케이션이 초기화되지 않았습니다")

        logger.info("QT 애플리케이션 시작")
        logger.debug("DPI 스케일링 제어 - 시스템 글꼴 크기와 무관하게 일관된 UI 제공")

        return self.app.exec()
