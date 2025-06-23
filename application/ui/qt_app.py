import logging
import os
import sys
from typing import Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from application.api.api_server import APIServer
from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager
from application.ui.tray_app import TrayApp
from application.util.logger import setup_logger

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
        main_app_instance: Any = None,  # 메인 App 클래스 인스턴스
    ):
        self.mcp_manager = mcp_manager
        self.mcp_tool_manager = mcp_tool_manager
        self.api_app_instance = api_app_instance
        self.main_app_instance = main_app_instance  # 메인 App 인스턴스 저장
        self.qt_app: QApplication | None = None
        self.tray_app: TrayApp | None = None

    def setup_qt_environment(self) -> None:
        """QT 환경 설정"""
        # DPI 스케일링 제어 설정 (간소화된 방법)
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
        os.environ["QT_SCALE_FACTOR"] = "1"
        os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"

    def set_application_icon(self) -> None:
        """애플리케이션 아이콘 설정"""
        if not self.qt_app:
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
                    self.qt_app.setWindowIcon(app_icon)

                    logger.debug("애플리케이션 아이콘을 logo.png로 설정 완료 (다중 크기)")
                else:
                    logger.warning("logo.png 파일을 아이콘으로 로드할 수 없습니다")
            else:
                logger.warning("logo.png 파일을 찾을 수 없습니다")
        except Exception as e:
            logger.error("애플리케이션 아이콘 설정 실패: %s", e)

    def create_qt_application(self) -> None:
        """QT 애플리케이션 생성 및 설정"""
        self.qt_app = QApplication(sys.argv)

        # 애플리케이션 정보 설정 (Windows 작업 표시줄용)
        self.qt_app.setApplicationName("DS Pilot")
        self.qt_app.setApplicationDisplayName("DS Pilot - AI 채팅 도구")
        self.qt_app.setApplicationVersion("1.0.0")
        self.qt_app.setOrganizationName("DS Pilot")
        self.qt_app.setOrganizationDomain("dspilot.ai")

        # 애플리케이션 아이콘 설정
        self.set_application_icon()

        # 더 안전한 DPI 제어 방법
        try:
            self.qt_app.setAttribute(Qt.ApplicationAttribute.AA_DisableHighDpiScaling, True)
        except AttributeError:
            # PySide6에서 지원하지 않는 경우 무시
            logger.debug("일부 DPI 설정을 사용할 수 없지만, 환경변수로 제어됩니다.")

        self.apply_qt_styles()

        # 윈도우에서는 트레이 아이콘만 켜져 있어도 앱이 살아있도록 설정해야 합니다.
        self.qt_app.setQuitOnLastWindowClosed(False)

    def apply_qt_styles(self) -> None:
        """QT 스타일 적용"""
        if not self.qt_app:
            return

        # 시스템 테마와 무관하게 라이트 테마 강제 적용
        self.qt_app.setStyle("Fusion")  # 일관된 스타일 사용
        self.qt_app.setStyleSheet(
            """
            * {
                background-color: #FFFFFF;
                color: #1F2937;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 12px;  /* 명시적으로 12px 고정 */
            }
            QMainWindow, QWidget {
                background-color: #FFFFFF;
                color: #1F2937;
            }
            QMenuBar {
                background-color: #F9FAFB;
                color: #1F2937;
                border-bottom: 1px solid #E5E7EB;
                font-size: 12px;
            }
            QMenuBar::item:selected {
                background-color: #E5E7EB;
            }
            QMenu {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #F3F4F6;
            }
        """
        )

    def create_tray_app(self) -> None:
        """트레이 애플리케이션 생성"""
        self.tray_app = TrayApp(
            self.qt_app, self.mcp_manager, self.mcp_tool_manager, self.main_app_instance
        )

    def run(self) -> int:
        """QT 애플리케이션 실행"""
        if not self.qt_app:
            raise RuntimeError("QT 애플리케이션이 초기화되지 않았습니다")

        logger.info("QT 애플리케이션 시작")
        logger.debug("DPI 스케일링 제어 - 시스템 글꼴 크기와 무관하게 일관된 UI 제공")

        return self.qt_app.exec()
