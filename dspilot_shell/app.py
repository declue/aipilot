#!/usr/bin/env python3
"""
DSPilot SSH Terminal Manager
PySide6 기반 SSH 터미널 관리 프로그램
"""
import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

# dspilot_core 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from dspilot_core.util.logger import setup_logger
from dspilot_shell.main_window import MainWindow


def setup_application_logging():
    """애플리케이션 로깅 설정"""
    try:
        # dspilot_core의 로깅 시스템 사용
        logger = setup_logger("dspilot_shell")
        if logger:
            logger.info("DSPilot SSH Terminal Manager 시작")
            return logger
        else:
            # 기본 로깅 설정
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            return logging.getLogger("dspilot_shell")
    except Exception as e:
        print(f"로깅 설정 실패: {e}")
        return logging.getLogger("dspilot_shell")


def check_dependencies():
    """필수 의존성 확인"""
    missing_deps = []
    
    try:
        import paramiko
    except ImportError:
        missing_deps.append("paramiko")
    
    try:
        from PySide6 import QtWidgets
    except ImportError:
        missing_deps.append("PySide6")
    
    return missing_deps


def main():
    """메인 함수"""
    # Qt 애플리케이션 생성
    app = QApplication(sys.argv)
    app.setApplicationName("DSPilot SSH Terminal Manager")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("DSPilot")
    
    # 로깅 설정
    logger = setup_application_logging()
    
    try:
        # 의존성 확인
        missing_deps = check_dependencies()
        if missing_deps:
            error_msg = f"다음 패키지가 설치되지 않았습니다: {', '.join(missing_deps)}\n\n"
            error_msg += "다음 명령어로 설치하세요:\n"
            error_msg += f"pip install {' '.join(missing_deps)}"
            
            QMessageBox.critical(None, "의존성 오류", error_msg)
            return 1
        
        # 메인 윈도우 생성 및 표시
        main_window = MainWindow()
        main_window.show()
        
        logger.info("애플리케이션 시작 완료")
        
        # 이벤트 루프 실행
        return app.exec()
        
    except Exception as e:
        logger.error(f"애플리케이션 시작 실패: {e}")
        QMessageBox.critical(
            None, 
            "시작 오류", 
            f"애플리케이션을 시작할 수 없습니다:\n{str(e)}"
        )
        return 1
    
    finally:
        logger.info("애플리케이션 종료")


if __name__ == "__main__":
    sys.exit(main())