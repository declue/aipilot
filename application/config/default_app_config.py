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

# UI 기본 설정값 (문자열 형태 - ConfigParser 호환)
DEFAULT_UI_CONFIG: Dict[str, str] = {
    "font_family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
    "font_size": "14",
    "chat_bubble_max_width": "600",
    "window_theme": "light",
}

# GitHub 기본 설정값
DEFAULT_GITHUB_CONFIG: Dict[str, str] = {
    "repositories": "",  # 쉼표로 구분된 저장소 목록
    "webhook_enabled": "false",
    "webhook_port": "8000",
}

# 전체 기본 설정 구조
DEFAULT_APP_CONFIG_SECTIONS: Dict[str, Dict[str, str]] = {
    "LLM": DEFAULT_LLM_CONFIG,
    "UI": DEFAULT_UI_CONFIG,
    "GITHUB": DEFAULT_GITHUB_CONFIG,
}

# UI 설정 타입별 기본값 (런타임에서 사용 - 실제 타입)
DEFAULT_UI_VALUES: Dict[str, Any] = {
    "font_family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
    "font_size": 14,
    "chat_bubble_max_width": 600,
    "window_theme": "light",
}

# 지원되는 테마 목록
SUPPORTED_THEMES = ["light", "dark"]

# 설정 파일 관련 상수
DEFAULT_APP_CONFIG_FILE_NAME = "app.config"
DEFAULT_APP_CONFIG_TEMPLATE_SUFFIX = ".template"
