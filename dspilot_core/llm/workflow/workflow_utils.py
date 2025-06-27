"""
워크플로우 유틸리티 함수
"""

import logging
import uuid
from typing import Any, AsyncGenerator, Callable, Dict, Optional, Type

from langchain_core.runnables import RunnableConfig

from dspilot_core.llm.workflow.agent_workflow import AgentWorkflow
from dspilot_core.llm.workflow.base_workflow import BaseWorkflow
from dspilot_core.llm.workflow.basic_chat_workflow import BasicChatWorkflow
from dspilot_core.llm.workflow.research_workflow import ResearchWorkflow
from dspilot_core.util.logger import setup_logger

logger = setup_logger("workflow_utils") or logging.getLogger("workflow_utils")


# 워크플로우 레지스트리
_WORKFLOW_REGISTRY: Dict[str, Type[BaseWorkflow]] = {
    "basic": BasicChatWorkflow,
    "research": ResearchWorkflow,
    "agent": AgentWorkflow,
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

    if workflow_name not in _WORKFLOW_REGISTRY:
        available_workflows = ", ".join(_WORKFLOW_REGISTRY.keys())
        raise ValueError(
            f"지원하지 않는 워크플로우: {workflow_name}. "
            f"사용 가능한 워크플로우: {available_workflows}"
        )

    logger.debug(f"워크플로우 반환: {workflow_name}")
    return _WORKFLOW_REGISTRY[workflow_name]


def register_workflow(name: str, workflow_class: Type[BaseWorkflow]) -> None:
    """
    새로운 워크플로우 등록

    Args:
        name: 워크플로우 이름
        workflow_class: 워크플로우 클래스
    """
    _WORKFLOW_REGISTRY[name.lower()] = workflow_class
    logger.info(f"워크플로우 등록: {name}")


def get_available_workflows() -> list[str]:
    """사용 가능한 워크플로우 목록 반환"""
    return list(_WORKFLOW_REGISTRY.keys())


def random_uuid() -> str:
    """랜덤 UUID 생성"""
    return str(uuid.uuid4())


async def astream_graph(
    graph,
    inputs: Dict[str, Any],
    config: Optional[RunnableConfig] = None,
    streaming_callback: Optional[Callable[[str], None]] = None,
) -> AsyncGenerator[str, None]:
    """
    그래프 스트리밍 실행 (React Agent용)
    
    Args:
        graph: 실행할 그래프
        inputs: 입력 데이터
        config: 실행 설정
        streaming_callback: 스트리밍 콜백
        
    Yields:
        str: 스트리밍 출력
    """
    thread_id = config.get("configurable", {}).get("thread_id") if config else str(uuid.uuid4())
    
    try:
        async for chunk in graph.astream(inputs, config=config):
            if isinstance(chunk, dict):
                for node_name, output in chunk.items():
                    if "messages" in output:
                        for message in output["messages"]:
                            content = getattr(message, "content", str(message))
                            if content and content.strip():
                                if streaming_callback:
                                    streaming_callback(content)
                                yield content
                    else:
                        content = str(output)
                        if content and content.strip():
                            if streaming_callback:
                                streaming_callback(content)
                            yield content
            else:
                content = str(chunk)
                if content and content.strip():
                    if streaming_callback:
                        streaming_callback(content)
                    yield content
                    
    except Exception as e:
        error_msg = f"그래프 스트리밍 실행 오류: {e}"
        logger.error(error_msg)
        if streaming_callback:
            streaming_callback(error_msg)
        yield error_msg
