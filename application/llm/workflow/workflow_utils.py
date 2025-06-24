"""
워크플로우 유틸리티 함수
"""

import logging
import uuid
from typing import Any, AsyncGenerator, Callable, Dict, Optional, Type

from langchain_core.runnables import RunnableConfig

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


def random_uuid() -> str:
    """랜덤 UUID 생성"""
    return str(uuid.uuid4())


async def astream_graph(
    graph: Any,
    inputs: Dict[str, Any],
    callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    config: Optional[RunnableConfig] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    그래프를 스트리밍으로 실행하고 콜백 호출
    
    Args:
        graph: 실행할 그래프 (ReAct 에이전트 등)
        inputs: 입력 데이터
        callback: 스트리밍 콜백 함수
        config: 실행 설정
        
    Yields:
        Dict[str, Any]: 스트리밍 청크
    """
    try:
        async for chunk in graph.astream(inputs, config=config):
            if callback:
                callback(chunk)
            yield chunk
    except Exception as e:
        logger.error(f"그래프 스트리밍 실행 중 오류: {e}")
        error_chunk = {
            "error": str(e),
            "type": "error"
        }
        if callback:
            callback(error_chunk)
        yield error_chunk 