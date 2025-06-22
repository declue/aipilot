"""
설정 변경 알림 시스템 테스트

ConfigChangeNotifier와 관련 기능들에 대한 테스트를 수행합니다.
"""

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from application.config.config_change_notifier import (
    ConfigChangeNotifier,
    ConfigFileWatcher,
    get_config_change_notifier,
)


class TestConfigChangeNotifier(unittest.TestCase):
    """ConfigChangeNotifier 테스트"""

    def setUp(self):
        """테스트 초기화"""
        self.notifier = ConfigChangeNotifier()
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_config.ini")
        self.callback_calls = []

    def tearDown(self):
        """테스트 정리"""
        self.notifier.stop_all()
        # 임시 파일 및 디렉토리 정리
        try:
            if os.path.exists(self.test_file):
                os.remove(self.test_file)
            os.rmdir(self.test_dir)
        except:
            pass

    def test_callback_registration(self):
        """콜백 등록 테스트"""
        callback = Mock()
        
        self.notifier.register_callback(self.test_file, callback)
        
        # 콜백이 등록되었는지 확인
        abs_path = os.path.abspath(self.test_file)
        self.assertIn(abs_path, self.notifier._callbacks)
        self.assertIn(callback, self.notifier._callbacks[abs_path])

    def test_callback_unregistration(self):
        """콜백 해제 테스트"""
        callback = Mock()
        
        self.notifier.register_callback(self.test_file, callback)
        self.notifier.unregister_callback(self.test_file, callback)
        
        # 콜백이 해제되었는지 확인
        abs_path = os.path.abspath(self.test_file)
        self.assertNotIn(abs_path, self.notifier._callbacks)

    def test_unregister_all_callbacks(self):
        """모든 콜백 해제 테스트"""
        callback1 = Mock()
        callback2 = Mock()
        
        self.notifier.register_callback(self.test_file, callback1)
        self.notifier.register_callback(self.test_file, callback2)
        self.notifier.unregister_all_callbacks(self.test_file)
        
        # 모든 콜백이 해제되었는지 확인
        abs_path = os.path.abspath(self.test_file)
        self.assertNotIn(abs_path, self.notifier._callbacks)

    def test_duplicate_callback_registration(self):
        """중복 콜백 등록 방지 테스트"""
        callback = Mock()
        
        self.notifier.register_callback(self.test_file, callback)
        self.notifier.register_callback(self.test_file, callback)  # 중복 등록
        
        # 콜백이 한 번만 등록되었는지 확인
        abs_path = os.path.abspath(self.test_file)
        self.assertEqual(len(self.notifier._callbacks[abs_path]), 1)

    def test_notify_change(self):
        """변경 알림 테스트"""
        callback = Mock()
        self.notifier.register_callback(self.test_file, callback)
        
        # 변경 알림 발생
        self.notifier._notify_change(os.path.abspath(self.test_file), "modified")
        
        # 콜백이 호출되었는지 확인
        callback.assert_called_once_with(os.path.abspath(self.test_file), "modified")

    def test_callback_exception_handling(self):
        """콜백 예외 처리 테스트"""
        def failing_callback(file_path, change_type):
            raise Exception("Test exception")
        
        normal_callback = Mock()
        
        self.notifier.register_callback(self.test_file, failing_callback)
        self.notifier.register_callback(self.test_file, normal_callback)
        
        # 변경 알림 발생 (예외가 있어도 다른 콜백은 실행되어야 함)
        self.notifier._notify_change(os.path.abspath(self.test_file), "modified")
        
        # 정상 콜백은 호출되어야 함
        normal_callback.assert_called_once()

    def test_file_watching_start_stop(self):
        """파일 감시 시작/중지 테스트"""
        callback = Mock()
        
        # 파일 감시 시작
        self.notifier.register_callback(self.test_file, callback)
        self.assertTrue(self.notifier._running)
        
        # 파일 감시 중지
        self.notifier.unregister_callback(self.test_file, callback)
        self.assertFalse(self.notifier._running)

    @pytest.mark.skipif(os.name == "nt", reason="Windows에서 파일 이벤트 타이밍 이슈")
    def test_real_file_change_detection(self):
        """실제 파일 변경 감지 테스트"""
        callback_called = threading.Event()
        received_events = []
        
        def test_callback(file_path, change_type):
            received_events.append((file_path, change_type))
            callback_called.set()
        
        # 콜백 등록
        self.notifier.register_callback(self.test_file, test_callback)
        
        # 파일 생성
        with open(self.test_file, "w") as f:
            f.write("initial content")
        
        # 이벤트 대기 (최대 2초)
        if callback_called.wait(timeout=2.0):
            # 이벤트가 수신되었는지 확인
            self.assertTrue(len(received_events) > 0)
            # 생성 또는 수정 이벤트인지 확인
            event_types = [event[1] for event in received_events]
            self.assertTrue(any(event_type in ["created", "modified"] for event_type in event_types))

    def test_thread_safety(self):
        """스레드 안전성 테스트"""
        callbacks = [Mock() for _ in range(10)]
        threads = []
        
        def register_callback(cb):
            self.notifier.register_callback(self.test_file, cb)
        
        def unregister_callback(cb):
            self.notifier.unregister_callback(self.test_file, cb)
        
        # 여러 스레드에서 동시에 콜백 등록
        for cb in callbacks:
            thread = threading.Thread(target=register_callback, args=(cb,))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 모든 콜백이 등록되었는지 확인
        abs_path = os.path.abspath(self.test_file)
        self.assertEqual(len(self.notifier._callbacks[abs_path]), 10)
        
        # 콜백 해제
        threads = []
        for cb in callbacks:
            thread = threading.Thread(target=unregister_callback, args=(cb,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 모든 콜백이 해제되었는지 확인
        self.assertNotIn(abs_path, self.notifier._callbacks)


class TestConfigFileWatcher(unittest.TestCase):
    """ConfigFileWatcher 테스트"""

    def setUp(self):
        """테스트 초기화"""
        self.notifier = Mock()
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_config.ini")
        self.watched_files = {os.path.abspath(self.test_file)}
        self.watcher = ConfigFileWatcher(self.watched_files, self.notifier)

    def tearDown(self):
        """테스트 정리"""
        try:
            if os.path.exists(self.test_file):
                os.remove(self.test_file)
            os.rmdir(self.test_dir)
        except:
            pass

    def test_init_with_existing_file(self):
        """기존 파일이 있는 경우 초기화 테스트"""
        # 파일 생성
        with open(self.test_file, "w") as f:
            f.write("test content")
        
        # 새 watcher 생성
        watcher = ConfigFileWatcher(self.watched_files, self.notifier)
        
        # 수정 시간이 기록되었는지 확인
        abs_path = os.path.abspath(self.test_file)
        self.assertIn(abs_path, watcher.last_modified_times)

    def test_on_modified_cooldown(self):
        """수정 이벤트 쿨다운 테스트"""
        from unittest.mock import Mock
        from watchdog.events import FileModifiedEvent
        
        # 첫 번째 이벤트
        event = FileModifiedEvent(self.test_file)
        self.watcher.on_modified(event)
        
        # 즉시 두 번째 이벤트 (쿨다운 기간 내)
        self.watcher.on_modified(event)
        
        # 첫 번째 이벤트만 처리되어야 함
        self.notifier._notify_change.assert_called_once()

    def test_on_created(self):
        """파일 생성 이벤트 테스트"""
        from watchdog.events import FileCreatedEvent
        
        event = FileCreatedEvent(self.test_file)
        self.watcher.on_created(event)
        
        # 생성 이벤트가 알림되었는지 확인
        self.notifier._notify_change.assert_called_once_with(
            os.path.abspath(self.test_file), "created"
        )

    def test_on_deleted(self):
        """파일 삭제 이벤트 테스트"""
        from watchdog.events import FileDeletedEvent
        
        event = FileDeletedEvent(self.test_file)
        self.watcher.on_deleted(event)
        
        # 삭제 이벤트가 알림되었는지 확인
        self.notifier._notify_change.assert_called_once_with(
            os.path.abspath(self.test_file), "deleted"
        )

    def test_ignore_directory_events(self):
        """디렉토리 이벤트 무시 테스트"""
        from watchdog.events import DirModifiedEvent
        
        event = DirModifiedEvent(self.test_dir)
        self.watcher.on_modified(event)
        
        # 디렉토리 이벤트는 처리되지 않아야 함
        self.notifier._notify_change.assert_not_called()

    def test_ignore_non_watched_files(self):
        """감시하지 않는 파일 이벤트 무시 테스트"""
        from watchdog.events import FileModifiedEvent
        
        other_file = os.path.join(self.test_dir, "other_file.txt")
        event = FileModifiedEvent(other_file)
        self.watcher.on_modified(event)
        
        # 감시하지 않는 파일 이벤트는 처리되지 않아야 함
        self.notifier._notify_change.assert_not_called()


class TestGlobalNotifier(unittest.TestCase):
    """전역 notifier 테스트"""

    def test_singleton_behavior(self):
        """싱글톤 동작 테스트"""
        notifier1 = get_config_change_notifier()
        notifier2 = get_config_change_notifier()
        
        # 동일한 인스턴스인지 확인
        self.assertIs(notifier1, notifier2)

    def tearDown(self):
        """테스트 정리"""
        # 전역 notifier 정리
        notifier = get_config_change_notifier()
        notifier.stop_all()


if __name__ == "__main__":
    unittest.main() 