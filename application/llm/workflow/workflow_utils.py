"""
워크플로우 유틸리티 함수
"""

import logging
from typing import Dict, Type

from application.llm.workflow.base_workflow import BaseWorkflow
from application.llm.workflow.basic_chat_workflow import BasicChatWorkflow
from application.util.logger import setup_logger

logger = setup_logger("workflow_utils") or logging.getLogger("workflow_utils")


# 워크플로우 레지스트리
WORKFLOW_REGISTRY: Dict[str, Type[BaseWorkflow]] = {
    "basic_chat": BasicChatWorkflow,
}


def get_workflow(workflow_name: str) -> Type[BaseWorkflow]:
    """
    워크플로우 이름으로 워크플로우 클래스 반환
    
    Args:
        workflow_name: 워크플로우 이름
        
    Returns:
        Type[BaseWorkflow]: 워크플로우 클래스
        
    Raises:
        ValueError: 지원하지 않는 워크플로우인 경우
    """
    workflow_name = workflow_name.lower()
    
    if workflow_name not in WORKFLOW_REGISTRY:
        available_workflows = ", ".join(WORKFLOW_REGISTRY.keys())
        raise ValueError(
            f"지원하지 않는 워크플로우: {workflow_name}. "
            f"사용 가능한 워크플로우: {available_workflows}"
        )
    
    logger.debug(f"워크플로우 반환: {workflow_name}")
    return WORKFLOW_REGISTRY[workflow_name]


def register_workflow(name: str, workflow_class: Type[BaseWorkflow]) -> None:
    """
    새로운 워크플로우 등록
    
    Args:
        name: 워크플로우 이름
        workflow_class: 워크플로우 클래스
    """
    WORKFLOW_REGISTRY[name.lower()] = workflow_class
    logger.info(f"워크플로우 등록: {name}")


def get_available_workflows() -> list[str]:
    """사용 가능한 워크플로우 목록 반환"""
    return list(WORKFLOW_REGISTRY.keys()) 