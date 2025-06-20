import json
from typing import Any, Dict, Tuple

import pytest

from application.config.config_manager import ConfigManager
from application.util.filter_engine import FilterEngine


@pytest.fixture()
def fresh_config(tmp_path):
    """임시 디렉토리에 독립적인 ConfigManager 인스턴스를 생성한다."""
    config_path = tmp_path / "app.config"
    cfg = ConfigManager(str(config_path))  # 새로운 파일 경로 사용
    return cfg


def make_push_message(commit_count: int = 1) -> Dict[str, Any]:
    """테스트용 push 이벤트 메시지 생성"""
    return {
        "event_type": "push",
        "payload": {
            "commits": [{}] * commit_count,
            "ref": "refs/heads/main",
            "pusher": {"name": "tester"},
        },
    }


def test_global_disable(fresh_config: ConfigManager):
    settings = {"enabled": False}
    fresh_config.set_config_value("GITHUB", "notification_settings", json.dumps(settings))

    engine = FilterEngine(fresh_config)
    show_system, show_bubble = engine.should_show_notification(make_push_message())
    assert (show_system, show_bubble) == (False, False)


def test_min_commits_filter(fresh_config: ConfigManager):
    settings = {
        "enabled": True,
        "events": {
            "push": {"enabled": True, "min_commits": 2},
        },
    }
    fresh_config.set_config_value("GITHUB", "notification_settings", json.dumps(settings))
    engine = FilterEngine(fresh_config)

    # 커밋 1개 -> 필터링
    assert engine.should_show_notification(make_push_message(1)) == (False, False)
    # 커밋 2개 -> 통과
    assert engine.should_show_notification(make_push_message(2))[0] is True


def test_show_system_only(fresh_config: ConfigManager):
    settings = {
        "enabled": True,
        "events": {
            "push": {
                "enabled": True,
                "show_system_notification": True,
                "show_chat_bubble": False,
            }
        },
    }
    fresh_config.set_config_value("GITHUB", "notification_settings", json.dumps(settings))
    engine = FilterEngine(fresh_config)

    result: Tuple[bool, bool] = engine.should_show_notification(make_push_message(3))
    assert result == (True, False) 