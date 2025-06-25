"""
LLM 및 MCP 설정 검증기
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI

from application.llm.models.llm_config import LLMConfig
from application.llm.models.mcp_config import MCPConfig
from application.llm.validators.exceptions import (
    ConfigValidationError,
    InvalidAPIKeyError,
    InvalidMCPConfigError,
    InvalidModelError,
)
from application.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class LLMConfigValidator:
    """LLM 설정 검증기"""
    
    # 지원하는 모델 목록
    SUPPORTED_MODELS = {
        "openai": [
            "gpt-4o-mini",
            "gpt-4o", 
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ],
        "gemini": [
            "gemini-pro",
            "gemini-pro-vision",
        ],
        "ollama": [
            "llama2",
            "llama2:13b",
            "codellama",
            "mistral",
            "mixtral",
        ],
    }
    
    @classmethod
    def validate_config(cls, config: LLMConfig) -> None:
        """LLM 설정 전체 검증"""
        cls.validate_api_key(config.api_key)
        cls.validate_model(config.model, config.base_url)
        cls.validate_parameters(config)
        logger.info(f"LLM 설정 검증 완료: {config.model}")
    
    @classmethod
    def validate_api_key(cls, api_key: str) -> None:
        """API 키 검증"""
        if not api_key or not api_key.strip():
            raise InvalidAPIKeyError("API 키가 비어있습니다")
        
        if len(api_key.strip()) < 10:
            raise InvalidAPIKeyError("API 키가 너무 짧습니다")
        
        # 특수 문자 검증 (기본적인 형식 검사)
        if not re.match(r'^[a-zA-Z0-9\-_\.]+$', api_key.strip()):
            raise InvalidAPIKeyError("API 키 형식이 올바르지 않습니다")
    
    @classmethod
    def validate_model(cls, model: str, base_url: Optional[str] = None) -> None:
        """모델명 검증"""
        if not model or not model.strip():
            raise InvalidModelError("모델명이 비어있습니다")
        
        model = model.strip().lower()
        
        # base_url 기반 모델 검증
        if base_url:
            if "ollama" in base_url.lower():
                # Ollama 모델은 사용자 정의 가능하므로 기본 검증만
                return
            elif "anthropic" in base_url.lower():
                if not any(model.startswith(m.lower()) for m in cls.SUPPORTED_MODELS["anthropic"]):
                    raise InvalidModelError(f"지원하지 않는 Anthropic 모델: {model}")
            elif "gemini" in base_url.lower():
                if not any(model.startswith(m.lower()) for m in cls.SUPPORTED_MODELS["gemini"]):
                    raise InvalidModelError(f"지원하지 않는 Gemini 모델: {model}")
        else:
            # OpenAI 모델 검증
            if not any(model.startswith(m.lower()) for m in cls.SUPPORTED_MODELS["openai"]):
                raise InvalidModelError(f"지원하지 않는 OpenAI 모델: {model}")
    
    @classmethod
    def validate_parameters(cls, config: LLMConfig) -> None:
        """LLM 파라미터 검증"""
        # Temperature 검증
        if not (0.0 <= config.temperature <= 2.0):
            raise ConfigValidationError(
                "Temperature는 0.0과 2.0 사이의 값이어야 합니다", 
                "temperature"
            )
        
        # Max tokens 검증
        if config.max_tokens <= 0:
            raise ConfigValidationError(
                "Max tokens는 0보다 큰 값이어야 합니다",
                "max_tokens"
            )
        
        if config.max_tokens > 128000:  # 일반적인 최대값
            raise ConfigValidationError(
                "Max tokens가 너무 큽니다 (최대 128,000)",
                "max_tokens"
            )
        
        # Mode 검증
        valid_modes = ["basic", "mcp_tools", "workflow"]
        if config.mode not in valid_modes:
            raise ConfigValidationError(
                f"Mode는 {valid_modes} 중 하나여야 합니다",
                "mode"
            )
    
    @classmethod
    async def test_connection(cls, config: LLMConfig) -> bool:
        """실제 API 연결 테스트"""
        try:
            # 기본 검증 먼저 수행
            cls.validate_config(config)
            
            # 실제 연결 테스트
            llm_kwargs = {
                "model": config.model,
                "api_key": config.api_key,
                "temperature": 0.1,
                "max_tokens": 10,
            }
            
            if config.base_url:
                llm_kwargs["base_url"] = config.base_url
            
            llm = ChatOpenAI(**llm_kwargs)
            
            from langchain_core.messages import HumanMessage
            response = await llm.ainvoke([HumanMessage(content="Test")])
            
            logger.info(f"LLM 연결 테스트 성공: {config.model}")
            return True
            
        except Exception as e:
            logger.error(f"LLM 연결 테스트 실패: {e}")
            raise InvalidAPIKeyError(f"API 연결 테스트 실패: {str(e)}")


class MCPConfigValidator:
    """MCP 설정 검증기"""
    
    @classmethod
    def validate_config(cls, config: MCPConfig) -> None:
        """MCP 설정 전체 검증"""
        if not config.enabled:
            logger.info("MCP가 비활성화되어 있어 검증을 건너뜁니다")
            return
        
        cls.validate_servers(config.mcp_servers)
        cls.validate_default_server(config)
        logger.info(f"MCP 설정 검증 완료: {len(config.mcp_servers)}개 서버")
    
    @classmethod
    def validate_servers(cls, servers: Dict[str, Any]) -> None:
        """MCP 서버 설정 검증"""
        if not servers:
            raise InvalidMCPConfigError("MCP 서버 설정이 비어있습니다")
        
        for server_name, server_config in servers.items():
            cls.validate_server_config(server_name, server_config)
    
    @classmethod
    def validate_server_config(cls, server_name: str, config: Dict[str, Any]) -> None:
        """개별 서버 설정 검증"""
        if not isinstance(config, dict):
            raise InvalidMCPConfigError(f"서버 '{server_name}' 설정이 올바르지 않습니다")
        
        # 필수 필드 검증
        if "command" not in config and "url" not in config:
            raise InvalidMCPConfigError(
                f"서버 '{server_name}': command 또는 url 중 하나는 필수입니다"
            )
        
        # Command 방식 검증
        if "command" in config:
            cls.validate_command_config(server_name, config)
        
        # URL 방식 검증
        if "url" in config:
            cls.validate_url_config(server_name, config)
        
        # 환경 변수 검증
        if "env" in config and not isinstance(config["env"], dict):
            raise InvalidMCPConfigError(
                f"서버 '{server_name}': env는 딕셔너리 형태여야 합니다"
            )
    
    @classmethod
    def validate_command_config(cls, server_name: str, config: Dict[str, Any]) -> None:
        """Command 방식 설정 검증"""
        command = config["command"]
        
        if not command or not command.strip():
            raise InvalidMCPConfigError(
                f"서버 '{server_name}': command가 비어있습니다"
            )
        
        # 실행 파일 존재 여부 검증
        command_path = Path(command.strip())
        if command_path.is_absolute() and not command_path.exists():
            raise InvalidMCPConfigError(
                f"서버 '{server_name}': 명령어 파일을 찾을 수 없습니다: {command}"
            )
        
        # Arguments 검증
        if "args" in config and not isinstance(config["args"], list):
            raise InvalidMCPConfigError(
                f"서버 '{server_name}': args는 리스트 형태여야 합니다"
            )
    
    @classmethod
    def validate_url_config(cls, server_name: str, config: Dict[str, Any]) -> None:
        """URL 방식 설정 검증"""
        url = config["url"]
        
        if not url or not url.strip():
            raise InvalidMCPConfigError(
                f"서버 '{server_name}': url이 비어있습니다"
            )
        
        # 기본적인 URL 형식 검증
        if not re.match(r'^https?://', url.strip()):
            raise InvalidMCPConfigError(
                f"서버 '{server_name}': 올바른 URL 형식이 아닙니다: {url}"
            )
    
    @classmethod
    def validate_default_server(cls, config: MCPConfig) -> None:
        """기본 서버 설정 검증"""
        if config.default_server:
            if config.default_server not in config.mcp_servers:
                raise InvalidMCPConfigError(
                    f"기본 서버 '{config.default_server}'가 서버 목록에 없습니다"
                )
    
    @classmethod
    def get_validation_report(cls, config: MCPConfig) -> Dict[str, Any]:
        """설정 검증 리포트 생성"""
        report = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "server_count": len(config.mcp_servers),
            "enabled_servers": 0,
        }
        
        try:
            cls.validate_config(config)
            
            # 활성화된 서버 수 계산
            enabled_servers = config.get_enabled_servers()
            report["enabled_servers"] = len(enabled_servers)
            
            # 경고 사항 검사
            if not enabled_servers:
                report["warnings"].append("활성화된 서버가 없습니다")
            
            if not config.default_server:
                report["warnings"].append("기본 서버가 설정되지 않았습니다")
                
        except Exception as e:
            report["valid"] = False
            report["errors"].append(str(e))
        
        return report 