"""
LLM 모듈 커스텀 예외 클래스
"""


class ConfigValidationError(Exception):
    """설정 검증 실패 시 발생하는 예외"""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message)


class InvalidAPIKeyError(ConfigValidationError):
    """잘못된 API 키 예외"""
    
    def __init__(self, message: str = "유효하지 않은 API 키입니다"):
        super().__init__(message, "api_key")


class InvalidModelError(ConfigValidationError):
    """잘못된 모델명 예외"""
    
    def __init__(self, message: str = "지원하지 않는 모델입니다"):
        super().__init__(message, "model")


class InvalidMCPConfigError(ConfigValidationError):
    """잘못된 MCP 설정 예외"""
    
    def __init__(self, message: str = "MCP 설정이 올바르지 않습니다"):
        super().__init__(message, "mcp_config")


class MCPServerConnectionError(Exception):
    """MCP 서버 연결 실패 예외"""
    
    def __init__(self, server_name: str, message: str = None):
        self.server_name = server_name
        default_message = f"MCP 서버 '{server_name}' 연결에 실패했습니다"
        super().__init__(message or default_message)


class WorkflowExecutionError(Exception):
    """워크플로우 실행 실패 예외"""
    
    def __init__(self, workflow_name: str, message: str = None):
        self.workflow_name = workflow_name
        default_message = f"워크플로우 '{workflow_name}' 실행에 실패했습니다"
        super().__init__(message or default_message)


class ToolExecutionError(Exception):
    """도구 실행 실패 예외"""
    
    def __init__(self, tool_name: str, message: str = None):
        self.tool_name = tool_name
        default_message = f"도구 '{tool_name}' 실행에 실패했습니다"
        super().__init__(message or default_message) 