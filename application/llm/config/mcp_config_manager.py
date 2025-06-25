"""
MCP 설정 관리자
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from application.llm.models.mcp_config import MCPConfig
from application.util.logger import setup_logger

logger = setup_logger("mcp_config_manager") or logging.getLogger("mcp_config_manager")


class MCPConfigManager:
    """MCP 설정 관리자"""

    def __init__(self, config_file: str = "mcp.json"):
        """
        MCP 설정 관리자 초기화

        Args:
            config_file: MCP 설정 파일 경로
        """
        self.config_file = Path(config_file)
        self._config: Optional[MCPConfig] = None
        self.load_config()

    def load_config(self) -> MCPConfig:
        """MCP 설정 로드"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                self._config = MCPConfig.from_dict(config_data)
                logger.info(f"MCP 설정 로드 완료: {self.config_file}")
            else:
                logger.warning(f"MCP 설정 파일을 찾을 수 없습니다: {self.config_file}")
                self._config = MCPConfig()

        except Exception as e:
            logger.error(f"MCP 설정 로드 실패: {e}")
            self._config = MCPConfig()

        return self._config

    def save_config(self, config: MCPConfig) -> bool:
        """MCP 설정 저장"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

            self._config = config
            logger.info(f"MCP 설정 저장 완료: {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"MCP 설정 저장 실패: {e}")
            return False

    def get_config(self) -> MCPConfig:
        """현재 MCP 설정 반환"""
        if self._config is None:
            self.load_config()
        return self._config or MCPConfig()

    def get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """특정 서버 설정 반환"""
        config = self.get_config()
        return config.mcp_servers.get(server_name)

    def update_server_config(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """서버 설정 업데이트"""
        try:
            config = self.get_config()
            config.mcp_servers[server_name] = server_config
            return self.save_config(config)
        except Exception as e:
            logger.error(f"서버 설정 업데이트 실패 {server_name}: {e}")
            return False

    def remove_server_config(self, server_name: str) -> bool:
        """서버 설정 제거"""
        try:
            config = self.get_config()
            if server_name in config.mcp_servers:
                del config.mcp_servers[server_name]
                return self.save_config(config)
            return True
        except Exception as e:
            logger.error(f"서버 설정 제거 실패 {server_name}: {e}")
            return False

    def is_enabled(self) -> bool:
        """MCP 활성화 여부 확인"""
        config = self.get_config()
        return config.enabled

    def set_enabled(self, enabled: bool) -> bool:
        """MCP 활성화 상태 설정"""
        try:
            config = self.get_config()
            config.enabled = enabled
            return self.save_config(config)
        except Exception as e:
            logger.error(f"MCP 활성화 상태 설정 실패: {e}")
            return False
