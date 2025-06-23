from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)

_WORKFLOW_REGISTRY: Dict[str, Type["BaseWorkflow"]] = {}


class BaseWorkflow(ABC):
    @abstractmethod
    async def run(self, agent, user_msg: str, streaming_cb=None):  # noqa: D401
        ...


class SequentialWorkflow(BaseWorkflow):
    def __init__(self, steps: List[Callable]):
        self.steps = steps

    async def run(self, agent, user_msg: str, streaming_cb=None):  # type: ignore[override]
        result = user_msg
        for step in self.steps:
            result = await step(agent, result, streaming_cb)
        return result

    @staticmethod
    def factory(steps):
        class _Anonymous(SequentialWorkflow):
            def __init__(self):
                super().__init__(steps)

        return _Anonymous


async def _basic_chat_step(agent, msg, streaming_cb=None):
    return await agent._generate_basic_response(
        msg, streaming_cb
    )  # pylint: disable=protected-access


class BasicChatWorkflow(SequentialWorkflow):
    def __init__(self):
        super().__init__([_basic_chat_step])


def register_workflow(name: str, cls: Type[BaseWorkflow]):
    _WORKFLOW_REGISTRY[name] = cls


def get_workflow(name: str) -> Optional[Type[BaseWorkflow]]:
    return _WORKFLOW_REGISTRY.get(name)


# register default
register_workflow("basic_chat", BasicChatWorkflow)

__all__ = [
    "BaseWorkflow",
    "SequentialWorkflow",
    "BasicChatWorkflow",
    "register_workflow",
    "get_workflow",
]
