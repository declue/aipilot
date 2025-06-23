import os
from pathlib import Path
from unittest import mock

import pytest

from application.config.config_manager import ConfigManager
from application.config.libs.config_change_notifier import (
    cleanup_global_notifier,
    reset_global_notifier,
)

# 파일 감시 테스트 비활성화 조건
SKIP_FILE_WATCHING = os.environ.get("SKIP_FILE_WATCHING", "false").lower() in ("true", "1", "yes")


@pytest.fixture(autouse=True)
def setup_test_environment():
    """각 테스트마다 자동으로 실행되는 환경 설정"""
    # 전역 notifier 초기화
    reset_global_notifier()
    
    yield
    
    # 테스트 후 정리
    try:
        cleanup_global_notifier()
    except Exception:
        pass


@pytest.fixture
def config_manager_with_cleanup(tmp_path: Path):
    """ConfigManager 픽스처 - 자동 정리 포함"""
    config_file = tmp_path / "test_app.config"
    
    # 파일 감시 비활성화를 위한 패치
    with mock.patch.dict(os.environ, {"SKIP_FILE_WATCHING": "true"}):
        # ConfigManager의 파일 감시 설정을 무력화
        with mock.patch.object(ConfigManager, '_setup_file_watching', return_value=None):
            manager = ConfigManager(str(config_file))
    
    yield manager
    
    # 테스트 후 정리
    try:
        manager.cleanup()
    except Exception:
        pass


def test_create_and_load_default_config(config_manager_with_cleanup) -> None:
    """기본 설정 생성 및 로드 테스트"""
    manager = config_manager_with_cleanup
    config_file = manager.config_file
    
    assert os.path.exists(config_file)
    assert manager.get_config_value("LLM", "api_key") == "your-api-key-here"


def test_set_and_get_config_value(config_manager_with_cleanup) -> None:
    """설정값 설정 및 조회 테스트"""
    manager = config_manager_with_cleanup
    
    manager.set_config_value("TEST", "key", "value")
    assert manager.get_config_value("TEST", "key") == "value"


def test_llm_profile_create_update_delete(tmp_path: Path) -> None:
    """LLM 프로필 생성, 수정, 삭제 테스트"""
    config_file = tmp_path / "test_app.config"
    llm_profiles_file = tmp_path / "llm_profiles.json"
    
    # 파일 감시 비활성화를 위한 패치
    with mock.patch.dict(os.environ, {"SKIP_FILE_WATCHING": "true"}):
        with mock.patch.object(ConfigManager, '_setup_file_watching', return_value=None):
            manager = ConfigManager(str(config_file))
    
    try:
        # ConfigManager 인스턴스 생성 후 llm_profiles_file 경로 직접 설정
        manager.llm_profiles_file = str(llm_profiles_file)
        
        profile = {
            "name": "테스트",
            "api_key": "test-key",
            "base_url": "http://test",
            "model": "test-model",
            "temperature": 0.5,
            "max_tokens": 123,
            "top_k": 10,
        }
        manager.create_llm_profile("test", profile)
        profiles = manager.get_llm_profiles()
        assert "test" in profiles
        manager.update_llm_profile("test", {"model": "changed"})
        assert manager.get_llm_profiles()["test"]["model"] == "changed"
        manager.delete_llm_profile("test")
        assert "test" not in manager.get_llm_profiles()
    finally:
        manager.cleanup()


def test_set_and_get_ui_config(config_manager_with_cleanup) -> None:
    """UI 설정 테스트"""
    manager = config_manager_with_cleanup
    
    manager.set_ui_config("Arial", 16, 700, "dark")
    ui = manager.get_ui_config()
    assert ui["font_family"] == "Arial"
    assert ui["font_size"] == 16
    assert ui["chat_bubble_max_width"] == 700
    assert ui["window_theme"] == "dark"


def test_github_repositories(config_manager_with_cleanup) -> None:
    """GitHub 저장소 설정 테스트"""
    manager = config_manager_with_cleanup
    
    manager.set_github_repositories(["repo1", "repo2"])
    repos = manager.get_github_repositories()
    assert repos == ["repo1", "repo2"]


def test_instruction_content(tmp_path: Path) -> None:
    """인스트럭션 내용 테스트"""
    instructions_dir = tmp_path / "instructions"
    instructions_dir.mkdir()
    instruction_file = instructions_dir / "default_agent_instructions.txt"
    instruction_file.write_text("테스트 인스트럭션", encoding="utf-8")
    
    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        with mock.patch.dict(os.environ, {"SKIP_FILE_WATCHING": "true"}):
            with mock.patch.object(ConfigManager, '_setup_file_watching', return_value=None):
                manager = ConfigManager(str(tmp_path / "conf.config"))
        
        try:
            content = manager.get_instruction_content()
            assert "테스트 인스트럭션" in content
        finally:
            manager.cleanup()


def test_set_current_profile(tmp_path: Path) -> None:
    """현재 프로필 설정 테스트"""
    config_file = tmp_path / "test_app.config"
    llm_profiles_file = tmp_path / "llm_profiles.json"
    
    # 파일 감시 비활성화를 위한 패치
    with mock.patch.dict(os.environ, {"SKIP_FILE_WATCHING": "true"}):
        with mock.patch.object(ConfigManager, '_setup_file_watching', return_value=None):
            manager = ConfigManager(str(config_file))
    
    try:
        # ConfigManager 인스턴스 생성 후 llm_profiles_file 경로 직접 설정
        manager.llm_profiles_file = str(llm_profiles_file)
        
        # 기존 전역 프로필 정보 초기화 (외부 llm_profiles.json 영향 제거)
        manager._llm_profiles = {}
        manager.create_default_llm_profiles()

        manager.create_llm_profile("test2", {
            "name": "테스트2",
            "api_key": "k",
            "base_url": "b",
            "model": "m",
            "temperature": 0.1,
            "max_tokens": 1,
            "top_k": 1,
        })
        manager.set_current_profile("test2")
        assert manager.get_current_profile_name() == "test2"

        # 'test2' 프로필이 존재할 경우를 대비해 안전하게 삭제
        if "test2" in manager.get_llm_profiles():
            manager.delete_llm_profile("test2")
    finally:
        manager.cleanup()

