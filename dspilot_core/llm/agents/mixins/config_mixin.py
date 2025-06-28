#!/usr/bin/env python3
"""ConfigMixin: LLM 설정 로드 및 재초기화를 담당."""

from __future__ import annotations

import logging
from typing import Any

from dspilot_core.llm.models.llm_config import LLMConfig
from dspilot_core.llm.services.llm_service import LLMService
from dspilot_core.llm.validators.config_validator import LLMConfigValidator
from dspilot_core.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class ConfigMixin:
    """설정 로드와 재초기화 전담 믹스인"""

    config_manager: Any  # BaseAgent 에서 주입
    llm_config: LLMConfig
    llm_service: LLMService

    # ------------------------------------------------------------------
    # 설정 및 서비스 로드
    # ------------------------------------------------------------------
    def _load_config(self) -> None:  # pylint: disable=protected-access
        """config_manager 로부터 LLM 설정 로드"""
        try:
            cfg_dict = self.config_manager.get_llm_config()
            self.llm_config = LLMConfig.from_dict(cfg_dict)

            # 설정 검증 적용
            try:
                LLMConfigValidator.validate_config(self.llm_config)
                logger.debug(
                    "LLM 설정 로드 및 검증 완료: model=%s, mode=%s",
                    self.llm_config.model,
                    self.llm_config.mode,
                )
            except Exception as validation_exc:  # pylint: disable=broad-except
                logger.warning("LLM 설정 검증 실패: %s", validation_exc)
                # 검증 실패해도 설정은 로드된 상태로 진행

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("LLM 설정 로드 실패: %s", exc)
            # 안전한 기본값
            self.llm_config = LLMConfig(
                api_key="",
                base_url=None,
                model="gpt-4o-mini",
                max_tokens=1000,
                temperature=0.7,
                streaming=True,
                mode="basic",
                workflow=None,
            )

    # ------------------------------------------------------------------
    # 재초기화 헬퍼
    # ------------------------------------------------------------------
    def reinitialize_client(self) -> None:  # pylint: disable=protected-access
        """LLM 설정 변경 시 서비스 재초기화"""
        try:
            logger.info("BaseAgent 재초기화 시작")
            self._load_config()
            self.llm_service = LLMService(self.llm_config)
            logger.info(
                "BaseAgent 재초기화 완료: model=%s, mode=%s",
                self.llm_config.model,
                self.llm_config.mode,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("BaseAgent 재초기화 실패: %s", exc)
