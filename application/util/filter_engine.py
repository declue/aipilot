from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from application.config.config_manager import ConfigManager
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("ui") or logging.getLogger("ui")


class FilterEngine:
    """GitHub 이벤트 알림 표시 여부를 판단하는 엔진"""

    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager: ConfigManager = config_manager

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    def should_show_notification(self, message: Dict[str, Any]) -> Tuple[bool, bool]:
        """설정에 따라 시스템 알림과 채팅 버블 표시 여부를 반환한다.

        반환값: (show_system_notification, show_chat_bubble)
        """
        try:
            settings_json: str = (
                self.config_manager.get_config_value("GITHUB", "notification_settings", "{}")
                or "{}"
            )

            import json

            try:
                settings: Dict[str, Any] = json.loads(settings_json)
            except json.JSONDecodeError:
                # 설정 파싱 실패 시 모두 표시
                return True, True

            # 전역 활성 여부
            if not settings.get("enabled", True):
                return False, False

            # 이벤트 타입 매핑
            event_type: str = message.get("event_type", "")
            payload: Dict[str, Any] = message.get("payload", {})
            action: str = payload.get("action", "")
            event_key: Optional[str] = self._map_event_type(event_type, action, payload)

            events_settings: Dict[str, Any] = settings.get("events", {})

            # 매핑되지 않았거나 설정이 없으면 기본적으로 표시
            if event_key is None or event_key not in events_settings:
                return True, True

            event_config: Dict[str, Any] = events_settings[event_key]

            # 이벤트 비활성화
            if not event_config.get("enabled", True):
                return False, False

            # 액션 필터링
            if event_config.get("actions") and action:
                if not event_config["actions"].get(action, False):
                    return False, False

            # 커스텀 필터 체크
            if not self._check_custom_filters(event_key, event_config, message):
                return False, False

            return (
                event_config.get("show_system_notification", True),
                event_config.get("show_chat_bubble", True),
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("필터링 확인 중 오류: %s", exc)
            # 오류 발생 시 안전하게 모두 표시
            return True, True

    # ------------------------------------------------------------------
    # Internal helpers (private)
    # ------------------------------------------------------------------
    @staticmethod
    def _map_event_type(event_type: str, action: str, payload: Dict[str, Any]) -> Optional[str]:
        """이벤트 타입 문자열을 설정 파일의 키로 매핑한다."""
        if event_type == "push":
            return "push"
        if event_type == "pull_request":
            return "pull_request"
        if event_type == "issues":
            return "issues"
        if event_type == "release":
            return "release"
        if event_type in ("workflow_run", "workflow_job", "check_run", "check_suite"):
            return "workflow"
        if event_type in ("star", "fork", "watch", "create", "delete"):
            return "repository"
        return None

    # pylint: disable=too-many-return-statements,too-many-branches
    def _check_custom_filters(
        self,
        event_key: str,
        event_config: Dict[str, Any],
        message: Dict[str, Any],
    ) -> bool:
        """각 이벤트 타입별 세부 필터링 논리를 수행한다."""
        try:
            payload: Dict[str, Any] = message.get("payload", {})

            if event_key == "push":
                # 커밋 수 필터링
                commits: List[Any] = payload.get("commits", [])
                commit_count = len(commits)
                min_commits = event_config.get("min_commits", 1)
                max_commits = event_config.get("max_commits", 50)
                if commit_count < min_commits or commit_count > max_commits:
                    return False

                # 브랜치 필터링
                ref = payload.get("ref", "")
                branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

                if (exclude := event_config.get("exclude_branches")) and branch in exclude:
                    return False
                if (include := event_config.get("include_branches")) and branch not in include:
                    return False

            elif event_key == "release":
                release = payload.get("release", {})
                if release.get("prerelease", False) and not event_config.get("include_prerelease", True):
                    return False
                if release.get("draft", False) and not event_config.get("include_draft", False):
                    return False

            elif event_key == "workflow":
                workflow_run = (
                    payload.get("workflow_run", {})
                    or payload.get("workflow_job", {})
                    or payload.get("check_run", {})
                    or payload.get("check_suite", {})
                )
                status = workflow_run.get("status", "")
                conclusion = workflow_run.get("conclusion", "")

                actions = event_config.get("actions", {})
                if status and not actions.get(status, False):
                    return False
                if conclusion and not actions.get(conclusion, False):
                    return False

            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("커스텀 필터링 확인 중 오류: %s", exc)
            return True  # 오류 시 필터를 무시하고 표시함 