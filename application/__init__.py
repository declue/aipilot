"""Legacy namespace shim.

이 패키지는 기존 tests 코드에서 사용하던 'application.*' 네임스페이스를
현행 모듈 구조(dspilot_core, dspilot_cli, dspilot_app 등)로 매핑하기 위해
동적으로 하위 모듈을 주입합니다.
"""
import sys
from importlib import import_module

_MAPPING = {
    # LLM
    "application.llm": "dspilot_core.llm",
    "application.llm.agents": "dspilot_core.llm.agents",
    "application.llm.mcp": "dspilot_core.llm.mcp",
    "application.llm.utils": "dspilot_core.llm.utils",
    "application.llm.workflow": "dspilot_core.llm.workflow",
    "application.llm.monitoring": "dspilot_core.llm.monitoring",
    "application.llm.monitoring.metrics": "dspilot_core.llm.monitoring.metrics",
    # LLM models & services
    "application.llm.models": "dspilot_core.llm.models",
    "application.llm.services": "dspilot_core.llm.services",

    # Config
    "application.config": "dspilot_core.config",
    "application.config.libs": "dspilot_core.config.libs",

    # API (desktop app 기반)
    "application.api": "dspilot_app.api",
    "application.api.handlers": "dspilot_app.api.handlers",

    # CLI
    "application.cli": "dspilot_cli",
    "application.cli.constants": "dspilot_cli.constants",
    "application.cli.conversation_manager": "dspilot_cli.conversation_manager",
    "application.cli.output_manager": "dspilot_cli.output_manager",

    # UI
    "application.ui": "dspilot_app.ui",
    "application.ui.managers": "dspilot_app.ui.managers",
    "application.ui.managers.llm_tab_manager": "dspilot_app.ui.managers.llm_tab_manager",
    "application.ui.managers.ui_tab_manager": "dspilot_app.ui.managers.ui_tab_manager",

    # Tools (legacy path)
    "application.tools": "mcp_tools",

    # util
    "application.util": "dspilot_core.util",
    "application.util.logger": "dspilot_core.util.logger",
    "application.util.filter_engine": "dspilot_core.util.filter_engine",
    "application.util.friendly_message_builder": "dspilot_core.util.friendly_message_builder",
    "application.util.markdown_manager": "dspilot_core.util.markdown_manager",

    # tasks
    "application.tasks": "dspilot_core.tasks",
    "application.tasks.models": "dspilot_core.tasks.models",
    "application.tasks.services": "dspilot_core.tasks.services",
    "application.tasks.interfaces": "dspilot_core.tasks.interfaces",
    "application.tasks.exceptions": "dspilot_core.tasks.exceptions",

    # mcp tool submodule utils
    "application.llm.mcp.models": "dspilot_core.llm.models",

    # Legacy agent aliases
    "application.llm.llm_agent": "dspilot_core.llm.llm_agent",
    "application.llm.agents.basic_agent": "dspilot_core.llm.agents.basic_agent",

    # mcp tool utils
    "application.llm.mcp.mcp_tool_manager": "dspilot_core.llm.mcp.mcp_tool_manager",
    "application.llm.mcp.tool": "dspilot_core.llm.mcp.tool",
    "application.llm.mcp.tool.cache": "dspilot_core.llm.mcp.tool.cache",
    "application.llm.mcp.tool.converter": "dspilot_core.llm.mcp.tool.converter",
}

# 동적 모듈 등록
for alias, target in _MAPPING.items():
    try:
        module = import_module(target)
        sys.modules.setdefault(alias, module)
    except ModuleNotFoundError:  # target 미존재 시 무시
        continue

# 동적으로 util.*, tasks.*의 하위 모듈을 재귀 등록 (optional convenience)
def _register_submodules(base_alias: str, base_target: str):
    import pkgutil
    try:
        base_module = import_module(base_target)
    except ModuleNotFoundError:
        return
    pkg_path = getattr(base_module, "__path__", None)
    if not pkg_path:
        return
    for mod_info in pkgutil.iter_modules(pkg_path):
        sub_alias = f"{base_alias}.{mod_info.name}"
        sub_target = f"{base_target}.{mod_info.name}"
        try:
            sub_mod = import_module(sub_target)
            sys.modules.setdefault(sub_alias, sub_mod)
        except ModuleNotFoundError:
            continue

_register_submodules("application.util", "dspilot_core.util")
_register_submodules("application.tasks", "dspilot_core.tasks")

# 최상위 application 모듈이 하위 모듈 속성을 직접 노출하도록 설정
self_module = sys.modules[__name__]
for alias in _MAPPING.keys():
    if alias.count(".") == 1:  # application.<sub>
        sub_name = alias.split(".")[1]
        if alias in sys.modules:
            setattr(self_module, sub_name, sys.modules[alias])

del import_module, sys, _MAPPING 

# ----------------------------------------------------------------------------------
# 테스트 환경을 위한 Qt 라이브러리 더미 모듈 주입
# ----------------------------------------------------------------------------------

import sys as _sys
import types as _types


def _create_qt_stub(name: str):  # pragma: no cover
    mod = _types.ModuleType(name)

    class _Dummy:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass

        def __call__(self, *_, **__):  # noqa: D401
            return None

        def __getattr__(self, _item):  # noqa: D401
            return _Dummy()

        def __setattr__(self, _name, _value):  # noqa: D401
            pass

        def __iter__(self):  # noqa: D401
            return iter([])

    # 대표적인 Qt 클래스/함수 더미화
    for attr in [
        "QApplication",
        "QLabel",
        "QThreadPool",
        "QWidget",
        "QPushButton",
        "QComboBox",
        "QLineEdit",
        "QTextEdit",
        "QScrollArea",
        "QRunnable",
        "pyqtSlot",
        "Qt",
    ]:
        setattr(mod, attr, _Dummy)

    return mod


for _qt_pkg in (
    "PySide6",
    "PySide6.QtWidgets",
    "PySide6.QtCore",
    "PyQt5",
    "PyQt5.QtWidgets",
    "PyQt5.QtCore",
):
    if _qt_pkg not in _sys.modules:
        _sys.modules[_qt_pkg] = _create_qt_stub(_qt_pkg)

del _types, _create_qt_stub, _qt_pkg, _sys 