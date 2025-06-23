from __future__ import annotations

"""Event-specific friendly message builders.

각 GitHub 이벤트 타입에 대해 인간 친화적인 제목/내용을 생성하는 전략 클래스.
현재는 push, pull_request 두 타입만 별도 구현하고, 나머지는 WebhookClient 기존
로직을 재사용한다.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class BaseMessageBuilder(ABC):
    """Interface for building title/content pair."""

    @abstractmethod
    def build(self, message: Dict[str, Any]) -> Tuple[str, str]:  # noqa: D401
        ...


class PushMessageBuilder(BaseMessageBuilder):
    def build(self, message: Dict[str, Any]) -> Tuple[str, str]:
        payload = message.get("payload", {})
        commits = payload.get("commits", [])
        branch = payload.get("ref", "").replace("refs/heads/", "")
        commit_count = len(commits)
        pusher = payload.get("pusher", {}).get("name", "누군가")
        title = f"🚀 {pusher}님이 {branch or '브랜치'}에 {commit_count}개 커밋!"
        content = (
            f"{pusher}님이 {branch or '브랜치'}에 코드를 푸시했습니다. 커밋 수: {commit_count}"
        )
        return title, content


class PullRequestMessageBuilder(BaseMessageBuilder):
    def build(self, message: Dict[str, Any]) -> Tuple[str, str]:
        payload = message.get("payload", {})
        pr = payload.get("pull_request", {})
        action = payload.get("action", "")
        pr_title = pr.get("title", "제목 없음")
        pr_number = pr.get("number", "")
        author = pr.get("user", {}).get("login", "누군가")
        title = f"📝 PR {action}: {pr_title}"
        content = f'{author}님의 PR #{pr_number} "{pr_title}" ({action})'
        return title, content


# Mapping
_BUILDER_MAP: Dict[str, BaseMessageBuilder] = {
    "push": PushMessageBuilder(),
    "pull_request": PullRequestMessageBuilder(),
}


def get_builder(event_type: str) -> BaseMessageBuilder | None:  # noqa: D401
    return _BUILDER_MAP.get(event_type)
