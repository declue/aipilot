from application.util.friendly_message_builder import build_friendly_message


def test_push_builder():
    message = {
        "event_type": "push",
        "payload": {
            "commits": [{}, {}],
            "ref": "refs/heads/main",
            "pusher": {"name": "tester"},
        },
    }
    title, content = build_friendly_message(message)
    assert "tester" in title and title
    assert "커밋" in content


def test_fallback_builder():
    message = {"event_type": "star", "payload": {"sender": {"login": "me"}}}
    title, content = build_friendly_message(message)
    # fallback still returns strings
    assert isinstance(title, str) and isinstance(content, str) and title 