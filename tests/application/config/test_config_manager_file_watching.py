"""
ConfigManager 파일 변경 감지 통합 테스트

ConfigManager의 파일 변경 감지, 자동 리로드, 콜백 시스템에 대한 테스트를 수행합니다.
"""

import json
import os
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from application.config.config_manager import ConfigManager


class TestConfigManagerFileWatching(unittest.TestCase):
    """ConfigManager 파일 변경 감지 테스트"""

    def setUp(self):
        """테스트 초기화"""
        self.test_dir = tempfile.mkdtemp()
        self.app_config_file = os.path.join(self.test_dir, "test_app.config")
        self.llm_profiles_file = os.path.join(self.test_dir, "test_llm_profiles.json")
        
        # 기본 설정 파일 생성
        self._create_test_app_config()
        self._create_test_llm_profiles()
        
        # ConfigManager 인스턴스 생성
        with patch('application.config.llm_profile_manager.DEFAULT_LLM_PROFILES_JSON', self.llm_profiles_file):
            self.config_manager = ConfigManager(self.app_config_file)
        
        self.callback_events = []

    def tearDown(self):
        """테스트 정리"""
        try:
            self.config_manager.cleanup()
            # 임시 파일들 정리
            for file_path in [self.app_config_file, self.llm_profiles_file]:
                if os.path.exists(file_path):
                    os.remove(file_path)
            os.rmdir(self.test_dir)
        except:
            pass

    def _create_test_app_config(self):
        """테스트용 app.config 파일 생성"""
        config_content = """[LLM]
api_key = test-key
base_url = http://localhost:11434/v1
model = test-model

[UI]
font_family = Arial
font_size = 14
"""
        with open(self.app_config_file, "w", encoding="utf-8") as f:
            f.write(config_content)

    def _create_test_llm_profiles(self):
        """테스트용 LLM 프로필 파일 생성"""
        profiles_data = {
            "profiles": {
                "test": {
                    "name": "테스트 프로필",
                    "api_key": "test-api-key",
                    "base_url": "http://test.example.com",
                    "model": "test-model",
                    "temperature": 0.8,
                    "max_tokens": 50000,
                    "top_k": 40
                }
            },
            "current_profile": "test"
        }
        with open(self.llm_profiles_file, "w", encoding="utf-8") as f:
            json.dump(profiles_data, f, ensure_ascii=False, indent=2)

    def test_callback_registration(self):
        """콜백 등록/해제 테스트"""
        callback = Mock()
        
        # 콜백 등록
        self.config_manager.register_change_callback(callback)
        
        # 콜백이 등록되었는지 확인
        self.assertIn(callback, self.config_manager._change_callbacks)
        
        # 콜백 해제
        self.config_manager.unregister_change_callback(callback)
        
        # 콜백이 해제되었는지 확인
        self.assertNotIn(callback, self.config_manager._change_callbacks)

    def test_force_reload(self):
        """강제 리로드 테스트"""
        callback = Mock()
        self.config_manager.register_change_callback(callback)
        
        # 강제 리로드 실행
        self.config_manager.force_reload()
        
        # 콜백이 호출되었는지 확인
        callback.assert_called_once_with("manual_reload", "forced")

    def test_app_config_change_detection(self):
        """app.config 파일 변경 감지 테스트"""
        callback_called = threading.Event()
        received_events = []
        
        def test_callback(file_path, change_type):
            received_events.append((file_path, change_type))
            callback_called.set()
        
        self.config_manager.register_change_callback(test_callback)
        
        # 원본 값 확인
        original_api_key = self.config_manager.get_config_value("LLM", "api_key")
        self.assertEqual(original_api_key, "test-key")
        
        # 파일 수정
        time.sleep(0.2)  # 파일 시스템 이벤트 안정화
        config_content = """[LLM]
api_key = modified-key
base_url = http://localhost:11434/v1
model = test-model

[UI]
font_family = Arial
font_size = 14
"""
        with open(self.app_config_file, "w", encoding="utf-8") as f:
            f.write(config_content)
        
        # 콜백 호출 대기 (최대 3초)
        if callback_called.wait(timeout=3.0):
            # 변경된 값이 자동으로 리로드되었는지 확인
            time.sleep(0.1)  # 리로드 완료 대기
            new_api_key = self.config_manager.get_config_value("LLM", "api_key")
            self.assertEqual(new_api_key, "modified-key")
            
            # 콜백이 호출되었는지 확인
            self.assertTrue(len(received_events) > 0)
            file_paths = [event[0] for event in received_events]
            self.assertTrue(any(self.app_config_file in path for path in file_paths))

    def test_llm_profiles_change_detection(self):
        """LLM 프로필 파일 변경 감지 테스트"""
        callback_called = threading.Event()
        received_events = []
        
        def test_callback(file_path, change_type):
            received_events.append((file_path, change_type))
            callback_called.set()
        
        self.config_manager.register_change_callback(test_callback)
        
        # 원본 프로필 확인
        original_profiles = self.config_manager.get_llm_profiles()
        self.assertIn("test", original_profiles)
        
        # 프로필 파일 수정
        time.sleep(0.2)  # 파일 시스템 이벤트 안정화
        modified_profiles_data = {
            "profiles": {
                "test": {
                    "name": "수정된 테스트 프로필",
                    "api_key": "modified-api-key",
                    "base_url": "http://modified.example.com",
                    "model": "modified-model",
                    "temperature": 0.9,
                    "max_tokens": 60000,
                    "top_k": 45
                },
                "new_profile": {
                    "name": "새 프로필",
                    "api_key": "new-api-key",
                    "base_url": "http://new.example.com",
                    "model": "new-model",
                    "temperature": 0.7,
                    "max_tokens": 40000,
                    "top_k": 30
                }
            },
            "current_profile": "test"
        }
        
        with open(self.llm_profiles_file, "w", encoding="utf-8") as f:
            json.dump(modified_profiles_data, f, ensure_ascii=False, indent=2)
        
        # 콜백 호출 대기 (최대 3초)
        if callback_called.wait(timeout=3.0):
            # 변경된 프로필이 자동으로 리로드되었는지 확인
            time.sleep(0.1)  # 리로드 완료 대기
            new_profiles = self.config_manager.get_llm_profiles()
            self.assertIn("new_profile", new_profiles)
            self.assertEqual(new_profiles["test"]["name"], "수정된 테스트 프로필")
            
            # 콜백이 호출되었는지 확인
            self.assertTrue(len(received_events) > 0)
            file_paths = [event[0] for event in received_events]
            self.assertTrue(any(self.llm_profiles_file in path for path in file_paths))

    def test_file_deletion_recovery(self):
        """파일 삭제 시 복구 테스트"""
        callback_called = threading.Event()
        received_events = []
        
        def test_callback(file_path, change_type):
            received_events.append((file_path, change_type))
            if change_type == "deleted":
                callback_called.set()
        
        self.config_manager.register_change_callback(test_callback)
        
        # app.config 파일 삭제
        time.sleep(0.2)  # 파일 시스템 이벤트 안정화
        os.remove(self.app_config_file)
        
        # 삭제 감지 대기 (최대 3초)
        if callback_called.wait(timeout=3.0):
            # 기본 설정으로 복구되었는지 확인
            time.sleep(0.2)  # 복구 완료 대기
            self.assertTrue(os.path.exists(self.app_config_file))
            
            # 콜백이 호출되었는지 확인
            delete_events = [event for event in received_events if event[1] == "deleted"]
            self.assertTrue(len(delete_events) > 0)

    def test_multiple_callbacks(self):
        """여러 콜백 동시 처리 테스트"""
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()
        
        # 여러 콜백 등록
        self.config_manager.register_change_callback(callback1)
        self.config_manager.register_change_callback(callback2)
        self.config_manager.register_change_callback(callback3)
        
        # 강제 리로드로 콜백 트리거
        self.config_manager.force_reload()
        
        # 모든 콜백이 호출되었는지 확인
        callback1.assert_called_once()
        callback2.assert_called_once()
        callback3.assert_called_once()

    def test_callback_exception_handling(self):
        """콜백 예외 처리 테스트"""
        def failing_callback(file_path, change_type):
            raise Exception("Test callback exception")
        
        normal_callback = Mock()
        
        # 실패하는 콜백과 정상 콜백 등록
        self.config_manager.register_change_callback(failing_callback)
        self.config_manager.register_change_callback(normal_callback)
        
        # 강제 리로드 (예외가 발생해도 다른 콜백은 실행되어야 함)
        self.config_manager.force_reload()
        
        # 정상 콜백은 호출되어야 함
        normal_callback.assert_called_once()

    def test_thread_safety_with_callbacks(self):
        """콜백과 함께 스레드 안전성 테스트"""
        callbacks = []
        threads = []
        
        def create_callback(callback_id):
            def callback(file_path, change_type):
                callbacks.append(f"callback_{callback_id}_{change_type}")
            return callback
        
        # 여러 스레드에서 동시에 콜백 등록
        for i in range(5):
            callback = create_callback(i)
            
            def register_callback(cb=callback):
                self.config_manager.register_change_callback(cb)
            
            thread = threading.Thread(target=register_callback)
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 콜백이 등록되었는지 확인
        self.assertEqual(len(self.config_manager._change_callbacks), 5)
        
        # 강제 리로드로 모든 콜백 트리거
        self.config_manager.force_reload()
        
        # 모든 콜백이 실행되었는지 확인
        time.sleep(0.1)  # 콜백 실행 완료 대기
        self.assertEqual(len(callbacks), 5)

    def test_config_value_freshness(self):
        """설정값 최신성 보장 테스트"""
        callback_called = threading.Event()
        
        def test_callback(file_path, change_type):
            if self.app_config_file in file_path and change_type in ["modified", "created"]:
                callback_called.set()\
        
        self.config_manager.register_change_callback(test_callback)
        
        # 초기값 확인
        initial_value = self.config_manager.get_config_value("LLM", "api_key")
        self.assertEqual(initial_value, "test-key")
        
        # 외부에서 파일 수정 (시뮬레이션)
        time.sleep(0.2)  # 파일 시스템 이벤트 안정화
        config_content = """[LLM]
api_key = externally-modified-key
base_url = http://localhost:11434/v1
model = test-model

[UI]
font_family = Arial
font_size = 14
"""
        with open(self.app_config_file, "w", encoding="utf-8") as f:
            f.write(config_content)
        
        # 파일 변경 감지 대기 (최대 3초)
        if callback_called.wait(timeout=3.0):
            # 리로드 완료 대기
            time.sleep(0.1)
            updated_value = self.config_manager.get_config_value("LLM", "api_key")
            # 자동으로 업데이트된 값이 반환되는지 확인
            self.assertEqual(updated_value, "externally-modified-key")
        else:
            # 파일 변경이 감지되지 않았다면 강제 리로드 후 확인
            self.config_manager.force_reload()
            updated_value = self.config_manager.get_config_value("LLM", "api_key")
            self.assertEqual(updated_value, "externally-modified-key")


if __name__ == "__main__":
    unittest.main() 