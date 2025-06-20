import os
from pathlib import Path
from unittest import mock

from application.config.config_manager import ConfigManager


def test_create_and_load_default_config(tmp_path: Path) -> None:
    config_file = tmp_path / "test_app.config"
    manager = ConfigManager(str(config_file))
    assert os.path.exists(config_file)
    assert manager.get_config_value("LLM", "api_key") == "your-api-key-here"


def test_set_and_get_config_value(tmp_path: Path) -> None:
    config_file = tmp_path / "test_app.config"
    manager = ConfigManager(str(config_file))
    manager.set_config_value("TEST", "key", "value")
    assert manager.get_config_value("TEST", "key") == "value"


def test_llm_profile_create_update_delete(tmp_path: Path) -> None:
    config_file = tmp_path / "test_app.config"
    llm_profiles_file = tmp_path / "llm_profiles.json"
    
    # ConfigManager 인스턴스 생성 후 llm_profiles_file 경로 직접 설정
    manager = ConfigManager(str(config_file))
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


def test_set_and_get_ui_config(tmp_path: Path) -> None:
    config_file = tmp_path / "test_app.config"
    manager = ConfigManager(str(config_file))
    manager.set_ui_config("Arial", 16, 700, "dark")
    ui = manager.get_ui_config()
    assert ui["font_family"] == "Arial"
    assert ui["font_size"] == 16
    assert ui["chat_bubble_max_width"] == 700
    assert ui["window_theme"] == "dark"


def test_github_repositories(tmp_path: Path) -> None:
    config_file = tmp_path / "test_app.config"
    manager = ConfigManager(str(config_file))
    manager.set_github_repositories(["repo1", "repo2"])
    repos = manager.get_github_repositories()
    assert repos == ["repo1", "repo2"]


def test_instruction_content(tmp_path: Path) -> None:
    instructions_dir = tmp_path / "instructions"
    instructions_dir.mkdir()
    instruction_file = instructions_dir / "default_agent_instructions.txt"
    instruction_file.write_text("테스트 인스트럭션", encoding="utf-8")
    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        manager = ConfigManager(str(tmp_path / "conf.config"))
        content = manager.get_instruction_content()
        assert "테스트 인스트럭션" in content


def test_set_current_profile(tmp_path: Path) -> None:
    config_file = tmp_path / "test_app.config"
    llm_profiles_file = tmp_path / "llm_profiles.json"
    
    # ConfigManager 인스턴스 생성 후 llm_profiles_file 경로 직접 설정
    manager = ConfigManager(str(config_file))
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

