"""Legacy 'tools' namespace shim for backward-compat tests."""
import sys
from importlib import import_module

# weather 모듈 매핑
try:
    weather_mod = import_module("mcp_tools.weather_tool.weather")
    sys.modules.setdefault("tools.weather", weather_mod)
except ModuleNotFoundError:
    pass 

# ---------------------------------------------------------------------------
# remote_desktop 모듈 매핑 (가능하면 실제 구현, 실패 시 스텁)
# ---------------------------------------------------------------------------

try:
    _real_rd_mod = import_module("tools.remote_desktop_mcp.remote_desktop")
    sys.modules.setdefault("tools.remote_desktop", _real_rd_mod)
except ModuleNotFoundError:  # pragma: no cover – 환경에 따라 없을 수 있음
    import types as _types

    def _create_remote_desktop_stub():  # pragma: no cover
        mod = _types.ModuleType("tools.remote_desktop")

        def _make_result(success: bool, **extra):  # noqa: D401
            res = {"success": success}
            res.update(extra)
            return res

        # 함수들 – 파라미터에 따라 success 반환 값 단순 로직
        mod.capture_full_screen = lambda *_a, **_k: _make_result(True)
        mod.capture_region = lambda *_a, **_k: _make_result(True)
        mod.capture_with_annotation = lambda *_a, **_k: _make_result(True)
        mod.save_screenshot = lambda *_a, **_k: _make_result(True, file_path="/tmp/shot.png")
        mod.find_element_on_screen = lambda *_a, **_k: _make_result(False)
        mod.get_multimodal_analysis_data = lambda *_a, **_k: _make_result(True)
        mod.get_screen_info = lambda *_a, **_k: _make_result(True, screen_width=1920, screen_height=1080)

        return mod

    if "tools.remote_desktop" not in sys.modules:
        sys.modules["tools.remote_desktop"] = _create_remote_desktop_stub()

    del _types, _create_remote_desktop_stub 