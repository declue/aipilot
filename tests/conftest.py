import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 백그라운드 리소스 정리를 위한 자동 실행 픽스처
# 전체 테스트 세션 동안 활성화되어, 종료 시 남은 스레드나 QApplication 인스턴스를 종료합니다.

from application.config.libs.config_change_notifier import get_config_change_notifier

try:
    # PySide6 가 설치되지 않은 환경도 있으므로 동적 import 처리
    from PySide6.QtWidgets import QApplication  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – GUI 미지원 환경
    QApplication = None  # type: ignore


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

    # 2) QApplication 인스턴스가 남아있다면 종료
    if QApplication is not None:
        try:
            app = QApplication.instance()
            if app is not None:
                app.quit()
        except Exception:  # pragma: no cover – 정리 과정 예외 무시
            pass 