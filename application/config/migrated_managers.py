"""
기존 설정 관리자들의 새로운 구조 마이그레이션

기존 AppConfigManager, LLMProfileManager, MCPConfigManager를 
새로운 BaseConfigManager 기반으로 재구현합니다.
"""

import logging
from typing import Dict, Any, Optional, List

from .base_config_manager import BaseConfigManager
from .interfaces import ConfigDict
from .validators import LLMConfigValidator, MCPConfigValidator, GitHubConfigValidator
from .default_app_config import DEFAULT_APP_CONFIG_SECTIONS, DEFAULT_UI_VALUES
from .default_llm_profiles import DEFAULT_LLM_PROFILES, DEFAULT_LLM_PROFILE

logger = logging.getLogger(__name__)


class ModernAppConfigManager(BaseConfigManager):
    """현대적인 앱 설정 관리자
    
    새로운 BaseConfigManager 기반으로 재구현된 앱 설정 관리자입니다.
    """
    
    def __init__(self, config_file: Optional[str] = None, **kwargs):
        """ModernAppConfigManager 생성자"""
        config_file = config_file or "app.config"
        
        # GitHub 검증기 추가
        if 'validator' not in kwargs:
            kwargs['validator'] = GitHubConfigValidator()
        
        super().__init__(config_file, **kwargs)
    
    def get_default_config_data(self) -> ConfigDict:
        """기본 설정 데이터 반환"""
        return DEFAULT_APP_CONFIG_SECTIONS.copy()
    
    def create_default_config(self) -> None:
        """기본 설정 생성"""
        self._config_data = self.get_default_config_data()
        self.save_config()
        logger.info("기본 앱 설정 생성 완료: %s", self.config_file)
    
    # ========== UI 설정 관련 메서드들 ==========
    
    def get_ui_config(self) -> Dict[str, Any]:
        """UI 설정 반환"""
        try:
            ui_section = self.get_section("UI")
            
            # 타입 변환 및 검증
            font_size = int(ui_section.get("font_size", DEFAULT_UI_VALUES["font_size"]))
            chat_bubble_max_width = int(ui_section.get("chat_bubble_max_width", DEFAULT_UI_VALUES["chat_bubble_max_width"]))
            
            return {
                "font_family": ui_section.get("font_family", DEFAULT_UI_VALUES["font_family"]),
                "font_size": font_size,
                "chat_bubble_max_width": chat_bubble_max_width,
                "window_theme": ui_section.get("window_theme", DEFAULT_UI_VALUES["window_theme"]),
            }
        except Exception as e:
            logger.error("UI 설정 가져오기 실패: %s", e)
            return DEFAULT_UI_VALUES.copy()
    
    def set_ui_config(self, font_family: str, font_size: int, chat_bubble_max_width: int, window_theme: str) -> None:
        """UI 설정 저장"""
        try:
            ui_config = {
                "font_family": font_family,
                "font_size": str(font_size),
                "chat_bubble_max_width": str(chat_bubble_max_width),
                "window_theme": window_theme,
            }
            self.set_section("UI", ui_config)
            self.save_config()
            logger.info("UI 설정 저장 완료")
        except Exception as e:
            logger.error("UI 설정 저장 실패: %s", e)
            raise
    
    def save_ui_config(self, ui_config: Dict[str, Any]) -> None:
        """UI 설정 저장 (딕셔너리 형태)"""
        try:
            font_family = ui_config.get("font_family", DEFAULT_UI_VALUES["font_family"])
            font_size = int(ui_config.get("font_size", DEFAULT_UI_VALUES["font_size"]))
            chat_bubble_max_width = int(ui_config.get("chat_bubble_max_width", DEFAULT_UI_VALUES["chat_bubble_max_width"]))
            window_theme = ui_config.get("window_theme", DEFAULT_UI_VALUES["window_theme"])
            
            self.set_ui_config(font_family, font_size, chat_bubble_max_width, window_theme)
        except Exception as e:
            logger.error("UI 설정 딕셔너리 저장 실패: %s", e)
            raise
    
    # ========== GitHub 설정 관련 메서드들 ==========
    
    def get_github_repositories(self) -> List[str]:
        """GitHub 저장소 목록 반환"""
        try:
            repositories_str = self.get_value("GITHUB.repositories", "")
            if repositories_str:
                return [repo.strip() for repo in repositories_str.split(",") if repo.strip()]
            return []
        except Exception as e:
            logger.error("GitHub 저장소 목록 가져오기 실패: %s", e)
            return []
    
    def set_github_repositories(self, repositories: List[str]) -> None:
        """GitHub 저장소 목록 설정"""
        try:
            repositories_str = ",".join(repositories)
            self.set_value("GITHUB.repositories", repositories_str)
            self.save_config()
            logger.info("GitHub 저장소 목록 설정 완료: %s개", len(repositories))
        except Exception as e:
            logger.error("GitHub 저장소 목록 설정 실패: %s", e)
            raise
    
    def get_github_config(self) -> Dict[str, Any]:
        """GitHub 설정 반환"""
        try:
            webhook_enabled_str = self.get_value("GITHUB.webhook_enabled", "false")
            webhook_port_str = self.get_value("GITHUB.webhook_port", "8000")
            
            webhook_enabled = webhook_enabled_str.lower() in ("true", "1", "yes", "on")
            
            try:
                webhook_port = int(webhook_port_str)
                if webhook_port <= 0 or webhook_port > 65535:
                    webhook_port = 8000
            except (ValueError, TypeError):
                webhook_port = 8000
            
            return {
                "repositories": self.get_github_repositories(),
                "webhook_enabled": webhook_enabled,
                "webhook_port": webhook_port,
            }
        except Exception as e:
            logger.error("GitHub 설정 가져오기 실패: %s", e)
            return {
                "repositories": [],
                "webhook_enabled": False,
                "webhook_port": 8000,
            }
    
    def set_github_config(self, github_config: Dict[str, Any]) -> None:
        """GitHub 설정 저장"""
        try:
            if "repositories" in github_config:
                self.set_github_repositories(github_config["repositories"])
            
            if "webhook_enabled" in github_config:
                self.set_value("GITHUB.webhook_enabled", str(github_config["webhook_enabled"]).lower())
            
            if "webhook_port" in github_config:
                port = int(github_config["webhook_port"])
                if 1 <= port <= 65535:
                    self.set_value("GITHUB.webhook_port", str(port))
                else:
                    raise ValueError(f"잘못된 포트 번호: {port}")
            
            self.save_config()
            logger.info("GitHub 설정 저장 완료")
        except Exception as e:
            logger.error("GitHub 설정 저장 실패: %s", e)
            raise


class ModernLLMProfileManager(BaseConfigManager):
    """현대적인 LLM 프로필 관리자
    
    새로운 BaseConfigManager 기반으로 재구현된 LLM 프로필 관리자입니다.
    """
    
    def __init__(self, profiles_file: Optional[str] = None, **kwargs):
        """ModernLLMProfileManager 생성자"""
        profiles_file = profiles_file or "llm_profiles.json"
        
        # LLM 검증기 추가
        if 'validator' not in kwargs:
            kwargs['validator'] = LLMConfigValidator()
        
        super().__init__(profiles_file, **kwargs)
        self._current_profile_name = DEFAULT_LLM_PROFILE
    
    def get_default_config_data(self) -> ConfigDict:
        """기본 설정 데이터 반환"""
        return {
            "profiles": DEFAULT_LLM_PROFILES.copy(),
            "current_profile": DEFAULT_LLM_PROFILE,
        }
    
    def create_default_config(self) -> None:
        """기본 설정 생성"""
        self._config_data = self.get_default_config_data()
        self._current_profile_name = DEFAULT_LLM_PROFILE
        self.save_config()
        logger.info("기본 LLM 프로필 생성 완료: %s", self.config_file)
    
    def on_after_load(self) -> None:
        """로드 후 처리"""
        super().on_after_load()
        self._current_profile_name = self.get_value("current_profile", DEFAULT_LLM_PROFILE)
    
    # ========== LLM 프로필 관련 메서드들 ==========
    
    def get_llm_profiles(self) -> Dict[str, Dict[str, Any]]:
        """모든 LLM 프로필 반환"""
        return self.get_value("profiles", {})
    
    def get_current_profile_name(self) -> str:
        """현재 선택된 프로필 이름 반환"""
        return self._current_profile_name
    
    def set_current_profile(self, profile_name: str) -> None:
        """현재 프로필 설정"""
        profiles = self.get_llm_profiles()
        if profile_name not in profiles:
            raise ValueError(f"프로필 '{profile_name}'을 찾을 수 없습니다")
        
        self._current_profile_name = profile_name
        self.set_value("current_profile", profile_name)
        self.save_config()
        logger.info("현재 프로필을 '%s'으로 변경", profile_name)
    
    def get_current_profile(self) -> Dict[str, Any]:
        """현재 선택된 프로필 정보 반환"""
        profiles = self.get_llm_profiles()
        return profiles.get(self._current_profile_name, {})
    
    def create_llm_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """새 LLM 프로필 생성"""
        profiles = self.get_llm_profiles()
        if profile_name in profiles:
            raise ValueError(f"프로필 '{profile_name}'이 이미 존재합니다")
        
        profiles[profile_name] = config
        self.set_value("profiles", profiles)
        self.save_config()
        logger.info("새 LLM 프로필 '%s' 생성 완료", profile_name)
    
    def update_llm_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """LLM 프로필 업데이트"""
        profiles = self.get_llm_profiles()
        if profile_name not in profiles:
            raise ValueError(f"프로필 '{profile_name}'을 찾을 수 없습니다")
        
        profiles[profile_name].update(config)
        self.set_value("profiles", profiles)
        self.save_config()
        logger.info("LLM 프로필 '%s' 업데이트 완료", profile_name)
    
    def delete_llm_profile(self, profile_name: str) -> None:
        """LLM 프로필 삭제"""
        profiles = self.get_llm_profiles()
        if profile_name not in profiles:
            raise ValueError(f"프로필 '{profile_name}'을 찾을 수 없습니다")
        
        if profile_name == "default":
            raise ValueError("'default' 프로필은 삭제할 수 없습니다")
        
        if self._current_profile_name == profile_name:
            self.set_current_profile(DEFAULT_LLM_PROFILE)
        
        del profiles[profile_name]
        self.set_value("profiles", profiles)
        self.save_config()
        logger.info("LLM 프로필 '%s' 삭제 완료", profile_name)
    
    def profile_exists(self, profile_name: str) -> bool:
        """프로필 존재 여부 확인"""
        profiles = self.get_llm_profiles()
        return profile_name in profiles


class ModernMCPConfigManager(BaseConfigManager):
    """현대적인 MCP 설정 관리자
    
    새로운 BaseConfigManager 기반으로 재구현된 MCP 설정 관리자입니다.
    """
    
    def __init__(self, config_file: Optional[str] = None, **kwargs):
        """ModernMCPConfigManager 생성자"""
        config_file = config_file or "mcp.json"
        
        # MCP 검증기 추가
        if 'validator' not in kwargs:
            kwargs['validator'] = MCPConfigValidator()
        
        super().__init__(config_file, **kwargs)
    
    def get_default_config_data(self) -> ConfigDict:
        """기본 설정 데이터 반환"""
        return {
            "mcpServers": {},
            "defaultServer": None,
            "enabled": True,
        }
    
    def create_default_config(self) -> None:
        """기본 설정 생성"""
        self._config_data = self.get_default_config_data()
        self.save_config()
        logger.info("기본 MCP 설정 생성 완료: %s", self.config_file)
    
    # ========== MCP 설정 관련 메서드들 ==========
    
    def get_servers(self) -> Dict[str, Any]:
        """MCP 서버 목록 반환"""
        return self.get_value("mcpServers", {})
    
    def add_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        """MCP 서버 추가"""
        if not server_name or not server_name.strip():
            raise ValueError("서버 이름은 필수 입력값입니다")
        
        servers = self.get_servers()
        if server_name in servers:
            raise ValueError(f"서버 '{server_name}'이 이미 존재합니다")
        
        servers[server_name] = server_config
        self.set_value("mcpServers", servers)
        self.save_config()
        logger.info("MCP 서버 '%s' 추가 완료", server_name)
    
    def update_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        """MCP 서버 업데이트"""
        servers = self.get_servers()
        if server_name not in servers:
            raise ValueError(f"서버 '{server_name}'을 찾을 수 없습니다")
        
        servers[server_name].update(server_config)
        self.set_value("mcpServers", servers)
        self.save_config()
        logger.info("MCP 서버 '%s' 업데이트 완료", server_name)
    
    def remove_server(self, server_name: str) -> None:
        """MCP 서버 제거"""
        servers = self.get_servers()
        if server_name not in servers:
            raise ValueError(f"서버 '{server_name}'을 찾을 수 없습니다")
        
        # 기본 서버였다면 해제
        if self.get_value("defaultServer") == server_name:
            self.set_value("defaultServer", None)
        
        del servers[server_name]
        self.set_value("mcpServers", servers)
        self.save_config()
        logger.info("MCP 서버 '%s' 제거 완료", server_name)
    
    def get_default_server(self) -> Optional[str]:
        """기본 서버 이름 반환"""
        return self.get_value("defaultServer")
    
    def set_default_server(self, server_name: Optional[str]) -> None:
        """기본 서버 설정"""
        if server_name is not None:
            servers = self.get_servers()
            if server_name not in servers:
                raise ValueError(f"서버 '{server_name}'을 찾을 수 없습니다")
        
        self.set_value("defaultServer", server_name)
        self.save_config()
        logger.info("기본 MCP 서버를 '%s'으로 설정", server_name)
    
    def is_enabled(self) -> bool:
        """MCP 기능 활성화 여부 반환"""
        return bool(self.get_value("enabled", True))
    
    def set_enabled(self, enabled: bool) -> None:
        """MCP 기능 활성화/비활성화 설정"""
        self.set_value("enabled", enabled)
        self.save_config()
        status = "활성화" if enabled else "비활성화"
        logger.info("MCP 기능 %s", status)
    
    def server_exists(self, server_name: str) -> bool:
        """서버 존재 여부 확인"""
        servers = self.get_servers()
        return server_name in servers 