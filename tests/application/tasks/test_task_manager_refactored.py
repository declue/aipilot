"""리팩토링된 TaskManager 테스트"""

from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.tasks.interfaces import ITaskConfiguration, ITaskScheduler
from application.tasks.models.task_config import TaskConfig, TaskSettings
from application.tasks.task_manager import TaskManager


class MockTaskConfiguration(ITaskConfiguration):
    """Mock 작업 설정 관리자"""
    
    def __init__(self):
        self._settings = TaskSettings()
        self._settings.enabled = True
        self._tasks = {}
        
    def load_settings(self) -> TaskSettings:
        return self._settings
        
    def save_settings(self, settings: TaskSettings) -> bool:
        self._settings = settings
        return True
        
    def add_task(self, task: TaskConfig) -> bool:
        self._tasks[task.id] = task
        if self._settings.tasks is None:
            self._settings.tasks = {}
        self._settings.tasks[task.id] = task
        return True
        
    def remove_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            if self._settings.tasks and task_id in self._settings.tasks:
                del self._settings.tasks[task_id]
            return True
        return False
        
    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        return self._tasks.get(task_id)
        
    def get_all_tasks(self) -> Dict[str, TaskConfig]:
        return self._tasks.copy()
        
    def get_enabled_tasks(self) -> Dict[str, TaskConfig]:
        return {k: v for k, v in self._tasks.items() if v.enabled}
        
    @property
    def settings(self) -> TaskSettings:
        return self._settings


class MockTaskScheduler(ITaskScheduler):
    """Mock 작업 스케줄러"""
    
    def __init__(self):
        self._is_running = False
        self._jobs = {}
        self._on_executed = None
        self._on_error = None
        
    def start(self) -> None:
        self._is_running = True
        
    def stop(self) -> None:
        self._is_running = False
        
    def add_job(self, task: TaskConfig) -> bool:
        self._jobs[task.id] = task
        return True
        
    def remove_job(self, task_id: str) -> bool:
        if task_id in self._jobs:
            del self._jobs[task_id]
            return True
        return False
        
    def update_job(self, task: TaskConfig) -> bool:
        self._jobs[task.id] = task
        return True
        
    def get_running_jobs(self) -> List[dict]:
        return [{"id": task.id, "name": task.name} for task in self._jobs.values()]
        
    def set_job_listener(self, on_executed=None, on_error=None) -> None:
        self._on_executed = on_executed
        self._on_error = on_error
        
    @property
    def is_running(self) -> bool:
        return self._is_running


class TestTaskManager:
    """리팩토링된 TaskManager 테스트 클래스"""

    @pytest.fixture
    def mock_task_configuration(self):
        """Mock 작업 설정 관리자"""
        return MockTaskConfiguration()

    @pytest.fixture
    def mock_task_scheduler(self):
        """Mock 작업 스케줄러"""
        return MockTaskScheduler()

    @pytest.fixture
    def task_manager(self, mock_task_configuration, mock_task_scheduler):
        """TaskManager 인스턴스 (Mock 의존성 주입)"""
        with patch('application.tasks.task_manager.HttpClient') as mock_http:
            with patch('application.tasks.task_manager.TaskExecutor') as mock_executor:
                manager = TaskManager(
                    config_file="test_task.json",
                    task_configuration=mock_task_configuration,
                    task_scheduler=mock_task_scheduler
                )
                return manager

    @pytest.fixture
    def sample_task(self):
        """샘플 작업 생성"""
        return TaskConfig(
            id="test_task",
            name="Test Task",
            description="Test Task Description",
            action_type="llm_request",
            action_params={"prompt": "test prompt"},
            cron_expression="0 0 * * *",
            enabled=True
        )

    def test_init_with_dependencies(self, mock_task_configuration, mock_task_scheduler):
        """의존성 주입을 통한 초기화 테스트"""
        with patch('application.tasks.task_manager.HttpClient') as mock_http:
            with patch('application.tasks.task_manager.TaskExecutor') as mock_executor:
                manager = TaskManager(
                    task_configuration=mock_task_configuration,
                    task_scheduler=mock_task_scheduler
                )
                
                assert manager.task_configuration is mock_task_configuration
                assert manager.task_scheduler is mock_task_scheduler
                assert mock_http.called
                assert mock_executor.called

    def test_start_scheduler(self, task_manager, mock_task_scheduler):
        """스케줄러 시작 테스트"""
        task_manager.start()
        
        assert mock_task_scheduler.is_running
        
    def test_start_scheduler_disabled(self, task_manager, mock_task_configuration, mock_task_scheduler):
        """스케줄러 비활성화 상태에서 시작 테스트"""
        mock_task_configuration.settings.enabled = False
        
        task_manager.start()
        
        assert not mock_task_scheduler.is_running

    def test_stop_scheduler(self, task_manager, mock_task_scheduler):
        """스케줄러 중지 테스트"""
        # 먼저 시작
        mock_task_scheduler._is_running = True
        
        with patch.object(task_manager.http_client, 'close', new_callable=AsyncMock) as mock_close:
            with patch('asyncio.run') as mock_asyncio_run:
                task_manager.stop()
                
                assert not mock_task_scheduler.is_running
                mock_asyncio_run.assert_called_once()

    def test_add_task_success(self, task_manager, sample_task, mock_task_configuration, mock_task_scheduler):
        """작업 추가 성공 테스트"""
        # 스케줄러가 실행 중인 상태로 설정
        mock_task_scheduler._is_running = True
        
        result = task_manager.add_task(sample_task)
        
        assert result is True
        assert sample_task.id in mock_task_configuration.get_all_tasks()
        assert sample_task.id in mock_task_scheduler._jobs

    def test_add_task_scheduler_not_running(self, task_manager, sample_task, mock_task_configuration, mock_task_scheduler):
        """스케줄러가 실행 중이 아닐 때 작업 추가 테스트"""
        mock_task_scheduler._is_running = False
        
        result = task_manager.add_task(sample_task)
        
        assert result is True
        assert sample_task.id in mock_task_configuration.get_all_tasks()
        # 스케줄러가 실행 중이 아니므로 작업이 스케줄러에 추가되지 않음
        assert sample_task.id not in mock_task_scheduler._jobs

    def test_update_task_success(self, task_manager, sample_task, mock_task_configuration, mock_task_scheduler):
        """작업 수정 성공 테스트"""
        # 먼저 작업 추가
        mock_task_configuration.add_task(sample_task)
        mock_task_scheduler._is_running = True
        
        # 작업 수정
        sample_task.name = "Updated Task"
        result = task_manager.update_task(sample_task)
        
        assert result is True
        updated_task = mock_task_configuration.get_task(sample_task.id)
        assert updated_task.name == "Updated Task"

    def test_remove_task_success(self, task_manager, sample_task, mock_task_configuration, mock_task_scheduler):
        """작업 제거 성공 테스트"""
        # 먼저 작업 추가
        mock_task_configuration.add_task(sample_task)
        mock_task_scheduler.add_job(sample_task)
        mock_task_scheduler._is_running = True
        
        # 작업 제거
        result = task_manager.remove_task(sample_task.id)
        
        assert result is True
        assert sample_task.id not in mock_task_configuration.get_all_tasks()
        assert sample_task.id not in mock_task_scheduler._jobs

    def test_get_tasks(self, task_manager, sample_task, mock_task_configuration):
        """모든 작업 조회 테스트"""
        mock_task_configuration.add_task(sample_task)
        
        tasks = task_manager.get_tasks()
        
        assert sample_task.id in tasks
        assert tasks[sample_task.id] == sample_task

    def test_get_task(self, task_manager, sample_task, mock_task_configuration):
        """특정 작업 조회 테스트"""
        mock_task_configuration.add_task(sample_task)
        
        task = task_manager.get_task(sample_task.id)
        
        assert task == sample_task

    def test_get_task_not_found(self, task_manager):
        """존재하지 않는 작업 조회 테스트"""
        task = task_manager.get_task("non_existent_task")
        
        assert task is None

    def test_get_running_jobs(self, task_manager, sample_task, mock_task_scheduler):
        """실행 중인 작업 조회 테스트"""
        mock_task_scheduler.add_job(sample_task)
        
        jobs = task_manager.get_running_jobs()
        
        assert len(jobs) == 1
        assert jobs[0]["id"] == sample_task.id
        assert jobs[0]["name"] == sample_task.name

    def test_toggle_task_enable(self, task_manager, mock_task_configuration):
        """작업 활성화 토글 테스트"""
        # 비활성화된 작업 생성
        task = TaskConfig(
            id="toggle_task",
            name="Toggle Task",
            description="Toggle Task Description",
            action_type="notification",
            action_params={"message": "test"},
            cron_expression="0 0 * * *",
            enabled=False
        )
        mock_task_configuration.add_task(task)
        
        # 활성화로 토글
        result = task_manager.toggle_task(task.id)
        
        assert result is True
        updated_task = mock_task_configuration.get_task(task.id)
        assert updated_task.enabled is True

    def test_toggle_task_disable(self, task_manager, sample_task, mock_task_configuration):
        """작업 비활성화 토글 테스트"""
        mock_task_configuration.add_task(sample_task)
        
        # 비활성화로 토글
        result = task_manager.toggle_task(sample_task.id)
        
        assert result is True
        updated_task = mock_task_configuration.get_task(sample_task.id)
        assert updated_task.enabled is False

    def test_toggle_task_not_found(self, task_manager):
        """존재하지 않는 작업 토글 테스트"""
        result = task_manager.toggle_task("non_existent_task")
        
        assert result is False

    def test_set_enabled_true(self, task_manager, mock_task_configuration, mock_task_scheduler):
        """스케줄러 활성화 테스트"""
        mock_task_scheduler._is_running = False
        
        task_manager.set_enabled(True)
        
        assert mock_task_configuration.settings.enabled is True

    def test_set_enabled_false(self, task_manager, mock_task_configuration, mock_task_scheduler):
        """스케줄러 비활성화 테스트"""
        mock_task_scheduler._is_running = True
        
        with patch.object(task_manager, 'stop') as mock_stop:
            task_manager.set_enabled(False)
            
            assert mock_task_configuration.settings.enabled is False
            mock_stop.assert_called_once()

    def test_is_running_property(self, task_manager, mock_task_scheduler):
        """실행 상태 프로퍼티 테스트"""
        mock_task_scheduler._is_running = True
        assert task_manager.is_running is True
        
        mock_task_scheduler._is_running = False
        assert task_manager.is_running is False

    def test_on_task_executed_callback(self, task_manager, sample_task, mock_task_configuration):
        """작업 실행 완료 콜백 테스트"""
        # 작업 추가
        mock_task_configuration.add_task(sample_task)
        
        # 콜백 함수 설정
        callback_called = False
        def test_callback(task_id, event):
            nonlocal callback_called
            callback_called = True
            assert task_id == sample_task.id
        
        task_manager.on_task_executed = test_callback
        
        # 콜백 실행
        task_manager._on_task_executed(sample_task.id, "test_event")
        
        assert callback_called

    def test_on_task_error_callback(self, task_manager):
        """작업 실행 오류 콜백 테스트"""
        # 콜백 함수 설정
        callback_called = False
        def test_callback(task_id, event):
            nonlocal callback_called
            callback_called = True
            assert task_id == "error_task"
        
        task_manager.on_task_error = test_callback
        
        # 콜백 실행
        task_manager._on_task_error("error_task", "test_error")
        
        assert callback_called 