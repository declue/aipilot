import pytest

from dspilot_cli.cli_application import DSPilotCLI
from dspilot_cli.exceptions import ManagerInitializationError, SystemInitializationError


@pytest.mark.asyncio
async def test_initialize_failure(monkeypatch):
    """SystemManager 초기화 실패 시 SystemInitializationError 가 발생하는지 확인"""

    cli_app = DSPilotCLI(quiet_mode=True)

    async def fake_initialize(self):  # type: ignore  # noqa: D401
        return False, "강제 실패"

    # SystemManager.initialize 패치
    monkeypatch.setattr(
        cli_app.system_manager,
        "initialize",
        fake_initialize.__get__(cli_app.system_manager, type(cli_app.system_manager)),
    )

    with pytest.raises(SystemInitializationError):
        await cli_app.initialize()


@pytest.mark.asyncio
async def test_manager_initialization_failure(monkeypatch):
    """OutputManager 생성 실패 시 ManagerInitializationError 발생"""

    # OutputManager.__init__이 예외를 던지도록 패치
    from dspilot_cli import output_manager as om_module

    original_init = om_module.OutputManager.__init__

    def faulty_init(self, *args, **kwargs):  # type: ignore  # noqa: D401
        raise RuntimeError("init error")

    monkeypatch.setattr(om_module.OutputManager, "__init__", faulty_init)

    with pytest.raises(ManagerInitializationError):
        DSPilotCLI(quiet_mode=True)

    # 패치 복구
    monkeypatch.setattr(om_module.OutputManager, "__init__", original_init)


@pytest.mark.asyncio
async def test_cleanup_handles_errors(monkeypatch):
    """_cleanup 메소드가 내부 예외를 삼키고 종료까지 이어지는지 확인"""

    cli_app = DSPilotCLI(quiet_mode=True)

    async def faulty_cleanup(self):  # type: ignore  # noqa: D401
        raise RuntimeError("cleanup fail")

    monkeypatch.setattr(
        cli_app.system_manager,
        "cleanup",
        faulty_cleanup.__get__(cli_app.system_manager, type(cli_app.system_manager)),
    )

    # 예외가 전파되지 않아야 함
    try:
        await cli_app._cleanup()
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"_cleanup 이 예외를 전파했습니다: {exc}") 