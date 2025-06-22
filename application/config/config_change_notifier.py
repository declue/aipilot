import logging
import os
import threading
import time
from typing import Callable, Dict, List, Optional, Set

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("config_change_notifier") or logging.getLogger(
    "config_change_notifier"
)

# 콜백 함수 타입 정의
ConfigChangeCallback = Callable[[str, str], None]  # (file_path, change_type)


class ConfigFileWatcher(FileSystemEventHandler):
    """설정 파일 변경 감지 핸들러"""
    
    def __init__(self, watched_files: Set[str], notifier: "ConfigChangeNotifier"):
        """
        Args:
            watched_files: 감시할 파일 경로들
            notifier: 알림을 처리할 ConfigChangeNotifier 인스턴스
        """
        self.watched_files = watched_files
        self.notifier = notifier
        self.last_modified_times: Dict[str, float] = {}
        
        # 초기 수정 시간 기록
        for file_path in watched_files:
            if os.path.exists(file_path):
                self.last_modified_times[file_path] = os.path.getmtime(file_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """파일 수정 이벤트 처리"""
        if event.is_directory:
            return
            
        file_path = os.path.abspath(event.src_path)
        
        if file_path in self.watched_files:
            # 중복 이벤트 방지를 위한 시간 체크
            current_time = time.time()
            last_time = self.last_modified_times.get(file_path, 0)
            
            if current_time - last_time > 0.1:  # 100ms 쿨다운
                self.last_modified_times[file_path] = current_time
                logger.debug(f"파일 변경 감지: {file_path}")
                self.notifier._notify_change(file_path, "modified") # pylint: disable=protected-access

    def on_created(self, event: FileSystemEvent) -> None:
        """파일 생성 이벤트 처리"""
        if event.is_directory:
            return
            
        file_path = os.path.abspath(event.src_path)
        
        if file_path in self.watched_files:
            logger.debug(f"파일 생성 감지: {file_path}")
            self.notifier._notify_change(file_path, "created") # pylint: disable=protected-access

    def on_deleted(self, event: FileSystemEvent) -> None:
        """파일 삭제 이벤트 처리"""
        if event.is_directory:
            return
            
        file_path = os.path.abspath(event.src_path)
        
        if file_path in self.watched_files:
            logger.debug(f"파일 삭제 감지: {file_path}")
            self.notifier._notify_change(file_path, "deleted") # pylint: disable=protected-access


class ConfigChangeNotifier:
    """설정 변경 알림 관리자"""
    
    def __init__(self):
        self._callbacks: Dict[str, List[ConfigChangeCallback]] = {}
        self._observer: Optional[Observer] = None # type: ignore
        self._watched_files: Set[str] = set()
        self._watched_directories: Set[str] = set()
        self._lock = threading.RLock()
        self._running = False

    def register_callback(self, file_path: str, callback: ConfigChangeCallback) -> None:
        """설정 변경 콜백 등록
        
        Args:
            file_path: 감시할 파일 경로
            callback: 변경 시 호출할 콜백 함수
        """
        with self._lock:
            abs_path = os.path.abspath(file_path)
            
            if abs_path not in self._callbacks:
                self._callbacks[abs_path] = []
            
            if callback not in self._callbacks[abs_path]:
                self._callbacks[abs_path].append(callback)
                logger.debug(f"콜백 등록: {abs_path}")
                
            # 파일 감시 시작
            self._start_watching_file(abs_path)

    def unregister_callback(self, file_path: str, callback: ConfigChangeCallback) -> None:
        """설정 변경 콜백 해제
        
        Args:
            file_path: 파일 경로
            callback: 해제할 콜백 함수
        """
        with self._lock:
            abs_path = os.path.abspath(file_path)
            
            if abs_path in self._callbacks:
                try:
                    self._callbacks[abs_path].remove(callback)
                    logger.debug(f"콜백 해제: {abs_path}")
                    
                    # 콜백이 없으면 파일 감시 중지
                    if not self._callbacks[abs_path]:
                        del self._callbacks[abs_path]
                        self._stop_watching_file(abs_path)
                except ValueError:
                    pass

    def unregister_all_callbacks(self, file_path: str) -> None:
        """특정 파일의 모든 콜백 해제
        
        Args:
            file_path: 파일 경로
        """
        with self._lock:
            abs_path = os.path.abspath(file_path)
            
            if abs_path in self._callbacks:
                del self._callbacks[abs_path]
                self._stop_watching_file(abs_path)
                logger.debug(f"모든 콜백 해제: {abs_path}")

    def _start_watching_file(self, file_path: str) -> None:
        """파일 감시 시작"""
        if file_path in self._watched_files:
            return
            
        directory = os.path.dirname(file_path)
        self._watched_files.add(file_path)
        
        if directory not in self._watched_directories:
            self._watched_directories.add(directory)
            
            if not self._running:
                self._start_observer()
            
            # 디렉토리 감시 추가
            if self._observer and os.path.exists(directory):
                self._observer.schedule(
                    ConfigFileWatcher(self._watched_files, self),
                    directory,
                    recursive=False
                )
                logger.debug(f"디렉토리 감시 시작: {directory}")

    def _stop_watching_file(self, file_path: str) -> None:
        """파일 감시 중지"""
        self._watched_files.discard(file_path)
        
        # 해당 디렉토리의 다른 파일들도 확인
        directory = os.path.dirname(file_path)
        has_other_files = any(
            os.path.dirname(f) == directory for f in self._watched_files
        )
        
        if not has_other_files:
            self._watched_directories.discard(directory)
            
        # 더 이상 감시할 파일이 없으면 observer 중지
        if not self._watched_files and self._running:
            self._stop_observer()

    def _start_observer(self) -> None:
        """Observer 시작"""
        if self._running:
            return
            
        try:
            self._observer = Observer()
            self._observer.start()
            self._running = True
            logger.debug("파일 감시 시작")
        except Exception as e:
            logger.error(f"Observer 시작 실패: {e}")

    def _stop_observer(self) -> None:
        """Observer 중지"""
        if not self._running or not self._observer:
            return
            
        try:
            self._observer.stop()
            self._observer.join(timeout=1.0)
            self._observer = None
            self._running = False
            logger.debug("파일 감시 중지")
        except Exception as e:
            logger.error(f"Observer 중지 실패: {e}")

    def _notify_change(self, file_path: str, change_type: str) -> None:
        """변경 사항을 등록된 콜백들에게 알림
        
        Args:
            file_path: 변경된 파일 경로
            change_type: 변경 타입 (modified, created, deleted)
        """
        with self._lock:
            callbacks = self._callbacks.get(file_path, [])
            
            for callback in callbacks.copy():  # 복사본으로 순회 (콜백 중 해제될 수 있음)
                try:
                    callback(file_path, change_type)
                except Exception as e:
                    logger.error(f"콜백 실행 중 오류 [{file_path}]: {e}")

    def stop_all(self) -> None:
        """모든 감시 중지"""
        with self._lock:
            self._callbacks.clear()
            self._watched_files.clear()
            self._watched_directories.clear()
            self._stop_observer()

    def __del__(self):
        """소멸자"""
        try:
            self.stop_all()
        except Exception:
            pass


# 전역 인스턴스
_global_notifier: Optional[ConfigChangeNotifier] = None


def get_config_change_notifier() -> ConfigChangeNotifier:
    """글로벌 ConfigChangeNotifier 인스턴스 반환"""
    global _global_notifier # pylint: disable=global-statement
    if _global_notifier is None:
        _global_notifier = ConfigChangeNotifier()
    return _global_notifier 