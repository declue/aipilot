import pytest

from dspilot_cli.cli_mode_handler import ModeHandler
from dspilot_cli.exceptions import ModeHandlerError
from dspilot_cli.output_manager import OutputManager


class DummyQueryProcessor:
    async def process_query(self, _query):  # noqa: D401
        raise RuntimeError("processing failed")


class DummyInteractionManager:
    def get_user_input(self, _prompt):  # noqa: D401
        return "exit"


class DummyCommandHandler:
    async def handle_command(self, _cmd):  # noqa: D401
        return False


@pytest.mark.asyncio
async def test_run_single_query_error():
    """process_query 가 예외를 던질 때 ModeHandlerError 로 래핑되는지 테스트"""

    output_manager = OutputManager(quiet_mode=True)
    qp = DummyQueryProcessor()
    im = DummyInteractionManager()
    ch = DummyCommandHandler()

    handler = ModeHandler(output_manager, im, ch, qp)  # type: ignore[arg-type]

    with pytest.raises(ModeHandlerError):
        await handler.run_single_query("테스트") 