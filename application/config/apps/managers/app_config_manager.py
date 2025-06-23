import configparser
import logging
import os
import shutil
from typing import Any, Dict, List, Optional

from application.config.apps.defaults.default_app_config import (
    DEFAULT_APP_CONFIG_FILE_NAME,
    DEFAULT_APP_CONFIG_SECTIONS,
    DEFAULT_APP_CONFIG_TEMPLATE_SUFFIX,
    DEFAULT_UI_VALUES,
    SUPPORTED_THEMES,
)
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("config") or logging.getLogger("config")


class AppConfigManager:
    """애플리케이션 설정 관리 클래스

    app.config 파일을 통해 애플리케이션의 기본 설정들을 관리합니다.
    단일 책임 원칙에 따라 app.config 파일 관리만을 담당합니다.
    """

    def __init__(self, config_file: Optional[str] = None) -> None:
        """AppConfigManager 생성자

        Args:
            config_file: 설정 파일 경로. None인 경우 기본값 사용
        """
        if config_file:
            self.config_file = config_file
        else:
            app_config_path = DEFAULT_APP_CONFIG_FILE_NAME
            template_path = DEFAULT_APP_CONFIG_FILE_NAME + DEFAULT_APP_CONFIG_TEMPLATE_SUFFIX

            if os.path.exists(app_config_path):
                self.config_file = app_config_path
            elif os.path.exists(template_path):
                shutil.copy(template_path, app_config_path)
                self.config_file = app_config_path
                logger.info("템플릿에서 %s 파일 생성 완료", DEFAULT_APP_CONFIG_FILE_NAME)
            else:
                self.config_file = app_config_path
                logger.warning("설정 파일이 없어 기본값으로 생성됩니다")

        self.config: configparser.ConfigParser = configparser.ConfigParser()
        self.load_config()

    def load_config(self) -> None:
        """설정 파일 로드"""
        if not self.config_file:
            logger.error("설정 파일 경로가 비어있습니다")
            self.create_default_config()
            return

        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding="utf-8")
                logger.debug("설정 파일 로드 완료: %s", self.config_file)
            except (configparser.Error, UnicodeDecodeError) as exception:
                logger.error("설정 파일 파싱 실패: %s", exception)
                self.create_default_config()
            except PermissionError as exception:
                logger.error("설정 파일 접근 권한 없음: %s", exception)
                self.create_default_config()
            except OSError as exception:
                logger.error("설정 파일 읽기 실패: %s", exception)
                self.create_default_config()
            except Exception as exception:
                logger.error("설정 파일 로드 중 예상치 못한 오류: %s", exception)
                self.create_default_config()
        else:
            logger.info(
                "설정 파일이 존재하지 않음, 기본 설정 생성: %s", self.config_file
            )
            self.create_default_config()

    def create_default_config(self) -> None:
        """기본 설정 생성"""
        try:
            self.config.clear()

            # 기본 설정 섹션들을 순회하며 추가
            for section_name, section_config in DEFAULT_APP_CONFIG_SECTIONS.items():
                self.config[section_name] = section_config

            self.save_config()
            logger.debug("기본 설정 파일 생성 완료")
        except Exception as exception:
            logger.error("기본 설정 생성 실패: %s", exception)
            raise

    def save_config(self) -> None:
        """설정 파일 저장"""
        if not self.config_file:
            logger.error("설정 파일 경로가 비어있습니다")
            return

        try:
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            with open(self.config_file, "w", encoding="utf-8") as config_file:
                self.config.write(config_file)
            logger.debug("설정 파일 저장 완료: %s", self.config_file)
        except PermissionError as exception:
            logger.error("설정 파일 저장 권한 없음: %s", exception)
        except OSError as exception:
            logger.error("설정 파일 저장 실패: %s", exception)
        except Exception as exception:
            logger.error("설정 파일 저장 중 예상치 못한 오류: %s", exception)

    def get_ui_config(self) -> Dict[str, Any]:
        """UI 설정 반환"""
        try:
            self.load_config()

            # 기본값을 사용하여 설정값 가져오기
            font_size_str = self.config.get(
                "UI", "font_size", fallback=str(DEFAULT_UI_VALUES["font_size"]))
            chat_bubble_max_width_str = self.config.get(
                "UI", "chat_bubble_max_width", fallback=str(DEFAULT_UI_VALUES["chat_bubble_max_width"])
            )

            # 폰트 크기 파싱 및 검증
            try:
                font_size = int(font_size_str)
                if font_size <= 0:
                    logger.warning(
                        "잘못된 폰트 크기 값: %s, 기본값 사용", font_size_str
                    )
                    font_size = DEFAULT_UI_VALUES["font_size"]
            except (ValueError, TypeError):
                logger.warning(
                    "폰트 크기 변환 실패: %s, 기본값 사용", font_size_str
                )
                font_size = DEFAULT_UI_VALUES["font_size"]

            # 채팅 버블 너비 파싱 및 검증
            try:
                chat_bubble_max_width = int(chat_bubble_max_width_str)
                if chat_bubble_max_width <= 0:
                    logger.warning(
                        "잘못된 채팅 버블 너비 값: %s, 기본값 사용",
                        chat_bubble_max_width_str,
                    )
                    chat_bubble_max_width = DEFAULT_UI_VALUES["chat_bubble_max_width"]
            except (ValueError, TypeError):
                logger.warning(
                    "채팅 버블 너비 변환 실패: %s, 기본값 사용",
                    chat_bubble_max_width_str,
                )
                chat_bubble_max_width = DEFAULT_UI_VALUES["chat_bubble_max_width"]

            return {
                "font_family": self.config.get(
                    "UI",
                    "font_family",
                    fallback=DEFAULT_UI_VALUES["font_family"],
                ),
                "font_size": font_size,
                "chat_bubble_max_width": chat_bubble_max_width,
                "window_theme": self.config.get("UI", "window_theme", fallback=DEFAULT_UI_VALUES["window_theme"]),
            }
        except Exception as exception:
            logger.error("UI 설정 가져오기 실패: %s", exception)
            # 예외 발생 시 기본값 반환
            return DEFAULT_UI_VALUES.copy()

    def set_ui_config(
        self,
        font_family: str,
        font_size: int,
        chat_bubble_max_width: int,
        window_theme: str,
    ) -> None:
        """UI 설정 저장"""
        try:
            if not font_family or not window_theme:
                raise ValueError("폰트 패밀리와 윈도우 테마는 필수 입력값입니다")

            if font_size <= 0:
                raise ValueError("폰트 크기는 0보다 커야 합니다")

            if chat_bubble_max_width <= 0:
                raise ValueError("채팅 버블 최대 너비는 0보다 커야 합니다")

            if window_theme not in SUPPORTED_THEMES:
                logger.warning(
                    "알 수 없는 테마: %s, 기본값 '%s' 사용",
                    window_theme,
                    DEFAULT_UI_VALUES["window_theme"]
                )
                window_theme = DEFAULT_UI_VALUES["window_theme"]

            if "UI" not in self.config:
                self.config.add_section("UI")

            self.config["UI"]["font_family"] = font_family
            self.config["UI"]["font_size"] = str(font_size)
            self.config["UI"]["chat_bubble_max_width"] = str(
                chat_bubble_max_width)
            self.config["UI"]["window_theme"] = window_theme
            self.save_config()
            logger.info("UI 설정 저장 완료")
        except ValueError as exception:
            logger.error("UI 설정 값 오류: %s", exception)
            raise
        except Exception as exception:
            logger.error("UI 설정 저장 실패: %s", exception)
            raise

    def save_ui_config(self, ui_config: Dict[str, Any]) -> None:
        """UI 설정 저장 (딕셔너리 형태)

        Args:
            ui_config: UI 설정 딕셔너리
        """
        try:
            # 필수 필드 검증 및 기본값 적용
            font_family = ui_config.get(
                "font_family", DEFAULT_UI_VALUES["font_family"])
            font_size = int(ui_config.get(
                "font_size", DEFAULT_UI_VALUES["font_size"]))
            chat_bubble_max_width = int(ui_config.get(
                "chat_bubble_max_width", DEFAULT_UI_VALUES["chat_bubble_max_width"]))
            window_theme = ui_config.get(
                "window_theme", DEFAULT_UI_VALUES["window_theme"])

            # 기존 메서드 활용
            self.set_ui_config(font_family, font_size,
                               chat_bubble_max_width, window_theme)
        except (ValueError, TypeError) as exception:
            logger.error(f"UI 설정 딕셔너리 변환 실패: {exception}")
            raise
        except Exception as exception:
            logger.error(f"UI 설정 저장 실패: {exception}")
            raise

    def get_config_value(
        self, section: str, key: str, fallback: Optional[str] = None
    ) -> Optional[str]:
        """설정값 가져오기"""
        try:
            if not section or not key:
                raise ValueError("섹션과 키는 필수 입력값입니다")

            return self.config.get(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError) as exception:
            logger.warning("설정 값 없음 [%s.%s]: %s", section, key, exception)
            return fallback
        except Exception as exception:
            logger.error(
                "설정 값 가져오기 실패 [%s.%s]: %s", section, key, exception
            )
            return fallback

    def set_config_value(self, section: str, key: str, value: str) -> None:
        """설정값 저장"""
        try:
            if not section or not key:
                raise ValueError("섹션과 키는 필수 입력값입니다")

            if value is None:
                raise ValueError("값은 None일 수 없습니다")

            if section not in self.config:
                self.config.add_section(section)

            self.config[section][key] = str(value)
            self.save_config()
            logger.debug("설정 값 저장 완료 [%s.%s]: %s", section, key, value)
        except ValueError as exception:
            logger.error("설정 값 오류 [%s.%s]: %s", section, key, exception)
            raise
        except Exception as exception:
            logger.error("설정 값 저장 실패 [%s.%s]: %s", section, key, exception)
            raise

    def get_github_repositories(self) -> List[str]:
        """GitHub 저장소 목록 반환"""
        try:
            repositories_str = self.config.get(
                "GITHUB", "repositories", fallback="")
            if repositories_str:
                # 콤마로 구분된 문자열을 리스트로 변환
                repositories = [
                    repo.strip() for repo in repositories_str.split(",") if repo.strip()
                ]
                return repositories
            return []
        except Exception as exception:
            logger.error("GitHub 저장소 목록 가져오기 실패: %s", exception)
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
            logger.info(f"GitHub 저장소 목록 설정 완료: {len(repositories)}개")
        except Exception as exception:
            logger.error(f"GitHub 저장소 목록 설정 실패: {exception}")
            raise

    def get_github_config(self) -> Dict[str, Any]:
        """GitHub 설정 반환"""
        try:
            webhook_enabled_str = self.config.get(
                "GITHUB", "webhook_enabled", fallback="false")
            webhook_port_str = self.config.get(
                "GITHUB", "webhook_port", fallback="8000")

            # Boolean 변환
            webhook_enabled = webhook_enabled_str.lower() in ("true", "1", "yes", "on")

            # Port 변환 및 검증
            try:
                webhook_port = int(webhook_port_str)
                if webhook_port <= 0 or webhook_port > 65535:
                    logger.warning(
                        f"잘못된 포트 번호: {webhook_port_str}, 기본값 8000 사용")
                    webhook_port = 8000
            except (ValueError, TypeError):
                logger.warning(f"포트 번호 변환 실패: {webhook_port_str}, 기본값 8000 사용")
                webhook_port = 8000

            return {
                "repositories": self.get_github_repositories(),
                "webhook_enabled": webhook_enabled,
                "webhook_port": webhook_port,
            }
        except Exception as exception:
            logger.error(f"GitHub 설정 가져오기 실패: {exception}")
            return {
                "repositories": [],
                "webhook_enabled": False,
                "webhook_port": 8000,
            }

    def set_github_config(self, github_config: Dict[str, Any]) -> None:
        """GitHub 설정 저장"""
        try:
            if "GITHUB" not in self.config:
                self.config.add_section("GITHUB")

            # 저장소 목록 설정
            if "repositories" in github_config:
                self.set_github_repositories(github_config["repositories"])

            # 웹훅 설정
            if "webhook_enabled" in github_config:
                self.config["GITHUB"]["webhook_enabled"] = str(
                    github_config["webhook_enabled"]).lower()

            if "webhook_port" in github_config:
                port = int(github_config["webhook_port"])
                if port <= 0 or port > 65535:
                    raise ValueError(f"잘못된 포트 번호: {port}")
                self.config["GITHUB"]["webhook_port"] = str(port)

            self.save_config()
            logger.info("GitHub 설정 저장 완료")
        except ValueError as exception:
            logger.error(f"GitHub 설정 값 오류: {exception}")
            raise
        except Exception as exception:
            logger.error(f"GitHub 설정 저장 실패: {exception}")
            raise
