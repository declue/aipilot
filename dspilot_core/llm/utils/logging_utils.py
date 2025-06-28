"""
LLM 모듈용 표준화된 로깅 유틸리티
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from dspilot_core.util.logger import setup_logger


class LogLevel(Enum):
    """로그 레벨 열거형"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def get_llm_logger(name: str) -> logging.Logger:
    """
    기존 setup_logger와 호환되는 LLM 로거 반환
    
    Args:
        name: 로거 이름
        
    Returns:
        logging.Logger: 로거 인스턴스
    """
    return setup_logger(name) or logging.getLogger(name)


def log_structured(
    logger: logging.Logger,
    level: LogLevel,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    operation: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """
    구조화된 로그 메시지 생성 및 기록
    
    Args:
        logger: 로거 인스턴스
        level: 로그 레벨
        message: 로그 메시지
        context: 추가 컨텍스트 정보
        operation: 작업명
        user_id: 사용자 ID
        session_id: 세션 ID
    """
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "message": message,
    }
    
    if context:
        log_data["context"] = context
    if operation:
        log_data["operation"] = operation
    if user_id:
        log_data["user_id"] = user_id
    if session_id:
        log_data["session_id"] = session_id
    
    structured_msg = json.dumps(log_data, ensure_ascii=False, default=str)
    log_method = getattr(logger, level.value.lower())
    log_method(structured_msg)


class LLMLogger:
    """LLM 모듈용 표준화된 로거"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _create_structured_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> str:
        """구조화된 로그 메시지 생성"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "logger": self.name,
            "message": message,
        }
        
        if context:
            log_data["context"] = context
        if user_id:
            log_data["user_id"] = user_id
        if session_id:
            log_data["session_id"] = session_id
        if operation:
            log_data["operation"] = operation
            
        return json.dumps(log_data, ensure_ascii=False, default=str)
    
    def debug(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """디버그 로그"""
        structured_msg = self._create_structured_message(message, context, **kwargs)
        self.logger.debug(structured_msg)
    
    def info(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """정보 로그"""
        structured_msg = self._create_structured_message(message, context, **kwargs)
        self.logger.info(structured_msg)
    
    def warning(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """경고 로그"""
        structured_msg = self._create_structured_message(message, context, **kwargs)
        self.logger.warning(structured_msg)
    
    def error(
        self,
        message: str,
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """오류 로그"""
        if error:
            if context is None:
                context = {}
            context["error_type"] = type(error).__name__
            context["error_details"] = str(error)
        
        structured_msg = self._create_structured_message(message, context, **kwargs)
        self.logger.error(structured_msg)
    
    def critical(
        self,
        message: str,
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """중요 오류 로그"""
        if error:
            if context is None:
                context = {}
            context["error_type"] = type(error).__name__
            context["error_details"] = str(error)
        
        structured_msg = self._create_structured_message(message, context, **kwargs)
        self.logger.critical(structured_msg)
    
    def log_agent_activity(
        self,
        agent_type: str,
        operation: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        duration: Optional[float] = None,
        success: bool = True,
        **kwargs
    ) -> None:
        """Agent 활동 전용 로그"""
        context = {
            "agent_type": agent_type,
            "operation": operation,
            "success": success,
        }
        
        if duration is not None:
            context["duration_seconds"] = duration
        
        # 추가 컨텍스트 병합
        if kwargs:
            context.update(kwargs)
        
        log_method = getattr(self.logger, level.value.lower())
        structured_msg = self._create_structured_message(message, context)
        log_method(structured_msg)
    
    def log_config_event(
        self,
        event_type: str,
        config_name: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        **kwargs
    ) -> None:
        """설정 관련 이벤트 로그"""
        context = {
            "event_type": event_type,
            "config_name": config_name,
        }
        
        if kwargs:
            context.update(kwargs)
        
        log_method = getattr(self.logger, level.value.lower())
        structured_msg = self._create_structured_message(message, context)
        log_method(structured_msg)
    
    def log_mcp_event(
        self,
        server_name: str,
        operation: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        tool_name: Optional[str] = None,
        **kwargs
    ) -> None:
        """MCP 관련 이벤트 로그"""
        context = {
            "server_name": server_name,
            "operation": operation,
        }
        
        if tool_name:
            context["tool_name"] = tool_name
        
        if kwargs:
            context.update(kwargs)
        
        log_method = getattr(self.logger, level.value.lower())
        structured_msg = self._create_structured_message(message, context)
        log_method(structured_msg)
    
    def log_workflow_event(
        self,
        workflow_name: str,
        step: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        **kwargs
    ) -> None:
        """워크플로우 관련 이벤트 로그"""
        context = {
            "workflow_name": workflow_name,
            "step": step,
        }
        
        if kwargs:
            context.update(kwargs)
        
        log_method = getattr(self.logger, level.value.lower())
        structured_msg = self._create_structured_message(message, context, operation="workflow")
        log_method(structured_msg)


# 편의 함수들
def log_agent_start(logger: LLMLogger, agent_type: str, message: str) -> None:
    """Agent 시작 로그"""
    logger.log_agent_activity(
        agent_type=agent_type,
        operation="start",
        message=message,
        level=LogLevel.INFO
    )


def log_agent_complete(
    logger: LLMLogger, 
    agent_type: str, 
    message: str, 
    duration: Optional[float] = None
) -> None:
    """Agent 완료 로그"""
    logger.log_agent_activity(
        agent_type=agent_type,
        operation="complete",
        message=message,
        level=LogLevel.INFO,
        duration=duration,
        success=True
    )


def log_agent_error(
    logger: LLMLogger, 
    agent_type: str, 
    message: str, 
    error: Optional[Exception] = None,
    duration: Optional[float] = None
) -> None:
    """Agent 오류 로그"""
    context = {"duration_seconds": duration} if duration else None
    logger.log_agent_activity(
        agent_type=agent_type,
        operation="error",
        message=message,
        level=LogLevel.ERROR,
        success=False,
        **context if context else {}
    )
    
    if error:
        logger.error(f"Agent {agent_type} 상세 오류", error=error)


def log_mcp_operation(
    logger: LLMLogger,
    server_name: str,
    operation: str,
    message: str,
    success: bool = True,
    tool_name: Optional[str] = None
) -> None:
    """MCP 작업 로그"""
    level = LogLevel.INFO if success else LogLevel.ERROR
    logger.log_mcp_event(
        server_name=server_name,
        operation=operation,
        message=message,
        level=level,
        tool_name=tool_name,
        success=success
    ) 