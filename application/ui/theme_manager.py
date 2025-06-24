"""테마 및 스타일 관리 클래스"""

import logging
from enum import Enum
from typing import Dict, List, Optional

from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class ThemeType(Enum):
    """테마 타입 열거형."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # 시스템 설정에 따라 자동


class ThemeManager:
    """Qt 애플리케이션의 테마와 스타일을 관리하는 클래스."""

    def __init__(self) -> None:
        self.current_theme: ThemeType = ThemeType.LIGHT
        self._theme_styles: Dict[ThemeType, Dict[str, str]] = self._initialize_theme_styles()

    def _initialize_theme_styles(self) -> Dict[ThemeType, Dict[str, str]]:
        """테마별 스타일 정의 초기화."""
        return {
            ThemeType.LIGHT: {
                "style_name": "Fusion",
                "stylesheet": """
* {
  background-color: #FFFFFF;
  color: #1F2937;
}
"""
            },
            ThemeType.DARK: {
                "style_name": "Fusion",
                "stylesheet": """
* {
  background-color: #111827;
  color: #F9FAFB;
}
"""
            },
        }

    def set_theme(self, theme_type: ThemeType) -> None:
        """테마 설정."""
        self.current_theme = theme_type
        logger.info(f"테마가 {theme_type.value}로 변경되었습니다")

    def get_current_theme(self) -> ThemeType:
        """현재 테마 반환."""
        return self.current_theme

    def apply_theme_to_application(self, app: Optional[QApplication]) -> None:
        """QApplication에 현재 테마 적용."""
        if app is None:
            logger.warning("QApplication이 None입니다. 테마를 적용할 수 없습니다.")
            return

        try:
            cfg = self._theme_styles[self.current_theme]
            app.setStyle(cfg["style_name"])
            app.setStyleSheet(cfg["stylesheet"])
            logger.debug(f"{self.current_theme.value} 테마가 애플리케이션에 적용되었습니다")
        except KeyError:
            logger.error(f"정의되지 않은 테마입니다: {self.current_theme}")
        except Exception as exc:
            logger.error(f"테마 적용 중 오류 발생: {exc}")

    def get_theme_stylesheet(self, theme_type: Optional[ThemeType] = None) -> str:
        """특정 테마의 스타일시트 반환."""
        key = theme_type or self.current_theme
        try:
            return self._theme_styles[key]["stylesheet"]
        except KeyError:
            logger.error(f"정의되지 않은 테마입니다: {key}")
            return ""

    def get_available_themes(self) -> List[ThemeType]:
        """사용 가능한 테마 목록 반환."""
        return list(self._theme_styles.keys())

    def add_custom_theme(
        self, theme_type: ThemeType, style_name: str, stylesheet: str
    ) -> None:
        """사용자 정의 테마 추가."""
        self._theme_styles[theme_type] = {"style_name": style_name, "stylesheet": stylesheet}
        logger.info(f"사용자 정의 테마 '{theme_type.value}'가 추가되었습니다")

    def get_theme_colors(self, theme_type: Optional[ThemeType] = None) -> Dict[str, str]:
        """테마별 주요 색상 반환."""
        key = theme_type or self.current_theme
        schemes: Dict[ThemeType, Dict[str, str]] = {
            ThemeType.LIGHT: {
                "primary_bg": "#FFFFFF",
                "text_primary": "#1F2937",
            },
            ThemeType.DARK: {
                "primary_bg": "#111827",
                "text_primary": "#F9FAFB",
            },
        }
        return schemes.get(key, schemes[ThemeType.LIGHT])
