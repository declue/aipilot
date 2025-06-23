import json
import logging
import os
from typing import Any, Dict, List, Optional

from application.config.apps.managers.app_config_manager import AppConfigManager
from application.config.apps.managers.llm_profile_manager import LLMProfileManager
from application.config.apps.managers.mcp_config_manager import MCPConfigManager
from application.config.github_notification_config import GitHubNotificationConfig
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("config") or logging.getLogger("config")


class UnifiedConfigManager:
    """통합 설정 관리자

    모든 설정 관리자들을 조합하여 하나의 인터페이스로 제공합니다.
    각 설정 영역별로 전용 관리자를 사용하여 단일 책임 원칙을 준수합니다.
    """

    def __init__(
        self,
        app_config_file: Optional[str] = None,
        llm_profiles_file: Optional[str] = None,
        mcp_config_file: Optional[str] = None,
        github_notification_config_file: Optional[str] = None,
    ) -> None:
        """UnifiedConfigManager 생성자

        Args:
            app_config_file: 앱 설정 파일 경로
            llm_profiles_file: LLM 프로필 파일 경로
            mcp_config_file: MCP 설정 파일 경로
            github_notification_config_file: GitHub 알림 설정 파일 경로
        """
        # 각 전용 관리자 초기화
        self.app_config_manager = AppConfigManager(app_config_file)
        self.llm_profile_manager = LLMProfileManager(llm_profiles_file)
        self.mcp_config_manager = MCPConfigManager(mcp_config_file)

        # GitHub 알림 설정 (파일이 지정된 경우만 로드)
        self._github_notification_config: Optional[GitHubNotificationConfig] = None
        self._github_notification_config_file = github_notification_config_file
        if github_notification_config_file:
            self._load_github_notification_config()

        logger.info("통합 설정 관리자 초기화 완료")

    def _load_github_notification_config(self) -> None:
        """GitHub 알림 설정 로드"""
        try:
            if self._github_notification_config_file:
                if os.path.exists(self._github_notification_config_file):
                    with open(self._github_notification_config_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self._github_notification_config = GitHubNotificationConfig.from_dict(
                            data)
                else:
                    # 기본 설정 생성
                    self._github_notification_config = GitHubNotificationConfig()
                    self._save_github_notification_config()
        except Exception as exception:
            logger.error(f"GitHub 알림 설정 로드 실패: {exception}")
            self._github_notification_config = GitHubNotificationConfig()

    def _save_github_notification_config(self) -> None:
        """GitHub 알림 설정 저장"""
        try:
            if self._github_notification_config and self._github_notification_config_file:
                config_dir = os.path.dirname(
                    self._github_notification_config_file)
                if config_dir and not os.path.exists(config_dir):
                    os.makedirs(config_dir, exist_ok=True)

                with open(self._github_notification_config_file, "w", encoding="utf-8") as f:
                    json.dump(self._github_notification_config.to_dict(),
                              f, ensure_ascii=False, indent=2)

                logger.debug(
                    f"GitHub 알림 설정 저장 완료: {self._github_notification_config_file}")
        except Exception as exception:
            logger.error(f"GitHub 알림 설정 저장 실패: {exception}")

    # ========== 앱 설정 관련 메서드들 ==========
    def get_config_value(self, section: str, key: str, fallback: Optional[str] = None) -> Optional[str]:
        """앱 설정값 가져오기"""
        return self.app_config_manager.get_config_value(section, key, fallback)

    def set_config_value(self, section: str, key: str, value: str) -> None:
        """앱 설정값 저장"""
        self.app_config_manager.set_config_value(section, key, value)

    def get_ui_config(self) -> Dict[str, Any]:
        """UI 설정 반환"""
        return self.app_config_manager.get_ui_config()

    def set_ui_config(self, font_family: str, font_size: int, chat_bubble_max_width: int, window_theme: str) -> None:
        """UI 설정 저장"""
        self.app_config_manager.set_ui_config(
            font_family, font_size, chat_bubble_max_width, window_theme)

    def save_ui_config(self, ui_config: Dict[str, Any]) -> None:
        """UI 설정 저장 (딕셔너리 형태)"""
        self.app_config_manager.save_ui_config(ui_config)

    def get_github_repositories(self) -> List[str]:
        """GitHub 저장소 목록 반환"""
        return self.app_config_manager.get_github_repositories()

    def set_github_repositories(self, repositories: List[str]) -> None:
        """GitHub 저장소 목록 설정"""
        self.app_config_manager.set_github_repositories(repositories)

    def get_github_config(self) -> Dict[str, Any]:
        """GitHub 설정 반환"""
        return self.app_config_manager.get_github_config()

    def set_github_config(self, github_config: Dict[str, Any]) -> None:
        """GitHub 설정 저장"""
        self.app_config_manager.set_github_config(github_config)

    # ========== LLM 프로필 관련 메서드들 ==========
    def get_llm_profiles(self) -> Dict[str, Dict[str, Any]]:
        """모든 LLM 프로필 반환"""
        return self.llm_profile_manager.get_llm_profiles()

    def get_current_profile_name(self) -> str:
        """현재 선택된 프로필 이름 반환"""
        return self.llm_profile_manager.get_current_profile_name()

    def set_current_profile(self, profile_name: str) -> None:
        """현재 프로필 설정"""
        self.llm_profile_manager.set_current_profile(profile_name)

    def get_current_profile(self) -> Dict[str, Any]:
        """현재 선택된 프로필 정보 반환"""
        return self.llm_profile_manager.get_current_profile()

    def create_llm_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """새 LLM 프로필 생성"""
        self.llm_profile_manager.create_llm_profile(profile_name, config)

    def update_llm_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """LLM 프로필 업데이트"""
        self.llm_profile_manager.update_llm_profile(profile_name, config)

    def delete_llm_profile(self, profile_name: str) -> None:
        """LLM 프로필 삭제"""
        self.llm_profile_manager.delete_llm_profile(profile_name)

    def profile_exists(self, profile_name: str) -> bool:
        """프로필 존재 여부 확인"""
        return self.llm_profile_manager.profile_exists(profile_name)

    # ========== MCP 설정 관련 메서드들 ==========
    def get_mcp_config(self) -> Dict[str, Any]:
        """전체 MCP 설정 반환"""
        return self.mcp_config_manager.get_config()

    def get_mcp_servers(self) -> Dict[str, Any]:
        """MCP 서버 목록 반환"""
        return self.mcp_config_manager.get_servers()

    def add_mcp_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        """MCP 서버 추가"""
        self.mcp_config_manager.add_server(server_name, server_config)

    def update_mcp_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        """MCP 서버 업데이트"""
        self.mcp_config_manager.update_server(server_name, server_config)

    def remove_mcp_server(self, server_name: str) -> None:
        """MCP 서버 제거"""
        self.mcp_config_manager.remove_server(server_name)

    def get_default_mcp_server(self) -> Optional[str]:
        """기본 MCP 서버 이름 반환"""
        return self.mcp_config_manager.get_default_server()

    def set_default_mcp_server(self, server_name: Optional[str]) -> None:
        """기본 MCP 서버 설정"""
        self.mcp_config_manager.set_default_server(server_name)

    def is_mcp_enabled(self) -> bool:
        """MCP 기능 활성화 여부 반환"""
        return self.mcp_config_manager.is_enabled()

    def set_mcp_enabled(self, enabled: bool) -> None:
        """MCP 기능 활성화/비활성화 설정"""
        self.mcp_config_manager.set_enabled(enabled)

    def mcp_server_exists(self, server_name: str) -> bool:
        """MCP 서버 존재 여부 확인"""
        return self.mcp_config_manager.server_exists(server_name)

    # ========== GitHub 알림 설정 관련 메서드들 ==========
    def get_github_notification_config(self) -> Optional[GitHubNotificationConfig]:
        """GitHub 알림 설정 반환"""
        return self._github_notification_config

    def set_github_notification_config(self, config: GitHubNotificationConfig) -> None:
        """GitHub 알림 설정 저장"""
        self._github_notification_config = config
        self._save_github_notification_config()

    def should_show_github_notification(self, event_type: str, action: Optional[str] = None, **kwargs) -> tuple[bool, bool]:
        """GitHub 알림을 표시할지 여부를 결정"""
        if self._github_notification_config:
            return self._github_notification_config.should_show_notification(event_type, action, **kwargs)
        return False, False

    # ========== 통합 메서드들 ==========
    def reload_all_configs(self) -> None:
        """모든 설정 파일 리로드"""
        try:
            self.app_config_manager.load_config()
            self.llm_profile_manager.load_llm_profiles()
            self.mcp_config_manager.load_config()
            if self._github_notification_config_file:
                self._load_github_notification_config()
            logger.info("모든 설정 파일 리로드 완료")
        except Exception as exception:
            logger.error(f"설정 파일 리로드 실패: {exception}")

    def get_all_config_files(self) -> List[str]:
        """모든 설정 파일 경로 반환"""
        files = [
            self.app_config_manager.config_file,
            self.llm_profile_manager.llm_profiles_file,
            self.mcp_config_manager.config_file,
        ]

        if self._github_notification_config_file:
            files.append(self._github_notification_config_file)

        return files

    def cleanup(self) -> None:
        """리소스 정리"""
        try:
            # 각 관리자가 BaseConfigManager를 상속하면 cleanup 메서드가 있을 것임
            # 현재는 직접 호출하지 않음 (각 관리자의 __del__에서 처리)
            logger.info("통합 설정 관리자 정리 완료")
        except Exception as exception:
            logger.error(f"리소스 정리 실패: {exception}")

    def __del__(self) -> None:
        """소멸자"""
        try:
            self.cleanup()
        except Exception:
            pass
