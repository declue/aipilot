"""작업 설정 모델 테스트"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from application.tasks.models.task_config import TaskConfig, TaskConfigFileManager, TaskSettings


class TestTaskConfig:
    """TaskConfig 클래스 테스트"""

    def test_task_config_초기화_기본값(self) -> None:
        """기본값으로 TaskConfig 초기화 테스트"""
        task = TaskConfig(
            id="test-task",
            name="테스트 작업",
            description="테스트용 작업입니다",
            cron_expression="0 10 * * *",
            action_type="llm_request",
            action_params={"prompt": "안녕하세요"},
        )

        assert task.id == "test-task"
        assert task.name == "테스트 작업"
        assert task.description == "테스트용 작업입니다"
        assert task.cron_expression == "0 10 * * *"
        assert task.action_type == "llm_request"
        assert task.action_params == {"prompt": "안녕하세요"}
        assert task.enabled is True
        assert task.created_at is not None
        assert task.last_run is None
        assert task.run_count == 0

    def test_task_config_post_init_created_at_자동설정(self) -> None:
        """__post_init__에서 created_at 자동 설정 테스트"""
        with patch("application.tasks.models.task_config.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            task = TaskConfig(
                id="test",
                name="테스트",
                description="설명",
                cron_expression="0 10 * * *",
                action_type="test",
                action_params={},
            )

            assert task.created_at == "2024-01-01T12:00:00"

    def test_task_config_to_dict(self) -> None:
        """to_dict 메서드 테스트"""
        task = TaskConfig(
            id="test",
            name="테스트",
            description="설명",
            cron_expression="0 10 * * *",
            action_type="test",
            action_params={"key": "value"},
            enabled=False,
            created_at="2024-01-01T00:00:00",
            last_run="2024-01-01T10:00:00",
            run_count=5,
        )

        result = task.to_dict()

        expected = {
            "id": "test",
            "name": "테스트",
            "description": "설명",
            "cron_expression": "0 10 * * *",
            "action_type": "test",
            "action_params": {"key": "value"},
            "enabled": False,
            "created_at": "2024-01-01T00:00:00",
            "last_run": "2024-01-01T10:00:00",
            "run_count": 5,
        }

        assert result == expected

    def test_task_config_from_dict(self) -> None:
        """from_dict 클래스 메서드 테스트"""
        data = {
            "id": "test",
            "name": "테스트",
            "description": "설명",
            "cron_expression": "0 10 * * *",
            "action_type": "test",
            "action_params": {"key": "value"},
            "enabled": False,
            "created_at": "2024-01-01T00:00:00",
            "last_run": "2024-01-01T10:00:00",
            "run_count": 5,
        }

        task = TaskConfig.from_dict(data)

        assert task.id == "test"
        assert task.name == "테스트"
        assert task.description == "설명"
        assert task.cron_expression == "0 10 * * *"
        assert task.action_type == "test"
        assert task.action_params == {"key": "value"}
        assert task.enabled is False
        assert task.created_at == "2024-01-01T00:00:00"
        assert task.last_run == "2024-01-01T10:00:00"
        assert task.run_count == 5

    def test_task_config_update_last_run(self) -> None:
        """update_last_run 메서드 테스트"""
        task = TaskConfig(
            id="test",
            name="테스트",
            description="설명",
            cron_expression="0 10 * * *",
            action_type="test",
            action_params={},
        )

        initial_run_count = task.run_count

        with patch("application.tasks.models.task_config.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
            
            task.update_last_run()

            assert task.last_run == "2024-01-01T12:00:00"
            assert task.run_count == initial_run_count + 1


class TestTaskSettings:
    """TaskSettings 클래스 테스트"""

    def test_task_settings_초기화_기본값(self) -> None:
        """기본값으로 TaskSettings 초기화 테스트"""
        settings = TaskSettings()

        assert settings.enabled is True
        assert settings.max_concurrent_jobs == 3
        assert settings.timezone == "Asia/Seoul"
        assert settings.log_level == "INFO"
        assert settings.tasks == {}

    def test_task_settings_add_task(self) -> None:
        """작업 추가 테스트"""
        settings = TaskSettings()
        task = TaskConfig(
            id="test-task",
            name="테스트 작업",
            description="설명",
            cron_expression="0 10 * * *",
            action_type="test",
            action_params={},
        )

        settings.add_task(task)

        assert "test-task" in settings.tasks
        assert settings.tasks["test-task"] == task

    def test_task_settings_remove_task(self) -> None:
        """작업 제거 테스트"""
        settings = TaskSettings()
        task = TaskConfig(
            id="test-task",
            name="테스트 작업",
            description="설명",
            cron_expression="0 10 * * *",
            action_type="test",
            action_params={},
        )

        settings.add_task(task)
        assert "test-task" in settings.tasks

        settings.remove_task("test-task")
        assert "test-task" not in settings.tasks

    def test_task_settings_remove_task_존재하지않는_작업(self) -> None:
        """존재하지 않는 작업 제거 시도 테스트"""
        settings = TaskSettings()
        
        # 예외가 발생하지 않아야 함
        settings.remove_task("nonexistent-task")

    def test_task_settings_get_task(self) -> None:
        """작업 조회 테스트"""
        settings = TaskSettings()
        task = TaskConfig(
            id="test-task",
            name="테스트 작업",
            description="설명",
            cron_expression="0 10 * * *",
            action_type="test",
            action_params={},
        )

        settings.add_task(task)

        retrieved_task = settings.get_task("test-task")
        assert retrieved_task == task

        nonexistent_task = settings.get_task("nonexistent")
        assert nonexistent_task is None

    def test_task_settings_get_enabled_tasks(self) -> None:
        """활성화된 작업들 조회 테스트"""
        settings = TaskSettings()
        
        enabled_task = TaskConfig(
            id="enabled-task",
            name="활성화된 작업",
            description="설명",
            cron_expression="0 10 * * *",
            action_type="test",
            action_params={},
            enabled=True,
        )
        
        disabled_task = TaskConfig(
            id="disabled-task",
            name="비활성화된 작업",
            description="설명",
            cron_expression="0 10 * * *",
            action_type="test",
            action_params={},
            enabled=False,
        )

        settings.add_task(enabled_task)
        settings.add_task(disabled_task)

        enabled_tasks = settings.get_enabled_tasks()

        assert len(enabled_tasks) == 1
        assert "enabled-task" in enabled_tasks
        assert "disabled-task" not in enabled_tasks

    def test_task_settings_to_dict(self) -> None:
        """to_dict 메서드 테스트"""
        settings = TaskSettings(
            enabled=False,
            max_concurrent_jobs=5,
            timezone="UTC",
            log_level="DEBUG",
        )
        
        task = TaskConfig(
            id="test-task",
            name="테스트 작업",
            description="설명",
            cron_expression="0 10 * * *",
            action_type="test",
            action_params={},
        )
        settings.add_task(task)

        result = settings.to_dict()

        expected = {
            "enabled": False,
            "max_concurrent_jobs": 5,
            "timezone": "UTC",
            "log_level": "DEBUG",
            "tasks": {
                "test-task": task.to_dict()
            },
        }

        assert result == expected

    def test_task_settings_from_dict(self) -> None:
        """from_dict 클래스 메서드 테스트"""
        data = {
            "enabled": False,
            "max_concurrent_jobs": 5,
            "timezone": "UTC",
            "log_level": "DEBUG",
            "tasks": {
                "test-task": {
                    "id": "test-task",
                    "name": "테스트 작업",
                    "description": "설명",
                    "cron_expression": "0 10 * * *",
                    "action_type": "test",
                    "action_params": {},
                    "enabled": True,
                    "created_at": "2024-01-01T00:00:00",
                    "last_run": None,
                    "run_count": 0,
                }
            },
        }

        settings = TaskSettings.from_dict(data)

        assert settings.enabled is False
        assert settings.max_concurrent_jobs == 5
        assert settings.timezone == "UTC"
        assert settings.log_level == "DEBUG"
        assert len(settings.tasks) == 1
        assert "test-task" in settings.tasks
        assert settings.tasks["test-task"].name == "테스트 작업"


class TestTaskConfigFileManager:
    """TaskConfigFileManager 클래스 테스트"""

    def test_save_to_file_성공(self) -> None:
        """파일 저장 성공 테스트"""
        settings = TaskSettings()
        task = TaskConfig(
            id="test-task",
            name="테스트 작업",
            description="설명",
            cron_expression="0 10 * * *",
            action_type="test",
            action_params={},
        )
        settings.add_task(task)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name

        try:
            TaskConfigFileManager.save_to_file(settings, tmp_path)

            # 파일이 올바르게 저장되었는지 확인
            with open(tmp_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)

            assert saved_data == settings.to_dict()

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_save_to_file_IOError(self) -> None:
        """파일 저장 시 IOError 발생 테스트"""
        settings = TaskSettings()
        
        with patch("builtins.open", side_effect=IOError("디스크 공간 부족")):
            with pytest.raises(RuntimeError, match="작업 설정 파일 저장 실패"):
                TaskConfigFileManager.save_to_file(settings, "/invalid/path")

    def test_load_from_file_성공(self) -> None:
        """파일 로드 성공 테스트"""
        # 테스트 데이터 준비
        original_settings = TaskSettings(
            enabled=False,
            max_concurrent_jobs=5,
            timezone="UTC",
            log_level="DEBUG",
        )
        task = TaskConfig(
            id="test-task",
            name="테스트 작업",
            description="설명",
            cron_expression="0 10 * * *",
            action_type="test",
            action_params={},
        )
        original_settings.add_task(task)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as tmp_file:
            json.dump(original_settings.to_dict(), tmp_file, ensure_ascii=False, indent=2)
            tmp_path = tmp_file.name

        try:
            loaded_settings = TaskConfigFileManager.load_from_file(tmp_path)

            assert loaded_settings.enabled == original_settings.enabled
            assert loaded_settings.max_concurrent_jobs == original_settings.max_concurrent_jobs
            assert loaded_settings.timezone == original_settings.timezone
            assert loaded_settings.log_level == original_settings.log_level
            assert len(loaded_settings.tasks) == 1
            assert "test-task" in loaded_settings.tasks

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_load_from_file_파일없음(self) -> None:
        """존재하지 않는 파일 로드 테스트"""
        settings = TaskConfigFileManager.load_from_file("/nonexistent/file.json")
        
        # 기본 설정이 반환되어야 함
        assert isinstance(settings, TaskSettings)
        assert settings.enabled is True
        assert settings.tasks == {}

    def test_load_from_file_JSON_파싱오류(self) -> None:
        """잘못된 JSON 파일 로드 테스트"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as tmp_file:
            tmp_file.write("invalid json format")
            tmp_path = tmp_file.name

        try:
            with pytest.raises(RuntimeError, match="작업 설정 파일 로드 실패"):
                TaskConfigFileManager.load_from_file(tmp_path)

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_load_from_file_IOError(self) -> None:
        """파일 로드 시 IOError 발생 테스트"""
        with patch("builtins.open", side_effect=IOError("권한 없음")):
            with pytest.raises(RuntimeError, match="작업 설정 파일 로드 실패"):
                TaskConfigFileManager.load_from_file("/some/path") 