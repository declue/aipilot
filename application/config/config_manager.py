import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

from application.config.apps.managers.app_config_manager import AppConfigManager
from application.config.apps.managers.llm_profile_manager import LLMProfileManager
from application.config.libs.config_change_notifier import (
    ConfigChangeCallback,
    get_config_change_notifier,
)
from application.llm.mcp.config.mcp_config_manager import MCPConfigManager
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("config") or logging.getLogger("config")


class ConfigManager:
    """통합 설정 관리 클래스"""

    def __init__(self, config_file: Optional[str] = None) -> None:
        """ConfigManager 생성자"""
        self._lock = threading.RLock()
        self._change_callbacks: List[ConfigChangeCallback] = []
        self._file_change_notifier = get_config_change_notifier()

        # 컴포지션을 통한 책임 분리
        self.app_config_manager = AppConfigManager(config_file)
        self.llm_profile_manager = LLMProfileManager()
        # MCP 설정 관리자 (기존 코드와의 호환성 확보)
        self.mcp_config_manager = MCPConfigManager()

        # 기존 인터페이스 호환성을 위한 속성들
        self.config_file = self.app_config_manager.config_file
        self.config = self.app_config_manager.config
        self.llm_profiles_file = self.llm_profile_manager.llm_profiles_file
        self._llm_profiles = self.llm_profile_manager._llm_profiles
        self._current_profile_name = self.llm_profile_manager._current_profile_name

        # 파일 변경 감지 설정
        self._setup_file_watching()

    def _setup_file_watching(self) -> None:
        """파일 변경 감지 설정"""
        try:
            # app.config 파일 감시
            if self.config_file:
                self._file_change_notifier.register_callback(
                    self.config_file, self._on_app_config_changed
                )
                logger.debug(f"app.config 파일 감시 시작: {self.config_file}")

            # llm_profiles.json 파일 감시
            if self.llm_profiles_file:
                self._file_change_notifier.register_callback(
                    self.llm_profiles_file, self._on_llm_profiles_changed
                )
                logger.debug(f"LLM 프로필 파일 감시 시작: {self.llm_profiles_file}")
        except Exception as e:
            logger.warning(f"파일 감시 설정 실패: {e}")

    def _on_app_config_changed(self, file_path: str, change_type: str) -> None:
        """app.config 파일 변경 시 콜백"""
        logger.info(f"app.config 파일 변경 감지: {change_type}")

        try:
            with self._lock:
                if change_type in ["modified", "created"]:
                    self.app_config_manager.load_config()
                    self.config = self.app_config_manager.config  # 참조 동기화

                    # 등록된 콜백들에게 알림
                    self._notify_config_changed(file_path, change_type)
                    logger.debug("app.config 리로드 완료")

                elif change_type == "deleted":
                    logger.warning("app.config 파일이 삭제됨, 기본 설정으로 복원")
                    self.app_config_manager.create_default_config()
                    self.config = self.app_config_manager.config
                    self._notify_config_changed(file_path, change_type)

        except Exception as e:
            logger.error(f"app.config 리로드 중 오류: {e}")

    def _on_llm_profiles_changed(self, file_path: str, change_type: str) -> None:
        """llm_profiles.json 파일 변경 시 콜백"""
        logger.info(f"LLM 프로필 파일 변경 감지: {change_type}")

        try:
            with self._lock:
                if change_type in ["modified", "created"]:
                    # 프로필 리로드
                    self.llm_profile_manager.load_llm_profiles()
                    # 참조 동기화
                    self._llm_profiles = (
                        self.llm_profile_manager._llm_profiles
                    )  # pylint: disable=protected-access
                    self._current_profile_name = (
                        self.llm_profile_manager._current_profile_name
                    )  # pylint: disable=protected-access

                    # 등록된 콜백들에게 알림
                    self._notify_config_changed(file_path, change_type)
                    logger.debug("LLM 프로필 리로드 완료")

                elif change_type == "deleted":
                    logger.warning("LLM 프로필 파일이 삭제됨, 기본 프로필로 복원")
                    self.llm_profile_manager.create_default_llm_profiles()
                    self._llm_profiles = (
                        self.llm_profile_manager._llm_profiles
                    )  # pylint: disable=protected-access
                    self._current_profile_name = (
                        self.llm_profile_manager._current_profile_name
                    )  # pylint: disable=protected-access
                    self._notify_config_changed(file_path, change_type)

        except Exception as e:
            logger.error(f"LLM 프로필 리로드 중 오류: {e}")

    def _notify_config_changed(self, file_path: str, change_type: str) -> None:
        """등록된 콜백들에게 설정 변경 알림"""
        for callback in self._change_callbacks.copy():
            try:
                callback(file_path, change_type)
            except Exception as e:
                logger.error(f"설정 변경 콜백 실행 중 오류: {e}")

    def register_change_callback(self, callback: ConfigChangeCallback) -> None:
        """설정 변경 콜백 등록"""
        with self._lock:
            if callback not in self._change_callbacks:
                self._change_callbacks.append(callback)
                logger.debug("설정 변경 콜백 등록됨")

    def unregister_change_callback(self, callback: ConfigChangeCallback) -> None:
        """설정 변경 콜백 해제"""
        with self._lock:
            try:
                self._change_callbacks.remove(callback)
                logger.debug("설정 변경 콜백 해제됨")
            except ValueError:
                pass

    def force_reload(self) -> None:
        """강제로 모든 설정 파일 리로드"""
        logger.info("설정 파일 강제 리로드 시작")

        try:
            with self._lock:
                # app.config 리로드
                self.app_config_manager.load_config()
                self.config = self.app_config_manager.config

                # llm_profiles.json 리로드
                self.llm_profile_manager.load_llm_profiles()
                self._llm_profiles = (
                    self.llm_profile_manager._llm_profiles
                )  # pylint: disable=protected-access
                self._current_profile_name = (
                    self.llm_profile_manager._current_profile_name
                )  # pylint: disable=protected-access

                # 콜백 알림
                self._notify_config_changed("manual_reload", "forced")
                logger.info("설정 파일 강제 리로드 완료")

        except Exception as e:
            logger.error(f"강제 리로드 중 오류: {e}")
            raise

    def load_config(self) -> None:
        """설정 파일 로드 - AppConfigManager에 위임"""
        with self._lock:
            self.app_config_manager.load_config()
            self.config = self.app_config_manager.config  # 참조 동기화

    def create_default_config(self) -> None:
        """기본 설정 생성 - AppConfigManager에 위임"""
        self.app_config_manager.create_default_config()

    def save_config(self) -> None:
        """설정 파일 저장 - AppConfigManager에 위임"""
        self.app_config_manager.save_config()

    def load_llm_profiles(self) -> None:
        """LLM 프로필 로드 - LLMProfileManager에 위임"""
        with self._lock:
            self.llm_profile_manager.load_llm_profiles()
            # 참조 동기화
            self._llm_profiles = (
                self.llm_profile_manager._llm_profiles
            )  # pylint: disable=protected-access
            self._current_profile_name = (
                self.llm_profile_manager._current_profile_name
            )  # pylint: disable=protected-access

    def create_default_llm_profiles(self) -> None:
        """기본 LLM 프로필 생성 - LLMProfileManager에 위임"""
        self.llm_profile_manager.create_default_llm_profiles()
        # 참조 동기화
        self._llm_profiles = (
            self.llm_profile_manager._llm_profiles
        )  # pylint: disable=protected-access
        self._current_profile_name = (
            self.llm_profile_manager._current_profile_name
        )  # pylint: disable=protected-access

    def save_llm_profiles(self) -> None:
        """LLM 프로필 저장 - LLMProfileManager에 위임"""
        self.llm_profile_manager.save_llm_profiles()

    def get_llm_profiles(self) -> Dict[str, Dict[str, Any]]:
        """LLM 프로필 목록 반환 - LLMProfileManager에 위임"""
        with self._lock:
            # 최신 데이터 확인을 위해 필요시 리로드
            return self.llm_profile_manager.get_llm_profiles()

    def get_current_profile_name(self) -> str:
        """현재 프로필 이름 반환 - LLMProfileManager에 위임"""
        with self._lock:
            return self.llm_profile_manager.get_current_profile_name()

    def set_current_profile(self, profile_name: str) -> None:
        """현재 프로필 설정 - LLMProfileManager에 위임하고 app.config에도 저장"""
        with self._lock:
            self.llm_profile_manager.set_current_profile(profile_name)

            # 기본 설정 파일에도 저장 (기존 동작 유지)
            if "LLM" not in self.config:
                self.config.add_section("LLM")
            self.config["LLM"]["current_profile"] = profile_name
            self.save_config()

            # 참조 동기화
            self._current_profile_name = (
                self.llm_profile_manager._current_profile_name
            )  # pylint: disable=protected-access

    def get_llm_config(self) -> Dict[str, Any]:
        """LLM 설정 반환 - 프로필 우선, 하위 호환성 유지"""
        with self._lock:
            try:
                self.load_config()
                self.load_llm_profiles()

                # 현재 프로필 가져오기
                current_profile = self.llm_profile_manager.get_current_profile()
                if current_profile:
                    return {
                        "api_key": current_profile.get("api_key", "your-api-key-here"),
                        "base_url": current_profile.get("base_url", "http://localhost:11434/v1"),
                        "model": current_profile.get("model", "llama3.2"),
                        "temperature": current_profile.get("temperature", 0.7),
                        "max_tokens": current_profile.get("max_tokens", 100000),
                        "top_k": current_profile.get("top_k", 50),
                        "instruction_file": current_profile.get(
                            "instruction_file",
                            "instructions/default_agent_instructions.txt",
                        ),
                        "mode": current_profile.get("mode", "basic"),
                        "workflow": current_profile.get("workflow", None),
                        "show_cot": current_profile.get("show_cot", "false"),
                        "react_max_turns": current_profile.get("react_max_turns", "5"),
                        "llm_retry_attempts": current_profile.get("llm_retry_attempts", "3"),
                        "retry_backoff_sec": current_profile.get("retry_backoff_sec", "1"),
                    }
                else:
                    # 프로필이 없으면 기본 설정에서 가져오기 (하위 호환성)
                    return {
                        "api_key": self.config.get("LLM", "api_key", fallback="your-api-key-here"),
                        "base_url": self.config.get(
                            "LLM", "base_url", fallback="http://localhost:11434/v1"
                        ),
                        "model": self.config.get("LLM", "model", fallback="llama3.2"),
                        "temperature": float(self.config.get("LLM", "temperature", fallback="0.7")),
                        "max_tokens": int(self.config.get("LLM", "max_tokens", fallback="100000")),
                        "top_k": int(self.config.get("LLM", "top_k", fallback="50")),
                        "instruction_file": self.config.get(
                            "LLM",
                            "instruction_file",
                            fallback="instructions/default_agent_instructions.txt",
                        ),
                        "mode": self.config.get("LLM", "mode", fallback="basic"),
                        "workflow": self.config.get("LLM", "workflow", fallback=None),
                        "show_cot": self.config.get("LLM", "show_cot", fallback="false"),
                        "react_max_turns": self.config.get("LLM", "react_max_turns", fallback="5"),
                        "llm_retry_attempts": self.config.get(
                            "LLM", "llm_retry_attempts", fallback="3"
                        ),
                        "retry_backoff_sec": self.config.get(
                            "LLM", "retry_backoff_sec", fallback="1"
                        ),
                    }
            except Exception as exception:
                logger.error("LLM 설정 가져오기 실패: %s", exception)
                return {
                    "api_key": "your-api-key-here",
                    "base_url": "http://localhost:11434/v1",
                    "model": "llama3.2",
                    "temperature": 0.7,
                    "max_tokens": 100000,
                    "top_k": 50,
                    "instruction_file": "instructions/default_agent_instructions.txt",
                    "mode": "basic",
                    "workflow": None,
                    "show_cot": "false",
                    "react_max_turns": "5",
                    "llm_retry_attempts": "3",
                    "retry_backoff_sec": "1",
                }

    def create_llm_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """새 LLM 프로필 생성 - LLMProfileManager에 위임"""
        with self._lock:
            self.llm_profile_manager.create_llm_profile(profile_name, config)
            # 참조 동기화
            self._llm_profiles = (
                self.llm_profile_manager._llm_profiles
            )  # pylint: disable=protected-access

    def update_llm_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """LLM 프로필 업데이트 - LLMProfileManager에 위임"""
        with self._lock:
            self.llm_profile_manager.update_llm_profile(profile_name, config)
            # 참조 동기화
            self._llm_profiles = (
                self.llm_profile_manager._llm_profiles
            )  # pylint: disable=protected-access

    def delete_llm_profile(self, profile_name: str) -> None:
        """LLM 프로필 삭제 - LLMProfileManager에 위임"""
        with self._lock:
            self.llm_profile_manager.delete_llm_profile(profile_name)
            # 참조 동기화
            self._llm_profiles = (
                self.llm_profile_manager._llm_profiles
            )  # pylint: disable=protected-access
            self._current_profile_name = (
                self.llm_profile_manager._current_profile_name
            )  # pylint: disable=protected-access

    def set_llm_config(self, api_key: str, base_url: str, model: str) -> None:
        """LLM 설정 저장 - AppConfigManager에 위임"""
        try:
            if not api_key or not base_url or not model:
                raise ValueError("API 키, 베이스 URL, 모델은 필수 입력값입니다")

            if "LLM" not in self.config:
                self.config.add_section("LLM")

            self.config["LLM"]["api_key"] = api_key
            self.config["LLM"]["base_url"] = base_url
            self.config["LLM"]["model"] = model
            self.save_config()
            logger.info("LLM 설정 저장 완료")
        except ValueError as exception:
            logger.error("LLM 설정 값 오류: %s", exception)
            raise
        except Exception as exception:
            logger.error("LLM 설정 저장 실패: %s", exception)
            raise

    def get_ui_config(self) -> Dict[str, Any]:
        """UI 설정 반환 - AppConfigManager에 위임"""
        with self._lock:
            return self.app_config_manager.get_ui_config()

    def set_ui_config(
        self,
        font_family: str,
        font_size: int,
        chat_bubble_max_width: int,
        window_theme: str,
    ) -> None:
        """UI 설정 저장 - AppConfigManager에 위임"""
        self.app_config_manager.set_ui_config(
            font_family, font_size, chat_bubble_max_width, window_theme
        )

    def get_config_value(
        self, section: str, key: str, fallback: Optional[str] = None
    ) -> Optional[str]:
        """설정값 가져오기 - AppConfigManager에 위임"""
        with self._lock:
            return self.app_config_manager.get_config_value(section, key, fallback)

    def set_config_value(self, section: str, key: str, value: str) -> None:
        """설정값 저장 - AppConfigManager에 위임"""
        self.app_config_manager.set_config_value(section, key, value)

    def get_github_repositories(self) -> List[str]:
        """GitHub 저장소 목록 반환 - AppConfigManager에 위임"""
        with self._lock:
            return self.app_config_manager.get_github_repositories()

    def set_github_repositories(self, repositories: List[str]) -> None:
        """GitHub 저장소 목록 설정 - AppConfigManager에 위임"""
        self.app_config_manager.set_github_repositories(repositories)

    def get_instruction_path(self) -> str:
        """지시 사항 파일 경로 반환"""
        if "llm" in self.config and "instruction_file" in self.config["llm"]:
            return self.config["llm"]["instruction_file"]
        return os.path.join(os.getcwd(), "instructions", "default_agent_instructions.txt")

    def get_instruction_content(self) -> str:
        """지시 사항 내용 반환"""
        instruction_file = self.get_instruction_path()
        try:
            # 파일이 존재하는지 확인
            if instruction_file and not os.path.exists(instruction_file):
                logger.warning(f"Instruction 파일이 존재하지 않습니다: {instruction_file}")
                return self._get_default_instruction_content()

            # 파일 읽기
            if instruction_file:
                with open(instruction_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        logger.warning(f"Instruction 파일이 비어있습니다: {instruction_file}")
                        return self._get_default_instruction_content()

                    logger.debug(f"Instruction 파일 로드 성공: {instruction_file}")
                    return content
            else:
                return self._get_default_instruction_content()
        except Exception as exception:
            logger.error(f"Instruction 파일 읽기 실패: {exception}")
            return self._get_default_instruction_content()

    def _get_default_instruction_content(self) -> str:
        """기본 지시 사항 내용 반환"""
        return """도구를 사용하여 질문에 답하세요. 반드시 한국어로 응답하세요.

=== GitHub 관련 질문 처리 규칙 ===
GitHub 관련 키워드("이슈", "issue", "PR", "pull request", "커밋", "commit" 등)가 포함된 질문을 받으면:
1. 반드시 GitHub 도구를 사용하세요
2. 구체적인 저장소가 명시되지 않은 경우, 관심 저장소들을 대상으로 하세요
3. "현재 open 상태인 이슈" 같은 질문은 관심 저장소들의 open 이슈를 검색하세요
"""

    def set_current_profile_name(self, profile_name: str) -> None:
        """현재 프로필 이름 설정 (하위 호환성)"""
        if "llm" not in self.config:
            self.config["llm"] = {}
        self.config["llm"]["current_profile"] = profile_name
        self.save_config()
        logger.info(f"LLM 프로필이 '{profile_name}'(으)로 변경되었습니다.")

    def save_ui_config(self, ui_config: Dict[str, Any]) -> None:
        """UI 설정 저장 - AppConfigManager에 위임"""
        self.app_config_manager.save_ui_config(ui_config)
        self.load_ui_config()

    def load_ui_config(self) -> None:
        """UI 설정 로드 - 기존 호환성 유지"""

    def cleanup(self) -> None:
        """리소스 정리"""
        try:
            # 파일 감시 해제
            if self.config_file:
                self._file_change_notifier.unregister_all_callbacks(self.config_file)
            if self.llm_profiles_file:
                self._file_change_notifier.unregister_all_callbacks(self.llm_profiles_file)

            # 콜백 리스트 클리어
            with self._lock:
                self._change_callbacks.clear()

            # 추가: 남은 콜백이 없다면 전역 Observer 까지 정리
            if not self._file_change_notifier._callbacks:  # pylint: disable=protected-access
                self._file_change_notifier.stop_all()

            # 약간의 대기로 스레드 정리 보장
            time.sleep(0.05)

            logger.debug("ConfigManager 리소스 정리 완료")
        except Exception as e:
            logger.error(f"ConfigManager 리소스 정리 중 오류: {e}")

    def __del__(self) -> None:
        """소멸자"""
        try:
            self.cleanup()
        except Exception:
            pass

    def get_mcp_config(self) -> Dict[str, Any]:
        """MCP 설정 반환 (하위 호환성을 위해 제공)"""
        try:
            return self.mcp_config_manager.get_config().model_dump()
        except Exception as exc:  # pragma: no cover – 예상치 못한 오류 로그
            logger.error("MCP 설정 가져오기 실패: %s", exc)
            return {}
