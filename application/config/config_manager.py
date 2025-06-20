import configparser
import json
import logging
import os
from typing import Any, Dict, List, Optional

from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("config_manager") or logging.getLogger(
    "config_manager"
)


class ConfigManager:
    """설정 파일 관리 클래스"""

    def __init__(self, config_file: Optional[str] = None) -> None:
        self.logger: logging.Logger = setup_logger(
            "config_manager"
        ) or logging.getLogger("config_manager")

        # 설정 파일 경로 설정
        if config_file:
            self.config_file = config_file
        else:
            # app.config 파일 경로를 찾음
            app_config_path = "app.config"
            template_path = "app.config.template"

            if os.path.exists(app_config_path):
                self.config_file = app_config_path
            elif os.path.exists(template_path):
                # template 파일을 복사하여 app.config 생성
                import shutil

                shutil.copy(template_path, app_config_path)
                self.config_file = app_config_path
                self.logger.info("템플릿에서 app.config 파일 생성 완료")
            else:
                self.config_file = app_config_path
                self.logger.warning("설정 파일이 없어 기본값으로 생성됩니다")

        self.config: configparser.ConfigParser = configparser.ConfigParser()
        self.load_config()

        # LLM 프로필을 저장할 별도 파일
        self.llm_profiles_file = "llm_profiles.json"
        self._llm_profiles: Dict[str, Dict[str, Any]] = {}
        self._current_profile_name = "default"
        self.load_llm_profiles()

    def load_config(self) -> None:
        """설정 파일 로드"""
        if not self.config_file:
            self.logger.error("설정 파일 경로가 비어있습니다")
            self.create_default_config()
            return

        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding="utf-8")
                self.logger.debug("설정 파일 로드 완료: %s", self.config_file)
            except (configparser.Error, UnicodeDecodeError) as exception:
                self.logger.error("설정 파일 파싱 실패: %s", exception)
                self.create_default_config()
            except PermissionError as exception:
                self.logger.error("설정 파일 접근 권한 없음: %s", exception)
                self.create_default_config()
            except OSError as exception:
                self.logger.error("설정 파일 읽기 실패: %s", exception)
                self.create_default_config()
            except Exception as exception:
                self.logger.error("설정 파일 로드 중 예상치 못한 오류: %s", exception)
                self.create_default_config()
        else:
            self.logger.info(
                "설정 파일이 존재하지 않음, 기본 설정 생성: %s", self.config_file
            )
            self.create_default_config()

    def create_default_config(self) -> None:
        """기본 설정 생성"""
        try:
            self.config.clear()

            self.config["LLM"] = {
                "api_key": "your-api-key-here",
                "base_url": "http://localhost:11434/v1",  # Ollama 기본 URL
                "model": "llama3.2",  # 기본 모델
                "temperature": "0.7",
                "max_tokens": "100000",
                "top_k": "50",
                "current_profile": "default",
                "mode": "basic",  # basic | react | workflow
                "workflow": "basic_chat",  # workflow 이름 (mode=workflow일 때)
                "show_cot": "false",  # chain-of-thought 노출 여부 (true/false)
                "react_max_turns": "5",  # ReAct 루프 최대 반복 횟수
                "llm_retry_attempts": "3",  # LLM 호출 재시도 횟수
                "retry_backoff_sec": "1",  # 초기 backoff(초)
            }

            self.config["UI"] = {
                "font_family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
                "font_size": "14",
                "chat_bubble_max_width": "600",
                "window_theme": "light",
            }

            self.save_config()
            self.logger.debug("기본 설정 파일 생성 완료")
        except Exception as exception:
            self.logger.error("기본 설정 생성 실패: %s", exception)
            raise

    def save_config(self) -> None:
        """설정 파일 저장"""
        if not self.config_file:
            self.logger.error("설정 파일 경로가 비어있습니다")
            return

        try:
            # 디렉토리가 없으면 생성
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            with open(self.config_file, "w", encoding="utf-8") as config_file:
                self.config.write(config_file)
            self.logger.debug("설정 파일 저장 완료: %s", self.config_file)
        except PermissionError as exception:
            self.logger.error("설정 파일 저장 권한 없음: %s", exception)
        except OSError as exception:
            self.logger.error("설정 파일 저장 실패: %s", exception)
        except Exception as exception:
            self.logger.error("설정 파일 저장 중 예상치 못한 오류: %s", exception)

    def load_llm_profiles(self) -> None:
        """LLM 프로필 로드"""
        try:
            if os.path.exists(self.llm_profiles_file):
                with open(self.llm_profiles_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._llm_profiles = data.get("profiles", {})
                    self._current_profile_name = data.get("current_profile", "default")
                    self.logger.debug(
                        f"LLM 프로필 로드 완료: {len(self._llm_profiles)}개 프로필"
                    )
            else:
                # 기본 프로필 생성
                self.create_default_llm_profiles()
        except Exception as exception:
            self.logger.error(f"LLM 프로필 로드 실패: {exception}")
            self.create_default_llm_profiles()

    def create_default_llm_profiles(self) -> None:
        """기본 LLM 프로필 생성"""
        try:
            self._llm_profiles = {
                "default": {
                    "name": "기본 프로필",
                    "api_key": "your-api-key-here",
                    "base_url": "http://localhost:11434/v1",
                    "model": "llama3.2",
                    "temperature": 0.7,
                    "max_tokens": 100000,
                    "top_k": 50,
                    "instruction_file": "instructions/default_agent_instructions.txt",
                    "description": "기본 Ollama 설정",
                },
                "openai": {
                    "name": "OpenAI GPT",
                    "api_key": "sk-your-openai-key",
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "max_tokens": 100000,
                    "top_k": 50,
                    "instruction_file": "instructions/openai_agent_instructions.txt",
                    "description": "OpenAI GPT 모델",
                },
            }
            self._current_profile_name = "default"
            self.save_llm_profiles()
            self.logger.debug("기본 LLM 프로필 생성 완료")
        except Exception as exception:
            self.logger.error(f"기본 LLM 프로필 생성 실패: {exception}")
            raise

    def save_llm_profiles(self) -> None:
        """LLM 프로필 저장"""
        try:
            data = {
                "profiles": self._llm_profiles,
                "current_profile": self._current_profile_name,
            }
            with open(self.llm_profiles_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.debug("LLM 프로필 저장 완료")
        except Exception as exception:
            self.logger.error(f"LLM 프로필 저장 실패: {exception}")
            raise

    def get_llm_profiles(self) -> Dict[str, Dict[str, Any]]:
        """모든 LLM 프로필 반환"""
        return self._llm_profiles.copy()

    def get_current_profile_name(self) -> str:
        """현재 선택된 프로필 이름 반환"""
        return self._current_profile_name

    def set_current_profile(self, profile_name: str) -> None:
        """현재 프로필 설정"""
        if profile_name in self._llm_profiles:
            self._current_profile_name = profile_name
            # 기본 설정 파일에도 저장
            if "LLM" not in self.config:
                self.config.add_section("LLM")
            self.config["LLM"]["current_profile"] = profile_name
            self.save_config()
            self.save_llm_profiles()
            self.logger.info(f"현재 프로필을 '{profile_name}'으로 변경")
        else:
            raise ValueError(f"프로필 '{profile_name}'을 찾을 수 없습니다")

    def get_llm_config(self) -> Dict[str, Any]:
        """현재 선택된 LLM 프로필의 설정 반환"""
        try:
            self.load_config()
            self.load_llm_profiles()

            # 현재 프로필 가져오기
            current_profile = self._llm_profiles.get(self._current_profile_name)
            if current_profile:
                return {
                    "api_key": current_profile.get("api_key", "your-api-key-here"),
                    "base_url": current_profile.get(
                        "base_url", "http://localhost:11434/v1"
                    ),
                    "model": current_profile.get("model", "llama3.2"),
                    "temperature": current_profile.get("temperature", 0.7),
                    "max_tokens": current_profile.get("max_tokens", 100000),
                    "top_k": current_profile.get("top_k", 50),
                    "instruction_file": current_profile.get(
                        "instruction_file",
                        "instructions/default_agent_instructions.txt",
                    ),
                    "show_cot": current_profile.get("show_cot", "false"),
                    "react_max_turns": current_profile.get("react_max_turns", "5"),
                    "llm_retry_attempts": current_profile.get("llm_retry_attempts", "3"),
                    "retry_backoff_sec": current_profile.get("retry_backoff_sec", "1"),
                }
            else:
                # 프로필이 없으면 기본 설정에서 가져오기 (하위 호환성)
                return {
                    "api_key": self.config.get(
                        "LLM", "api_key", fallback="your-api-key-here"
                    ),
                    "base_url": self.config.get(
                        "LLM", "base_url", fallback="http://localhost:11434/v1"
                    ),
                    "model": self.config.get("LLM", "model", fallback="llama3.2"),
                    "temperature": float(
                        self.config.get("LLM", "temperature", fallback="0.7")
                    ),
                    "max_tokens": int(
                        self.config.get("LLM", "max_tokens", fallback="100000")
                    ),
                    "top_k": int(self.config.get("LLM", "top_k", fallback="50")),
                    "instruction_file": self.config.get(
                        "LLM",
                        "instruction_file",
                        fallback="instructions/default_agent_instructions.txt",
                    ),
                    "show_cot": self.config.get("LLM", "show_cot", fallback="false"),
                    "react_max_turns": self.config.get("LLM", "react_max_turns", fallback="5"),
                    "llm_retry_attempts": self.config.get("LLM", "llm_retry_attempts", fallback="3"),
                    "retry_backoff_sec": self.config.get("LLM", "retry_backoff_sec", fallback="1"),
                }
        except Exception as exception:
            self.logger.error("LLM 설정 가져오기 실패: %s", exception)
            # 기본값 반환
            return {
                "api_key": "your-api-key-here",
                "base_url": "http://localhost:11434/v1",
                "model": "llama3.2",
                "temperature": 0.7,
                "max_tokens": 100000,
                "top_k": 50,
                "instruction_file": "instructions/default_agent_instructions.txt",
                "show_cot": "false",
                "react_max_turns": "5",
                "llm_retry_attempts": "3",
                "retry_backoff_sec": "1",
            }

    def create_llm_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """새 LLM 프로필 생성"""
        if profile_name in self._llm_profiles:
            raise ValueError(f"프로필 '{profile_name}'이 이미 존재합니다")

        required_fields = [
            "name",
            "api_key",
            "base_url",
            "model",
            "temperature",
            "max_tokens",
            "top_k",
        ]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"필수 필드 '{field}'가 없습니다")

        self._llm_profiles[profile_name] = config
        self.save_llm_profiles()
        self.logger.info(f"새 LLM 프로필 '{profile_name}' 생성 완료")

    def update_llm_profile(self, profile_name: str, config: Dict[str, Any]) -> None:
        """LLM 프로필 업데이트"""
        if profile_name not in self._llm_profiles:
            raise ValueError(f"프로필 '{profile_name}'을 찾을 수 없습니다")

        self._llm_profiles[profile_name].update(config)
        self.save_llm_profiles()
        self.logger.info(f"LLM 프로필 '{profile_name}' 업데이트 완료")

    def delete_llm_profile(self, profile_name: str) -> None:
        """LLM 프로필 삭제"""
        if profile_name not in self._llm_profiles:
            raise ValueError(f"프로필 '{profile_name}'을 찾을 수 없습니다")

        if profile_name == "default":
            raise ValueError("기본 프로필은 삭제할 수 없습니다")

        # 현재 선택된 프로필이면 기본 프로필로 변경
        if self._current_profile_name == profile_name:
            self.set_current_profile("default")

        del self._llm_profiles[profile_name]
        self.save_llm_profiles()
        self.logger.info(f"LLM 프로필 '{profile_name}' 삭제 완료")

    def set_llm_config(self, api_key: str, base_url: str, model: str) -> None:
        """LLM 설정 저장 (하위 호환성을 위해 유지)"""
        try:
            # 입력값 검증
            if not api_key or not base_url or not model:
                raise ValueError("API 키, 베이스 URL, 모델은 필수 입력값입니다")

            if "LLM" not in self.config:
                self.config.add_section("LLM")

            self.config["LLM"]["api_key"] = api_key
            self.config["LLM"]["base_url"] = base_url
            self.config["LLM"]["model"] = model
            self.save_config()
            self.logger.info("LLM 설정 저장 완료")
        except ValueError as exception:
            self.logger.error("LLM 설정 값 오류: %s", exception)
            raise
        except Exception as exception:
            self.logger.error("LLM 설정 저장 실패: %s", exception)
            raise

    def get_ui_config(self) -> Dict[str, Any]:
        """UI 설정 가져오기"""
        try:
            self.load_config()
            font_size_str = self.config.get("UI", "font_size", fallback="14")
            chat_bubble_max_width_str = self.config.get(
                "UI", "chat_bubble_max_width", fallback="600"
            )

            # 정수 변환 시 예외 처리
            try:
                font_size = int(font_size_str)
                if font_size <= 0:
                    self.logger.warning(
                        "잘못된 폰트 크기 값: %s, 기본값 사용", font_size_str
                    )
                    font_size = 14
            except (ValueError, TypeError):
                self.logger.warning(
                    "폰트 크기 변환 실패: %s, 기본값 사용", font_size_str
                )
                font_size = 14

            try:
                chat_bubble_max_width = int(chat_bubble_max_width_str)
                if chat_bubble_max_width <= 0:
                    self.logger.warning(
                        "잘못된 채팅 버블 너비 값: %s, 기본값 사용",
                        chat_bubble_max_width_str,
                    )
                    chat_bubble_max_width = 600
            except (ValueError, TypeError):
                self.logger.warning(
                    "채팅 버블 너비 변환 실패: %s, 기본값 사용",
                    chat_bubble_max_width_str,
                )
                chat_bubble_max_width = 600

            return {
                "font_family": self.config.get(
                    "UI",
                    "font_family",
                    fallback="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
                ),
                "font_size": font_size,
                "chat_bubble_max_width": chat_bubble_max_width,
                "window_theme": self.config.get("UI", "window_theme", fallback="light"),
            }
        except Exception as exception:
            self.logger.error("UI 설정 가져오기 실패: %s", exception)
            # 기본값 반환
            return {
                "font_family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
                "font_size": 14,
                "chat_bubble_max_width": 600,
                "window_theme": "light",
            }

    def set_ui_config(
        self,
        font_family: str,
        font_size: int,
        chat_bubble_max_width: int,
        window_theme: str,
    ) -> None:
        """UI 설정 저장"""
        try:
            # 입력값 검증
            if not font_family or not window_theme:
                raise ValueError("폰트 패밀리와 윈도우 테마는 필수 입력값입니다")

            if font_size <= 0:
                raise ValueError("폰트 크기는 0보다 커야 합니다")

            if chat_bubble_max_width <= 0:
                raise ValueError("채팅 버블 최대 너비는 0보다 커야 합니다")

            if window_theme not in ["light", "dark"]:
                self.logger.warning(
                    "알 수 없는 테마: %s, 기본값 'light' 사용", window_theme
                )
                window_theme = "light"

            if "UI" not in self.config:
                self.config.add_section("UI")

            self.config["UI"]["font_family"] = font_family
            self.config["UI"]["font_size"] = str(font_size)
            self.config["UI"]["chat_bubble_max_width"] = str(chat_bubble_max_width)
            self.config["UI"]["window_theme"] = window_theme
            self.save_config()
            self.logger.info("UI 설정 저장 완료")
        except ValueError as exception:
            self.logger.error("UI 설정 값 오류: %s", exception)
            raise
        except Exception as exception:
            self.logger.error("UI 설정 저장 실패: %s", exception)
            raise

    def get_config_value(
        self, section: str, key: str, fallback: Optional[str] = None
    ) -> Optional[str]:
        """특정 설정값 가져오기"""
        try:
            if not section or not key:
                raise ValueError("섹션과 키는 필수 입력값입니다")

            return self.config.get(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError) as exception:
            self.logger.warning("설정 값 없음 [%s.%s]: %s", section, key, exception)
            return fallback
        except Exception as exception:
            self.logger.error(
                "설정 값 가져오기 실패 [%s.%s]: %s", section, key, exception
            )
            return fallback

    def set_config_value(self, section: str, key: str, value: str) -> None:
        """특정 설정값 저장"""
        try:
            if not section or not key:
                raise ValueError("섹션과 키는 필수 입력값입니다")

            if value is None:
                raise ValueError("값은 None일 수 없습니다")

            if section not in self.config:
                self.config.add_section(section)

            self.config[section][key] = str(value)
            self.save_config()
            self.logger.debug("설정 값 저장 완료 [%s.%s]: %s", section, key, value)
        except ValueError as exception:
            self.logger.error("설정 값 오류 [%s.%s]: %s", section, key, exception)
            raise
        except Exception as exception:
            self.logger.error("설정 값 저장 실패 [%s.%s]: %s", section, key, exception)
            raise

    def get_github_repositories(self) -> List[str]:
        """GitHub Repository/Organization 목록 가져오기"""
        try:
            repositories_str = self.config.get("GITHUB", "repositories", fallback="")
            if repositories_str:
                # 콤마로 구분된 문자열을 리스트로 변환
                repositories = [
                    repo.strip() for repo in repositories_str.split(",") if repo.strip()
                ]
                return repositories
            return []
        except Exception as exception:
            self.logger.error("GitHub 저장소 목록 가져오기 실패: %s", exception)
            return []

    def set_github_repositories(self, repositories: List[str]) -> None:
        """GitHub 저장소 목록 설정"""
        try:
            if "GITHUB" not in self.config:
                self.config.add_section("GITHUB")

            # 리스트를 쉼표로 구분된 문자열로 변환
            repositories_str = ",".join(repositories)
            self.config["GITHUB"]["repositories"] = repositories_str
            self.save_config()
            self.logger.info(f"GitHub 저장소 목록 설정 완료: {len(repositories)}개")
        except Exception as exception:
            self.logger.error(f"GitHub 저장소 목록 설정 실패: {exception}")
            raise

    def get_instruction_path(self) -> str:
        """Instruction 파일 경로를 반환합니다."""
        if "llm" in self.config and "instruction_file" in self.config["llm"]:
            return self.config["llm"]["instruction_file"]
        return os.path.join(
            os.getcwd(), "instructions", "default_agent_instructions.txt"
        )

    def get_instruction_content(self) -> str:
        """Instruction 파일 내용을 읽어 반환합니다."""
        instruction_file = self.get_instruction_path()
        try:
            # 파일이 존재하는지 확인
            if instruction_file and not os.path.exists(instruction_file):
                self.logger.warning(
                    f"Instruction 파일이 존재하지 않습니다: {instruction_file}"
                )
                return self._get_default_instruction_content()

            # 파일 읽기
            if instruction_file:
                with open(instruction_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        self.logger.warning(
                            f"Instruction 파일이 비어있습니다: {instruction_file}"
                        )
                        return self._get_default_instruction_content()

                    self.logger.debug(f"Instruction 파일 로드 성공: {instruction_file}")
                    return content
            else:
                return self._get_default_instruction_content()
        except Exception as exception:
            self.logger.error(f"Instruction 파일 읽기 실패: {exception}")
            return self._get_default_instruction_content()

    def _get_default_instruction_content(self) -> str:
        """기본 instruction 내용 반환"""
        return """도구를 사용하여 질문에 답하세요. 반드시 한국어로 응답하세요.

=== GitHub 관련 질문 처리 규칙 ===
GitHub 관련 키워드("이슈", "issue", "PR", "pull request", "커밋", "commit" 등)가 포함된 질문을 받으면:
1. 반드시 GitHub 도구를 사용하세요
2. 구체적인 저장소가 명시되지 않은 경우, 관심 저장소들을 대상으로 하세요
3. "현재 open 상태인 이슈" 같은 질문은 관심 저장소들의 open 이슈를 검색하세요
4. 특별히 ORG나 REPO 언급이 없으면 관심 저장소를 중심으로 GitHub 도구를 사용하세요

=== 중요 ===
질문에 저장소가 명시되지 않았다면 관심 저장소 목록을 모두 확인하세요."""

    def set_current_profile_name(self, profile_name: str) -> None:
        """현재 LLM 프로필 이름을 설정합니다."""
        if "llm" not in self.config:
            self.config["llm"] = {}
        self.config["llm"]["current_profile"] = profile_name
        self.save_config()
        logger.info(f"LLM 프로필이 '{profile_name}'(으)로 변경되었습니다.")

    def save_ui_config(self, ui_config: Dict[str, Any]) -> None:
        """UI 설정을 저장합니다."""
        self.config["ui"] = ui_config
        self.save_config()
        self.load_ui_config()

    def load_ui_config(self) -> None:
        """UI 설정을 로드합니다."""
        # Implementation of load_ui_config method

    def get_mcp_config(self) -> Dict[str, Any]:
        """MCP 설정을 반환합니다."""
        try:
            # MCP 설정 파일에서 서버 정보 로드
            mcp_config_file = "mcp.json"
            if os.path.exists(mcp_config_file):
                with open(mcp_config_file, "r", encoding="utf-8") as f:
                    mcp_data: Dict[str, Any] = json.load(f)
                    return mcp_data
            else:
                # 기본 MCP 설정 반환
                return {"mcpServers": {}, "defaultServer": None, "enabled": True}
        except Exception as exception:
            self.logger.error(f"MCP 설정 로드 실패: {exception}")
            return {"mcpServers": {}, "defaultServer": None, "enabled": True}
