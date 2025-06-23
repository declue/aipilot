import logging
import re
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QFrame, QLayout, QTextBrowser

from application.util.logger import setup_logger

if TYPE_CHECKING:
    from application.ui.common.theme_manager import ThemeManager

logger: logging.Logger = setup_logger("ui") or logging.getLogger("ui")


# QFrame과 ABC의 메타클래스 충돌을 해결하기 위한 커스텀 메타클래스
# pylint: disable=inconsistent-mro
class QFrameABCMeta(type(QFrame), ABCMeta):  # type: ignore
    """QFrame과 ABC를 함께 사용하기 위한 메타클래스"""


# pylint: disable=invalid-metaclass
class ChatBubble(QFrame, metaclass=QFrameABCMeta):  # type: ignore
    """채팅 버블의 기본 클래스 (Presentation Layer)"""

    DEFAULT_FONT_FAMILY = (
        "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    )
    DEFAULT_FONT_SIZE = 14
    DEFAULT_CHAT_BUBBLE_MAX_WIDTH = 1000

    def __init__(
        self,
        message: str,
        ui_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QFrame] = None,
    ) -> None:
        super().__init__(parent)

        # 입력 유효성 검사
        if not isinstance(message, str):
            raise TypeError("message must be a string")
        if not message.strip():
            raise ValueError("message cannot be empty or whitespace only")

        if ui_config is not None and not isinstance(ui_config, dict):
            raise TypeError("ui_config must be a dictionary")

        self.message = message
        self.ui_config: Dict[str, Any] = ui_config or {
            "font_family": self.DEFAULT_FONT_FAMILY,
            "font_size": self.DEFAULT_FONT_SIZE,
            "chat_bubble_max_width": self.DEFAULT_CHAT_BUBBLE_MAX_WIDTH,
        }
        self.theme_manager: Optional["ThemeManager"] = None

        try:
            logger.debug(f"ChatBubble creating: message={message[:50]}...")
            self.setup_ui()
            # ChatBubble 자체는 너비 제한 없이 stretch되도록 함
            # 내부 버블 프레임들에서만 개별적으로 너비 제한
            logger.debug("ChatBubble initialized successfully")
        except Exception as exception:
            logger.error("Failed to initialize ChatBubble: %s", str(exception))
            raise

    @abstractmethod
    def setup_ui(self) -> None:
        """UI 레이아웃 설정 - 각 서브클래스에서 구현"""

    def get_font_config(self) -> tuple[str, int]:
        """폰트 설정을 반환"""
        font_family: str = self.ui_config.get("font_family", self.DEFAULT_FONT_FAMILY)
        font_size: int = self.ui_config.get("font_size", self.DEFAULT_FONT_SIZE)
        return font_family, font_size

    def get_max_width(self) -> int:
        """최대 너비 설정을 반환 - 윈도우 크기의 80%"""
        try:
            # QApplication을 통해 메인 윈도우 찾기
            app = QApplication.instance()
            if app is not None:
                # 모든 최상위 위젯 중에서 MainWindow 찾기
                for widget in app.topLevelWidgets():
                    if widget.isVisible() and hasattr(widget, 'objectName'):
                        # MainWindow나 QMainWindow인 경우
                        if 'MainWindow' in str(type(widget)) or hasattr(widget, 'centralWidget'):
                            window_width = widget.width()
                            if window_width > 100:  # 유효한 크기인지 확인
                                # 윈도우 크기의 80%로 설정
                                calculated_width = int(window_width * 0.80)
                                logger.info(
                                    f"[DEBUG] Main window width: {window_width}px, calculated 80% width: {calculated_width}px"
                                )
                                return calculated_width
                
                # MainWindow를 찾지 못한 경우, 화면 크기 사용
                screens = QGuiApplication.screens()
                if screens:
                    primary_screen = screens[0]  # 첫 번째 화면을 primary로 사용
                    screen_width = primary_screen.geometry().width()
                    # 화면 크기의 80%로 설정
                    calculated_width = int(screen_width * 0.80)
                    logger.info(
                        f"[DEBUG] Screen width: {screen_width}px, calculated 80% width: {calculated_width}px"
                    )
                    return calculated_width

            # 화면 정보를 가져올 수 없는 경우 기본값 사용
            logger.warning("Could not get screen/window information, using default width")
            # 화면 크기 기준 계산이 실패한 경우에만 설정값 사용
            config_max_width: int = int(
                self.ui_config.get(
                    "chat_bubble_max_width", self.DEFAULT_CHAT_BUBBLE_MAX_WIDTH
                )
            )
            return max(config_max_width, self.DEFAULT_CHAT_BUBBLE_MAX_WIDTH)

        except Exception as exception:
            logger.error("Failed to calculate max width: %s", str(exception))
            # 오류 발생 시 기본값 반환
            return self.DEFAULT_CHAT_BUBBLE_MAX_WIDTH

    def update_ui_config(self, new_ui_config: Dict[str, Any]) -> None:
        """UI 설정 업데이트"""
        if new_ui_config and isinstance(new_ui_config, dict):
            self.ui_config = new_ui_config

    def update_styles(self) -> None:
        """스타일 업데이트 - 기본 구현은 QTextBrowser 요소들의 스타일만 업데이트"""
        try:
            font_family, font_size = self.get_font_config()

            # 모든 QTextBrowser 위젯들을 찾아서 스타일 업데이트
            text_browsers = self.findChildren(QTextBrowser)
            for browser in text_browsers:
                current_style = browser.styleSheet()

                # 스타일시트에서 font-family와 font-size를 업데이트
                updated_style = self._update_font_in_stylesheet(
                    current_style, font_family, font_size
                )
                browser.setStyleSheet(updated_style)

                # 텍스트 브라우저 크기 재조정
                self._adjust_text_browser_size(browser)

        except Exception as exception:
            logger.error("Failed to update styles: %s", str(exception))

    def _update_font_in_stylesheet(
        self, stylesheet: str, font_family: str, font_size: int
    ) -> str:
        """스타일시트에서 폰트 설정을 업데이트"""

        # font-family 업데이트
        stylesheet = re.sub(
            r"font-family:\s*[^;]+;", f"font-family: '{font_family}';", stylesheet
        )

        # font-size 업데이트
        stylesheet = re.sub(
            r"font-size:\s*\d+px;", f"font-size: {font_size}px;", stylesheet
        )

        return stylesheet

    def _adjust_text_browser_size(self, browser: QTextBrowser) -> None:
        """텍스트 브라우저 크기를 내용에 맞게 조정"""
        try:
            max_width = self.get_max_width() - 16  # 패딩 고려
            browser.document().setTextWidth(max_width)
            document_height = browser.document().size().height()
            browser.setFixedHeight(int(document_height) + 5)
        except Exception as exception:
            logger.debug("Failed to adjust text browser size: %s", str(exception))

    def clear_layout(self) -> None:
        """현재 레이아웃의 모든 위젯을 제거"""
        layout = self.layout()
        if layout:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self.clear_child_layout(child.layout())

    def clear_child_layout(self, layout: QLayout) -> None:
        """자식 레이아웃의 모든 위젯을 재귀적으로 제거"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_child_layout(child.layout())

    def apply_theme(self, theme_manager: "ThemeManager") -> None:
        """테마 매니저를 설정하고 테마를 적용합니다."""
        try:
            self.theme_manager = theme_manager
            self.update_theme_styles()
            logger.debug(f"테마 적용 완료: {type(self).__name__}")
        except Exception as e:
            logger.error(f"테마 적용 실패 {type(self).__name__}: {e}")

    def update_theme_styles(self) -> None:
        """테마에 맞는 스타일을 적용합니다. 서브클래스에서 구현해야 합니다."""
        # 기본 구현: 기존 update_styles 호출
        self.update_styles()

    def get_theme_colors(self) -> Dict[str, str]:
        """현재 테마의 색상을 반환합니다."""
        if self.theme_manager:
            return self.theme_manager.get_theme_colors()
        else:
            # 기본 라이트 테마 색상 반환
            return {
                'background': '#FFFFFF',
                'text': '#1F2937',
                'surface': '#F8FAFC',
                'border': '#E5E7EB',
                'primary': '#2563EB',
                'primary_hover': '#1D4ED8',
                'success': '#10B981',
                'danger': '#EF4444'
            } 