from typing import Any, Dict, List

# LLM 프로필 관련 상수
DEFAULT_LLM_PROFILES_JSON = "llm_profiles.json"
DEFAULT_LLM_PROFILE = "default"

# LLM 프로필 필수 필드 목록
REQUIRED_LLM_PROFILE_FIELDS: List[str] = [
    "name",
    "api_key",
    "base_url",
    "model",
    "temperature",
    "max_tokens",
    "top_k",
]

# 기본 LLM 프로필들
DEFAULT_LLM_PROFILES: Dict[str, Dict[str, Any]] = {
    "default": {
        "name": "기본 프로필",
        "api_key": "your-api-key-here",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "temperature": 0.7,
        "max_tokens": 100000,
        "top_k": 50,
        "instruction_file": "instructions/default_agent_instructions.txt",
        "description": "기본 Ollama 설정 (적응형 워크플로우)",
        "mode": "adaptive",
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
        "description": "OpenAI GPT 모델 (적응형 워크플로우)",
        "mode": "adaptive",
    },
    "mcp_tools": {
        "name": "MCP 도구 모드",
        "api_key": "your-api-key-here",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "temperature": 0.7,
        "max_tokens": 100000,
        "top_k": 50,
        "instruction_file": "instructions/default_agent_instructions.txt",
        "description": "MCP 도구를 사용하여 실시간 정보 제공 (적응형 워크플로우)",
        "mode": "adaptive",
    },
}

# LLM 프로필 기본 구조 (새 프로필 생성 시 참조용)
DEFAULT_PROFILE_TEMPLATE: Dict[str, Any] = {
    "name": "",
    "api_key": "",
    "base_url": "",
    "model": "",
    "temperature": 0.7,
    "max_tokens": 100000,
    "top_k": 50,
    "instruction_file": "instructions/default_agent_instructions.txt",
    "description": "",
    "mode": "adaptive",
}

# LLM 프로필 파일 구조
DEFAULT_LLM_PROFILES_FILE_STRUCTURE: Dict[str, Any] = {
    "profiles": DEFAULT_LLM_PROFILES,
    "current_profile": DEFAULT_LLM_PROFILE,
}

# 보호된 프로필 목록 (삭제 불가)
PROTECTED_PROFILES: List[str] = ["default"]
