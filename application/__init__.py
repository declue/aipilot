"""Legacy compatibility shim for `application` namespace.

This package forwards legacy imports like `application.llm` or `application.ui` to
new module locations under `dspilot_core` / `dspilot_app`.
It enables older tests that rely on the historical `application` package path.
"""
import sys
from types import ModuleType

# Mapping table: legacy sub-module -> actual module path
_MAPPING = {
    "application.llm": "dspilot_core.llm",
    "application.llm.agents": "dspilot_core.llm.agents",
    "application.llm.mcp": "dspilot_core.llm.mcp",
    "application.llm.workflow": "dspilot_core.llm.workflow",
    "application.llm.monitoring": "dspilot_core.llm.monitoring",
    "application.ui": "dspilot_app.ui",
    "application.ui.managers": "dspilot_app.ui.managers",
    "application.ui.presentation": "dspilot_app.ui.presentation",
    "application.api": "dspilot_app.api",
    "application.config": "dspilot_core.config",
    "application.cli": "dspilot_cli",
}

for legacy, real in _MAPPING.items():
    if legacy not in sys.modules:
        module = ModuleType(legacy)
        sys.modules[legacy] = module
    # Set up attribute forwarding lazily using importlib
    parent_name, _, child_name = legacy.rpartition(".")
    parent_mod = sys.modules.get(parent_name)
    # attach attribute to parent for dot access
    if parent_mod and not hasattr(parent_mod, child_name):
        setattr(parent_mod, child_name, sys.modules[legacy])


def __getattr__(name):  # type: ignore[override]
    full = f"application.{name}"
    target = _MAPPING.get(full)
    if target:
        __import__(target)
        return sys.modules[target]
    # 동적 prefix 매핑 ---------------------------------------------------------
    if full.startswith("application.config."):
        tail = full[len("application.config.") :]
        real = f"dspilot_core.config.{tail}"
        try:
            __import__(real)
            sys.modules[full] = sys.modules[real]
            return sys.modules[real]
        except Exception:
            pass
    if full.startswith("application.ui."):
        tail = full[len("application.ui.") :]
        real = f"dspilot_app.ui.{tail}"
        try:
            __import__(real)
            sys.modules[full] = sys.modules[real]
            return sys.modules[real]
        except Exception:
            pass
    if full.startswith("application.llm."):
        tail = full[len("application.llm.") :]
        real = f"dspilot_core.llm.{tail}"
        try:
            __import__(real)
            sys.modules[full] = sys.modules[real]
            return sys.modules[real]
        except Exception:
            pass
    if full.startswith("application.cli."):
        tail = full[len("application.cli.") :]
        real = f"dspilot_cli.{tail}"
        try:
            __import__(real)
            sys.modules[full] = sys.modules[real]
            return sys.modules[real]
        except Exception:
            pass
    raise AttributeError(name) 