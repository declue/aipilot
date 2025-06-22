"""
기본 애플리케이션 설정값 정의

이 모듈은 애플리케이션 전체에서 사용되는 기본 설정값들을 중앙 집중적으로 관리합니다.
DRY(Don't Repeat Yourself) 원칙에 따라 기본값을 한 곳에서 정의하고 재사용합니다.
"""

from typing import Any, Dict

# LLM 기본 설정값
DEFAULT_LLM_CONFIG: Dict[str, str] = {
    "api_key": "your-api-key-here",
    "base_url": "http://localhost:11434/v1",
    "model": "llama3.2",
    "temperature": "0.7",
    "max_tokens": "100000",
    "top_k": "50",
    "current_profile": "default",
    "mode": "basic",
    "workflow": "basic_chat",
    "show_cot": "false",
    "react_max_turns": "5",
    "llm_retry_attempts": "3",
    "retry_backoff_sec": "1",
}

# UI 기본 설정값
DEFAULT_UI_CONFIG: Dict[str, str] = {
    "font_family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
    "font_size": "14",
    "chat_bubble_max_width": "600",
    "window_theme": "light",
}

# UI 설정 타입별 기본값 (런타임에서 사용)
DEFAULT_UI_VALUES: Dict[str, Any] = {
    "font_family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
    "font_size": 14,
    "chat_bubble_max_width": 600,
    "window_theme": "light",
}

# MCP 기본 설정값
DEFAULT_MCP_CONFIG: Dict[str, Any] = {
    "mcpServers": {},
    "defaultServer": None,
    "enabled": True,
}

# 전체 기본 설정 구조
DEFAULT_APP_CONFIG_SECTIONS: Dict[str, Dict[str, str]] = {
    "LLM": DEFAULT_LLM_CONFIG,
    "UI": DEFAULT_UI_CONFIG,
}

# 지원되는 테마 목록
SUPPORTED_THEMES = ["light", "dark"]

# 설정 파일 관련 상수
DEFAULT_APP_CONFIG_FILE_NAME = "app.config"
DEFAULT_APP_CONFIG_TEMPLATE_SUFFIX = ".template"
