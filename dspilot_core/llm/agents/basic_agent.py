"""Legacy BasicAgent shim.

기존 코드에서 `BasicAgent` 를 임포트할 때, 리팩터링된 `BaseAgent` 를 대신 제공하기 위한
얇은 래퍼입니다.
"""
from dspilot_core.llm.agents.base_agent import BaseAgent


class BasicAgent(BaseAgent):
    """`BaseAgent` 의 단순 별칭 – 향후 호환성 유지를 위해 존재"""
    pass  # pylint: disable=unnecessary-pass