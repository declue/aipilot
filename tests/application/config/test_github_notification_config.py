"""application.config.github_notification_config 에 대한 단위 테스트"""

from application.config.github_notification_config import GitHubNotificationConfig


def test_serialization_roundtrip() -> None:
    """to_json / from_json 왕복 직렬화 후 객체 동등성 검증"""
    original = GitHubNotificationConfig()

    json_str = original.to_json()
    reconstructed = GitHubNotificationConfig.from_json(json_str)

    # dataclass 의 기본 __eq__ 구현은 필드 비교를 수행하므로 그대로 사용한다.
    assert original == reconstructed


def test_should_show_notification_push_basic() -> None:
    """기본 push 이벤트는 min/max 커밋 범위 내라면 알림이 표시되어야 한다."""
    cfg = GitHubNotificationConfig()
    system_notify, chat_bubble = cfg.should_show_notification(
        event_type="push", commits=[{"id": "a"}], branch="main"
    )

    assert system_notify is True
    assert chat_bubble is True


def test_should_show_notification_push_too_many_commits() -> None:
    """max_commits 초과 시 알림이 표시되지 않아야 한다."""
    cfg = GitHubNotificationConfig()
    commits = [{"id": str(i)} for i in range(cfg.push.max_commits + 1)]
    system_notify, chat_bubble = cfg.should_show_notification(
        event_type="push", commits=commits, branch="main"
    )

    assert (system_notify, chat_bubble) == (False, False)


def test_should_show_notification_pull_request_action_filter() -> None:
    """PR action 이 비활성화 되어 있으면 알림이 표시되지 않아야 한다."""
    cfg = GitHubNotificationConfig()

    # pre-condition: closed 는 기본적으로 True 로 설정돼 있으므로 False 로 오버라이드
    cfg.pull_request.actions["edited"] = False

    system_notify, chat_bubble = cfg.should_show_notification(
        event_type="pull_request", action="edited"
    )

    assert (system_notify, chat_bubble) == (False, False) 