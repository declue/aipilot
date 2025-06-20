from __future__ import annotations

"""application.ui.controllers

Application layer – UI 컨트롤러 및 오케스트레이션.

초기 단계에서는 `MainWindow` 를 재-익스포트하여 기존 코드와의 호환성을
유지합니다.
"""

from application.ui.main_window import MainWindow  # type: ignore

__all__: list[str] = [
    "MainWindow",
] 