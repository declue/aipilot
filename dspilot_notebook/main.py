#!/usr/bin/env python3
"""
DSPilot Notebook - Windows 11 스타일 메모장 애플리케이션
"""

import sys
from pathlib import Path

# dspilot_core 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication

from dspilot_notebook.app import NotebookApplication


def main():
    """메인 함수"""
    # Qt 애플리케이션 생성
    app = QApplication(sys.argv)
    app.setApplicationName("DSPilot Notebook")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("DSPilot")
    
    # 다크 테마 적용
    app.setStyle("Fusion")
    
    # 메인 윈도우 생성
    notebook_app = NotebookApplication()
    notebook_app.show()
    
    # 이벤트 루프 시작
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
