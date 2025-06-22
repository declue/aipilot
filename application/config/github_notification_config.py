"""GitHub Webhook 알림 설정 데이터 모델"""

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class PushNotificationConfig:
    """Push 이벤트 알림 설정"""

    enabled: bool = True
    show_system_notification: bool = True
    show_chat_bubble: bool = True
    min_commits: int = 1  # 최소 커밋 수
    max_commits: int = 50  # 최대 커밋 수 (초과시 요약)
    exclude_branches: List[str] = field(default_factory=list)  # 제외할 브랜치
    include_branches: List[str] = field(
        default_factory=list
    )  # 포함할 브랜치 (비어있으면 모든 브랜치)


@dataclass
class PullRequestNotificationConfig:
    """Pull Request 이벤트 알림 설정"""

    enabled: bool = True
    show_system_notification: bool = True
    show_chat_bubble: bool = True
    actions: Dict[str, bool] = field(
        default_factory=lambda: {
            "opened": True,
            "closed": True,
            "reopened": True,
            "edited": False,
            "assigned": False,
            "unassigned": False,
            "review_requested": True,
            "review_request_removed": False,
            "labeled": False,
            "unlabeled": False,
            "synchronize": False,  # PR 업데이트
            "ready_for_review": True,
            "converted_to_draft": False,
        }
    )


@dataclass
class IssuesNotificationConfig:
    """Issues 이벤트 알림 설정"""

    enabled: bool = True
    show_system_notification: bool = True
    show_chat_bubble: bool = True
    actions: Dict[str, bool] = field(
        default_factory=lambda: {
            "opened": True,
            "closed": True,
            "reopened": True,
            "edited": False,
            "assigned": True,
            "unassigned": False,
            "labeled": False,
            "unlabeled": False,
            "locked": False,
            "unlocked": False,
            "transferred": True,
            "pinned": False,
            "unpinned": False,
        }
    )


@dataclass
class ReleaseNotificationConfig:
    """Release 이벤트 알림 설정"""

    enabled: bool = True
    show_system_notification: bool = True
    show_chat_bubble: bool = True
    actions: Dict[str, bool] = field(
        default_factory=lambda: {
            "published": True,
            "unpublished": False,
            "created": False,
            "edited": False,
            "deleted": True,
            "prereleased": True,
            "released": True,
        }
    )
    include_prerelease: bool = True
    include_draft: bool = False


@dataclass
class WorkflowNotificationConfig:
    """GitHub Actions Workflow 이벤트 알림 설정"""

    enabled: bool = True
    show_system_notification: bool = True
    show_chat_bubble: bool = True
    statuses: Dict[str, bool] = field(
        default_factory=lambda: {
            "success": True,
            "failure": True,
            "cancelled": True,
            "in_progress": False,
            "queued": False,
            "pending": False,
            "skipped": False,
            "timed_out": True,
            "action_required": True,
            "neutral": False,
            "stale": False,
        }
    )
    conclusions: Dict[str, bool] = field(
        default_factory=lambda: {
            "success": True,
            "failure": True,
            "cancelled": True,
            "timed_out": True,
            "action_required": True,
            "neutral": False,
            "skipped": False,
            "startup_failure": True,
        }
    )


@dataclass
class RepositoryNotificationConfig:
    """Repository 이벤트 알림 설정"""

    enabled: bool = True
    show_system_notification: bool = True
    show_chat_bubble: bool = True
    actions: Dict[str, bool] = field(
        default_factory=lambda: {
            "star": True,
            "unstar": False,
            "fork": True,
            "watch": False,
            "unwatch": False,
            "create": True,  # 브랜치/태그 생성
            "delete": True,  # 브랜치/태그 삭제
        }
    )


@dataclass
class CheckNotificationConfig:
    """Check Run/Suite 이벤트 알림 설정"""

    enabled: bool = True
    show_system_notification: bool = True
    show_chat_bubble: bool = True
    actions: Dict[str, bool] = field(
        default_factory=lambda: {
            "completed": True,
            "created": False,
            "rerequested": False,
            "requested_action": True,
        }
    )
    conclusions: Dict[str, bool] = field(
        default_factory=lambda: {
            "success": True,
            "failure": True,
            "neutral": False,
            "cancelled": True,
            "timed_out": True,
            "action_required": True,
            "skipped": False,
            "stale": False,
        }
    )


@dataclass
class GitHubNotificationConfig:
    """GitHub 알림 통합 설정"""

    enabled: bool = True
    push: PushNotificationConfig = field(
        default_factory=PushNotificationConfig)
    pull_request: PullRequestNotificationConfig = field(
        default_factory=PullRequestNotificationConfig
    )
    issues: IssuesNotificationConfig = field(
        default_factory=IssuesNotificationConfig)
    release: ReleaseNotificationConfig = field(
        default_factory=ReleaseNotificationConfig
    )
    workflow: WorkflowNotificationConfig = field(
        default_factory=WorkflowNotificationConfig
    )
    repository: RepositoryNotificationConfig = field(
        default_factory=RepositoryNotificationConfig
    )
    check: CheckNotificationConfig = field(
        default_factory=CheckNotificationConfig)

    # 전역 설정
    summary_enabled: bool = True  # 여러 이벤트 요약 기능
    summary_threshold: int = 3  # 요약을 시작할 최소 이벤트 수
    rate_limit_enabled: bool = True  # 속도 제한
    rate_limit_interval: int = 300  # 5분 내 최대 알림 수 제한
    rate_limit_max_count: int = 20  # 5분 내 최대 20개 알림

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        # dataclasses.asdict 는 중첩된 dataclass 까지 재귀적으로 순회하며
        # JSON 직렬화가 가능한 기본 타입(dict, list, primitive 등)으로 자동 변환한다.
        # 기존의 수동 변환 로직을 대체하여 유지보수성을 향상시킨다.
        return asdict(self) if is_dataclass(self) else {}

    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubNotificationConfig":
        """딕셔너리에서 생성"""

        def create_config(config_class, config_data):
            if not isinstance(config_data, dict):
                return config_class()

            # 필드 타입에 맞게 변환
            field_values = {}
            for field_name, _field_obj in config_class.__dataclass_fields__.items():
                if field_name in config_data:
                    field_values[field_name] = config_data[field_name]

            return config_class(**field_values)

        # 각 서브 설정 생성
        push_config = create_config(
            PushNotificationConfig, data.get("push", {}))
        pr_config = create_config(
            PullRequestNotificationConfig, data.get("pull_request", {})
        )
        issues_config = create_config(
            IssuesNotificationConfig, data.get("issues", {}))
        release_config = create_config(
            ReleaseNotificationConfig, data.get("release", {})
        )
        workflow_config = create_config(
            WorkflowNotificationConfig, data.get("workflow", {})
        )
        repository_config = create_config(
            RepositoryNotificationConfig, data.get("repository", {})
        )
        check_config = create_config(
            CheckNotificationConfig, data.get("check", {}))

        # 메인 설정 생성
        main_fields = {
            "enabled": data.get("enabled", True),
            "summary_enabled": data.get("summary_enabled", True),
            "summary_threshold": data.get("summary_threshold", 3),
            "rate_limit_enabled": data.get("rate_limit_enabled", True),
            "rate_limit_interval": data.get("rate_limit_interval", 300),
            "rate_limit_max_count": data.get("rate_limit_max_count", 20),
            "push": push_config,
            "pull_request": pr_config,
            "issues": issues_config,
            "release": release_config,
            "workflow": workflow_config,
            "repository": repository_config,
            "check": check_config,
        }

        return cls(**main_fields)

    @classmethod
    def from_json(cls, json_str: str) -> "GitHubNotificationConfig":
        """JSON 문자열에서 생성"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError) as _e:
            # 파싱 실패 시 기본 설정 반환
            return cls()

    def should_show_notification(
        self, event_type: str, action: Optional[str] = None, **kwargs
    ) -> tuple[bool, bool]:
        """
        알림을 표시할지 여부를 결정

        Returns:
            tuple[bool, bool]: (시스템 알림 표시 여부, 채팅 버블 표시 여부)
        """
        if not self.enabled:
            return False, False

        event_config: Optional[
            Union[
                PushNotificationConfig,
                PullRequestNotificationConfig,
                IssuesNotificationConfig,
                ReleaseNotificationConfig,
                WorkflowNotificationConfig,
                RepositoryNotificationConfig,
                CheckNotificationConfig,
            ]
        ] = None

        if event_type == "push":
            event_config = self.push
            # 커밋 수 확인
            commits = kwargs.get("commits", [])
            commit_count = len(commits) if commits else 1
            if (
                commit_count < event_config.min_commits
                or commit_count > event_config.max_commits
            ):
                return False, False

            # 브랜치 확인
            branch = kwargs.get("branch", "")
            if (
                event_config.exclude_branches
                and branch in event_config.exclude_branches
            ):
                return False, False
            if (
                event_config.include_branches
                and branch not in event_config.include_branches
            ):
                return False, False

        elif event_type == "pull_request":
            event_config = self.pull_request
            if action and not event_config.actions.get(action, False):
                return False, False

        elif event_type == "issues":
            event_config = self.issues
            if action and not event_config.actions.get(action, False):
                return False, False

        elif event_type == "release":
            event_config = self.release
            if action and not event_config.actions.get(action, False):
                return False, False

            # prerelease/draft 확인
            is_prerelease = kwargs.get("prerelease", False)
            is_draft = kwargs.get("draft", False)
            if is_prerelease and not event_config.include_prerelease:
                return False, False
            if is_draft and not event_config.include_draft:
                return False, False

        elif event_type in ["workflow_run", "workflow_job"]:
            event_config = self.workflow
            status = kwargs.get("status", "")
            conclusion = kwargs.get("conclusion", "")

            if status and not event_config.statuses.get(status, False):
                return False, False
            if conclusion and not event_config.conclusions.get(conclusion, False):
                return False, False

        elif event_type in ["check_run", "check_suite"]:
            event_config = self.check
            if action and not event_config.actions.get(action, False):
                return False, False

            conclusion = kwargs.get("conclusion", "")
            if conclusion and not event_config.conclusions.get(conclusion, False):
                return False, False

        elif event_type in ["star", "fork", "watch", "create", "delete"]:
            event_config = self.repository
            if not event_config.actions.get(event_type, False):
                return False, False

        # 기본적으로 활성화되지 않은 이벤트 타입
        if event_config is None:
            return False, False

        if not event_config.enabled:
            return False, False

        return event_config.show_system_notification, event_config.show_chat_bubble
