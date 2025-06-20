import asyncio

from application.llm.workflow import BasicChatWorkflow


class DummyAgent:
    """LLMAgent 와 동일한 인터페이스 일부만 구현한 테스트용 더미"""

    async def _generate_basic_response(self, msg: str, streaming_cb=None):  # pylint: disable=unused-argument
        # 테스트 용이성을 위해 입력을 prefix 와 함께 반환
        return f"echo:{msg}"


def test_basic_chat_workflow_echo():
    workflow = BasicChatWorkflow()
    dummy_agent = DummyAgent()

    result = asyncio.run(workflow.run(dummy_agent, "hello"))

    assert result == "echo:hello" 