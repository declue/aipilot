import json
import logging
import os
from typing import Any, Dict, Optional

from dspilot_core.util.logger import setup_logger

logger: logging.Logger = setup_logger("config") or logging.getLogger("config")


class MCPConfigManager:
    """MCP(Model Context Protocol) 설정 관리 클래스

    mcp.json 파일을 통해 MCP 서버 설정들을 관리합니다.
    단일 책임 원칙에 따라 MCP 설정 관리만을 담당합니다.
    """

    def __init__(self, config_file: Optional[str] = None) -> None:
        """MCPConfigManager 생성자

        Args:
            config_file: MCP 설정 파일 경로. None인 경우 기본값 사용
        """
        self.config_file = config_file or "mcp.json"
        self._mcp_config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """MCP 설정 파일 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._mcp_config = json.load(f)
                    logger.debug(f"MCP 설정 로드 완료: {self.config_file}")
            else:
                # 기본 MCP 설정 생성
                self.create_default_config()
        except (json.JSONDecodeError, UnicodeDecodeError) as exception:
            # 파일이 있지만 파싱에 실패한 경우, 원본 파일을 보존하고 예외를 다시 던집니다
            logger.error(f"MCP 설정 파일 파싱 실패 (원본 파일 보존): {exception}")
            logger.error(f"MCP 설정 파일 경로: {self.config_file}")
            raise RuntimeError(f"MCP 설정 파일 '{self.config_file}' 파싱에 실패했습니다. 원본 파일을 확인하고 수정해주세요.") from exception
        except PermissionError as exception:
            logger.error(f"MCP 설정 파일 접근 권한 없음: {exception}")
            # 권한 문제 시 메모리에서만 기본 설정 사용 (원본 파일 훼손 없음)
            self._mcp_config = {
                "mcpServers": {},
                "defaultServer": None,
                "enabled": True,
            }
            logger.warning("권한 문제로 인해 메모리에서 기본 MCP 설정을 사용합니다")
        except Exception as exception:
            logger.error(f"MCP 설정 로드 중 예상치 못한 오류: {exception}")
            raise RuntimeError(f"MCP 설정 파일 '{self.config_file}' 로드 중 예상치 못한 오류가 발생했습니다.") from exception

    def create_default_config(self) -> None:
        """기본 MCP 설정 생성"""
        try:
            self._mcp_config = {
                "mcpServers": {},
                "defaultServer": None,
                "enabled": True,
            }
            self.save_config()
            logger.debug("기본 MCP 설정 생성 완료")
        except Exception as exception:
            logger.error(f"기본 MCP 설정 생성 실패: {exception}")
            # 파일 저장에 실패해도 메모리에서는 기본 설정 사용
            if not self._mcp_config:
                self._mcp_config = {
                    "mcpServers": {},
                    "defaultServer": None,
                    "enabled": True,
                }

    def save_config(self) -> None:
        """MCP 설정 파일 저장"""
        try:
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._mcp_config, f, ensure_ascii=False, indent=2)
            logger.debug(f"MCP 설정 저장 완료: {self.config_file}")
        except PermissionError as exception:
            logger.error(f"MCP 설정 파일 저장 권한 없음: {exception}")
            raise
        except Exception as exception:
            logger.error(f"MCP 설정 저장 실패: {exception}")
            raise

    def get_config(self) -> Dict[str, Any]:
        """전체 MCP 설정 반환"""
        return self._mcp_config.copy()

    def get_servers(self) -> Dict[str, Any]:
        """MCP 서버 목록 반환"""
        return self._mcp_config.get("mcpServers", {})

    def add_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        """MCP 서버 추가

        Args:
            server_name: 서버 이름
            server_config: 서버 설정

        Raises:
            ValueError: 서버 이름이 비어있거나 이미 존재하는 경우
        """
        if not server_name or not server_name.strip():
            raise ValueError("서버 이름은 필수 입력값입니다")

        if server_name in self._mcp_config.get("mcpServers", {}):
            raise ValueError(f"서버 '{server_name}'이 이미 존재합니다")

        if "mcpServers" not in self._mcp_config:
            self._mcp_config["mcpServers"] = {}

        self._mcp_config["mcpServers"][server_name] = server_config
        self.save_config()
        logger.info(f"MCP 서버 '{server_name}' 추가 완료")

    def update_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        """MCP 서버 업데이트

        Args:
            server_name: 서버 이름
            server_config: 업데이트할 서버 설정

        Raises:
            ValueError: 서버가 존재하지 않는 경우
        """
        if server_name not in self._mcp_config.get("mcpServers", {}):
            raise ValueError(f"서버 '{server_name}'을 찾을 수 없습니다")

        self._mcp_config["mcpServers"][server_name].update(server_config)
        self.save_config()
        logger.info(f"MCP 서버 '{server_name}' 업데이트 완료")

    def remove_server(self, server_name: str) -> None:
        """MCP 서버 제거

        Args:
            server_name: 제거할 서버 이름

        Raises:
            ValueError: 서버가 존재하지 않는 경우
        """
        if server_name not in self._mcp_config.get("mcpServers", {}):
            raise ValueError(f"서버 '{server_name}'을 찾을 수 없습니다")

        # 기본 서버였다면 해제
        if self._mcp_config.get("defaultServer") == server_name:
            self._mcp_config["defaultServer"] = None

        del self._mcp_config["mcpServers"][server_name]
        self.save_config()
        logger.info(f"MCP 서버 '{server_name}' 제거 완료")

    def get_default_server(self) -> Optional[str]:
        """기본 서버 이름 반환"""
        return self._mcp_config.get("defaultServer")

    def set_default_server(self, server_name: Optional[str]) -> None:
        """기본 서버 설정

        Args:
            server_name: 기본으로 설정할 서버 이름. None인 경우 기본 서버 해제

        Raises:
            ValueError: 서버가 존재하지 않는 경우
        """
        if server_name is not None:
            if server_name not in self._mcp_config.get("mcpServers", {}):
                raise ValueError(f"서버 '{server_name}'을 찾을 수 없습니다")

        self._mcp_config["defaultServer"] = server_name
        self.save_config()
        logger.info(f"기본 MCP 서버를 '{server_name}'으로 설정")

    def is_enabled(self) -> bool:
        """MCP 기능 활성화 여부 반환"""
        return self._mcp_config.get("enabled", True)

    def set_enabled(self, enabled: bool) -> None:
        """MCP 기능 활성화/비활성화 설정

        Args:
            enabled: 활성화 여부
        """
        self._mcp_config["enabled"] = enabled
        self.save_config()
        status = "활성화" if enabled else "비활성화"
        logger.info(f"MCP 기능 {status}")

    def server_exists(self, server_name: str) -> bool:
        """서버 존재 여부 확인

        Args:
            server_name: 확인할 서버 이름

        Returns:
            서버 존재 여부
        """
        return server_name in self._mcp_config.get("mcpServers", {})
