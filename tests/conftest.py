import os
import sys
import threading
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Qt 관련 import 정리
try:
    # PySide6 가 설치되지 않은 환경도 있으므로 동적 import 처리
    from PySide6.QtCore import QThread, QThreadPool  # type: ignore
    from PySide6.QtWidgets import QApplication  # type: ignore
    QT_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover – GUI 미지원 환경
    QApplication = None  # type: ignore
    QThread = None  # type: ignore
    QThreadPool = None  # type: ignore
    QT_AVAILABLE = False

# 백그라운드 리소스 정리를 위한 자동 실행 픽스처
# 전체 테스트 세션 동안 활성화되어, 종료 시 남은 스레드나 QApplication 인스턴스를 종료합니다.

from application.config.libs.config_change_notifier import (
    cleanup_global_notifier,
    get_config_change_notifier,
    reset_global_notifier,
)


def _force_cleanup_threads():
    """남은 Observer 스레드를 강제로 정리"""
    import time

    # 현재 활성 스레드 확인
    active_threads = threading.active_count()
    
    # 잠시 대기
    time.sleep(0.05)  # 대기 시간 단축
    
    # Observer 관련 스레드 확인 및 정리
    for thread in threading.enumerate():
        if hasattr(thread, 'name') and ('watchdog' in thread.name.lower() or 'observer' in thread.name.lower()):
            if thread.is_alive() and thread != threading.current_thread():
                try:
                    # 데몬 스레드로 설정하여 강제 종료 가능하게 함
                    thread.daemon = True
                    # 스레드가 종료될 때까지 잠시 대기
                    if hasattr(thread, 'join'):
                        thread.join(timeout=0.1)
                except Exception:
                    pass
    
    # watchdog Observer 강제 정리
    try:
        # watchdog의 Observer 인스턴스들을 찾아서 정리
        import gc
        for obj in gc.get_objects():
            if hasattr(obj, '__class__') and 'Observer' in str(obj.__class__):
                try:
                    if hasattr(obj, 'stop') and hasattr(obj, 'is_alive'):
                        if obj.is_alive():
                            obj.stop()
                            if hasattr(obj, 'join'):
                                obj.join(timeout=0.1)
                except Exception:
                    pass
    except Exception:
        pass


def _cleanup_qt_threads():
    """Qt 스레드들을 안전하게 정리"""
    if not QT_AVAILABLE:
        return
        
    import time

    # QThreadPool 정리
    if QThreadPool is not None:
        try:
            pool = QThreadPool.globalInstance()
            if pool:
                pool.waitForDone(1000)  # 1초 대기
                pool.clear()
        except Exception:  # pragma: no cover
            pass
    
    # 활성 QThread 확인 및 정리
    active_threads = threading.enumerate()
    qt_threads = []
    
    for thread in active_threads:
        # QThread 인스턴스 확인
        if hasattr(thread, '__class__') and QThread is not None:
            try:
                if isinstance(thread, QThread) or 'QThread' in str(type(thread)):
                    qt_threads.append(thread)
            except Exception:  # pragma: no cover
                pass
    
    # QThread들을 안전하게 종료
    for qt_thread in qt_threads:
        try:
            if hasattr(qt_thread, 'quit') and hasattr(qt_thread, 'wait'):
                qt_thread.quit()
                qt_thread.wait(1000)  # 1초 대기
                
                # 여전히 실행 중이면 강제 종료
                if hasattr(qt_thread, 'isRunning') and qt_thread.isRunning():
                    if hasattr(qt_thread, 'terminate'):
                        qt_thread.terminate()
                        qt_thread.wait(500)  # 0.5초 대기
        except Exception:  # pragma: no cover
            pass
    
    # 약간의 추가 대기 시간
    time.sleep(0.05)


@pytest.fixture(autouse=True)
def _reset_global_config_notifier():
    """각 테스트 함수마다 전역 config notifier를 초기화합니다."""
    # 테스트 시작 전 초기화
    reset_global_notifier()
    
    yield
    
    # 테스트 완료 후 정리
    cleanup_global_notifier()
    
    # Qt 스레드 정리
    _cleanup_qt_threads()
    
    # 강제 스레드 정리
    _force_cleanup_threads()
    
    # 약간의 대기 시간으로 스레드 정리 보장
    import time
    time.sleep(0.01)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_resources_after_tests():
    """테스트 세션 종료 시 남아있는 리소스를 정리합니다."""
    # 테스트 실행 전 (yield 이전)에는 아무 것도 하지 않음
    yield

    # 1) ConfigChangeNotifier 내부 Observer 중지
    try:
        get_config_change_notifier().stop_all()
    except Exception:  # pragma: no cover – 정리 과정 예외 무시
        pass

    # 2) Qt 스레드 정리 (QApplication 정리 전에 실행)
    _cleanup_qt_threads()

    # 3) 강제 스레드 정리
    _force_cleanup_threads()

    # 4) QApplication 인스턴스가 남아있다면 종료
    if QT_AVAILABLE and QApplication is not None:
        try:
            app = QApplication.instance()
            if app is not None:
                app.quit()
                # 잠시 대기하여 앱이 완전히 종료되도록 함
                import time
                time.sleep(0.1)
        except Exception:  # pragma: no cover – 정리 과정 예외 무시
            pass 