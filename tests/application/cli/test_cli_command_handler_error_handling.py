import pytest

from dspilot_cli.cli_command_handler import CommandHandler
from dspilot_cli.exceptions import CommandHandlerError
from dspilot_cli.output_manager import OutputManager


class DummySystemManager:
    """필요 최소한의 인터페이스만 가진 스텁 SystemManager"""

    async def get_tools_list(self):
        return []

    def get_system_status(self):
        return []

    def get_llm_agent(self):
        return None


class DummyConversationManager:
    def __init__(self):
        self.conversation_history = []

    def get_pending_actions(self):
        return []

    def clear_conversation(self):
        pass


@pytest.mark.asyncio
async def test_handle_command_unexpected_error(monkeypatch):
    """_show_tools 가 예외를 발생시킬 때 CommandHandlerError 로 래핑되는지 테스트"""

    output_manager = OutputManager(quiet_mode=True)
    conv_manager = DummyConversationManager()
    system_manager = DummySystemManager()

    handler = CommandHandler(output_manager, conv_manager, system_manager)

    async def faulty_show_tools():  # type: ignore
        raise RuntimeError("tool list failed")

    monkeypatch.setattr(handler, "_show_tools", faulty_show_tools)

    with pytest.raises(CommandHandlerError):
        await handler.handle_command("tools") 