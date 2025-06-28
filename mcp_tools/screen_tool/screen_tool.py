import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, Tuple

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("pyautogui 라이브러리가 설치되지 않았습니다. 'pip install pyautogui'로 설치하세요.")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL 라이브러리가 설치되지 않았습니다. 'pip install pillow'로 설치하세요.")

# For window capture
if sys.platform == 'win32':
    try:
        import win32gui
        import win32ui
        import win32con
        import win32api
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
        print("win32gui 라이브러리가 설치되지 않았습니다. 'pip install pywin32'로 설치하세요.")
elif sys.platform == 'darwin':  # macOS
    try:
        import Quartz
        QUARTZ_AVAILABLE = True
    except ImportError:
        QUARTZ_AVAILABLE = False
        print("Quartz 라이브러리가 설치되지 않았습니다. macOS에서 윈도우 캡처를 위해 필요합니다.")
else:  # Linux
    try:
        import Xlib
        XLIB_AVAILABLE = True
    except ImportError:
        XLIB_AVAILABLE = False
        print("Xlib 라이브러리가 설치되지 않았습니다. Linux에서 윈도우 캡처를 위해 필요합니다.")

from mcp.server.fastmcp import FastMCP

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 screen_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "screen_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("SCREEN_TOOL_LOG_LEVEL", "WARNING").upper()
log_level_int = getattr(logging, log_level, logging.WARNING)

logging.basicConfig(
    level=log_level_int,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(log_file_path),
              logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# INFO 레벨 로그는 환경 변수가 DEBUG나 INFO로 설정된 경우에만 출력
if log_level_int <= logging.INFO:
    logger.info("Screen Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
    logger.info("운영체제: %s", sys.platform)
    logger.info("pyautogui 사용 가능: %s", PYAUTOGUI_AVAILABLE)
    logger.info("PIL 사용 가능: %s", PIL_AVAILABLE)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="Screen Capture Server",
    description="A server for screen capture operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

class ScreenCaptureService:
    """화면 캡처 기능을 제공하는 서비스 클래스"""

    def __init__(self):
        """ScreenCaptureService 초기화"""
        self.logger = logging.getLogger(__name__)
        self._check_dependencies()

    def _check_dependencies(self):
        """필요한 라이브러리가 설치되어 있는지 확인"""
        if not PYAUTOGUI_AVAILABLE:
            self.logger.error("pyautogui 라이브러리가 설치되지 않았습니다.")
        if not PIL_AVAILABLE:
            self.logger.error("PIL 라이브러리가 설치되지 않았습니다.")

        # 운영체제별 윈도우 캡처 라이브러리 확인
        if sys.platform == 'win32' and not WIN32_AVAILABLE:
            self.logger.warning("win32gui 라이브러리가 설치되지 않아 윈도우 캡처 기능이 제한됩니다.")
        elif sys.platform == 'darwin' and not QUARTZ_AVAILABLE:
            self.logger.warning("Quartz 라이브러리가 설치되지 않아 윈도우 캡처 기능이 제한됩니다.")
        elif sys.platform != 'win32' and sys.platform != 'darwin' and not XLIB_AVAILABLE:
            self.logger.warning("Xlib 라이브러리가 설치되지 않아 윈도우 캡처 기능이 제한됩니다.")

    def capture_screen(self, output_path: str = None) -> Optional[Image.Image]:
        """
        전체 화면을 캡처합니다.

        Args:
            output_path (str, optional): 이미지를 저장할 경로. 지정하지 않으면 이미지 객체만 반환합니다.

        Returns:
            Optional[Image.Image]: 캡처된 이미지 객체. 실패 시 None 반환.
        """
        if not PYAUTOGUI_AVAILABLE or not PIL_AVAILABLE:
            self.logger.error("필요한 라이브러리가 설치되지 않아 화면 캡처를 수행할 수 없습니다.")
            return None

        try:
            screenshot = pyautogui.screenshot()

            if output_path:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                screenshot.save(output_path)
                self.logger.info(f"전체 화면 캡처 이미지가 {output_path}에 저장되었습니다.")

            return screenshot
        except Exception as e:
            self.logger.error(f"전체 화면 캡처 중 오류 발생: {str(e)}")
            return None

    def capture_monitor(self, monitor_num: int = 0, output_path: str = None) -> Optional[Image.Image]:
        """
        특정 모니터 화면을 캡처합니다.

        Args:
            monitor_num (int): 캡처할 모니터 번호 (0부터 시작)
            output_path (str, optional): 이미지를 저장할 경로

        Returns:
            Optional[Image.Image]: 캡처된 이미지 객체. 실패 시 None 반환.
        """
        if not PYAUTOGUI_AVAILABLE or not PIL_AVAILABLE:
            self.logger.error("필요한 라이브러리가 설치되지 않아 화면 캡처를 수행할 수 없습니다.")
            return None

        try:
            # 모니터 정보 가져오기
            monitors = self.get_monitors_info()

            if monitor_num < 0 or monitor_num >= len(monitors):
                self.logger.error(f"유효하지 않은 모니터 번호: {monitor_num}. 사용 가능한 모니터: 0-{len(monitors)-1}")
                return None

            monitor = monitors[monitor_num]
            left, top, width, height = monitor['left'], monitor['top'], monitor['width'], monitor['height']

            # 해당 모니터 영역 캡처
            screenshot = pyautogui.screenshot(region=(left, top, width, height))

            if output_path:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                screenshot.save(output_path)
                self.logger.info(f"모니터 {monitor_num} 캡처 이미지가 {output_path}에 저장되었습니다.")

            return screenshot
        except Exception as e:
            self.logger.error(f"모니터 캡처 중 오류 발생: {str(e)}")
            return None

    def capture_region(self, left: int, top: int, width: int, height: int, output_path: str = None) -> Optional[Image.Image]:
        """
        지정된 영역을 캡처합니다.

        Args:
            left (int): 왼쪽 좌표
            top (int): 위쪽 좌표
            width (int): 너비
            height (int): 높이
            output_path (str, optional): 이미지를 저장할 경로

        Returns:
            Optional[Image.Image]: 캡처된 이미지 객체. 실패 시 None 반환.
        """
        if not PYAUTOGUI_AVAILABLE or not PIL_AVAILABLE:
            self.logger.error("필요한 라이브러리가 설치되지 않아 화면 캡처를 수행할 수 없습니다.")
            return None

        try:
            screenshot = pyautogui.screenshot(region=(left, top, width, height))

            if output_path:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                screenshot.save(output_path)
                self.logger.info(f"영역 캡처 이미지가 {output_path}에 저장되었습니다.")

            return screenshot
        except Exception as e:
            self.logger.error(f"영역 캡처 중 오류 발생: {str(e)}")
            return None

    def capture_window(self, window_name: str, output_path: str = None) -> Optional[Image.Image]:
        """
        특정 윈도우를 캡처합니다.

        Args:
            window_name (str): 캡처할 윈도우의 이름 (부분 일치)
            output_path (str, optional): 이미지를 저장할 경로

        Returns:
            Optional[Image.Image]: 캡처된 이미지 객체. 실패 시 None 반환.
        """
        if not PIL_AVAILABLE:
            self.logger.error("PIL 라이브러리가 설치되지 않아 화면 캡처를 수행할 수 없습니다.")
            return None

        # Windows 환경
        if sys.platform == 'win32':
            if not WIN32_AVAILABLE:
                self.logger.error("win32gui 라이브러리가 설치되지 않아 윈도우 캡처를 수행할 수 없습니다.")
                return None

            try:
                # 윈도우 핸들 찾기
                hwnd = self._find_window_win32(window_name)
                if not hwnd:
                    self.logger.error(f"'{window_name}' 이름의 윈도우를 찾을 수 없습니다.")
                    return None

                # 윈도우 크기 가져오기
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                width, height = right - left, bottom - top

                # 윈도우가 최소화되어 있는지 확인
                if width == 0 or height == 0:
                    self.logger.error("윈도우가 최소화되어 있어 캡처할 수 없습니다.")
                    return None

                # 윈도우 캡처
                hwndDC = win32gui.GetWindowDC(hwnd)
                mfcDC = win32ui.CreateDCFromHandle(hwndDC)
                saveDC = mfcDC.CreateCompatibleDC()
                saveBitMap = win32ui.CreateBitmap()
                saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
                saveDC.SelectObject(saveBitMap)

                # 윈도우 내용 복사
                result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

                # 비트맵을 PIL 이미지로 변환
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1)

                # 리소스 해제
                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(hwnd, hwndDC)

                if output_path:
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    img.save(output_path)
                    self.logger.info(f"윈도우 '{window_name}' 캡처 이미지가 {output_path}에 저장되었습니다.")

                return img
            except Exception as e:
                self.logger.error(f"윈도우 캡처 중 오류 발생: {str(e)}")
                return None

        # macOS 환경
        elif sys.platform == 'darwin':
            if not QUARTZ_AVAILABLE:
                self.logger.error("Quartz 라이브러리가 설치되지 않아 윈도우 캡처를 수행할 수 없습니다.")
                return None

            try:
                # 윈도우 목록 가져오기
                window_list = Quartz.CGWindowListCopyWindowInfo(
                    Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                    Quartz.kCGNullWindowID)

                target_window = None
                for window in window_list:
                    window_title = window.get('kCGWindowName', '')
                    if window_title and window_name.lower() in window_title.lower():
                        target_window = window
                        break

                if not target_window:
                    self.logger.error(f"'{window_name}' 이름의 윈도우를 찾을 수 없습니다.")
                    return None

                window_id = target_window.get('kCGWindowNumber')
                bounds = target_window.get('kCGWindowBounds')

                # 윈도우 이미지 캡처
                image_ref = Quartz.CGWindowListCreateImage(
                    Quartz.CGRectNull,
                    Quartz.kCGWindowListOptionIncludingWindow,
                    window_id,
                    Quartz.kCGWindowImageBoundsIgnoreFraming | Quartz.kCGWindowImageShouldBeOpaque)

                # CoreGraphics 이미지를 PIL 이미지로 변환
                width = Quartz.CGImageGetWidth(image_ref)
                height = Quartz.CGImageGetHeight(image_ref)

                # 이미지 데이터 가져오기
                data_provider = Quartz.CGImageGetDataProvider(image_ref)
                data = Quartz.CGDataProviderCopyData(data_provider)

                # PIL 이미지로 변환
                img = Image.frombuffer('RGBA', (width, height), data, 'raw', 'BGRA', 0, 1)

                if output_path:
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    img.save(output_path)
                    self.logger.info(f"윈도우 '{window_name}' 캡처 이미지가 {output_path}에 저장되었습니다.")

                return img
            except Exception as e:
                self.logger.error(f"윈도우 캡처 중 오류 발생: {str(e)}")
                return None

        # Linux 환경
        else:
            if not XLIB_AVAILABLE:
                self.logger.error("Xlib 라이브러리가 설치되지 않아 윈도우 캡처를 수행할 수 없습니다.")
                return None

            try:
                # Linux에서 윈도우 캡처 구현
                # 이 부분은 Xlib를 사용한 구현이 필요하지만, 복잡하므로 대안으로 pyautogui를 사용
                self.logger.warning("Linux에서 윈도우 이름으로 캡처하는 기능은 제한적입니다. 전체 화면 캡처로 대체합니다.")
                return self.capture_screen(output_path)
            except Exception as e:
                self.logger.error(f"윈도우 캡처 중 오류 발생: {str(e)}")
                return None

    def _find_window_win32(self, window_name: str) -> int:
        """
        Windows 환경에서 윈도우 이름으로 윈도우 핸들을 찾습니다.

        Args:
            window_name (str): 찾을 윈도우 이름 (부분 일치)

        Returns:
            int: 윈도우 핸들. 찾지 못한 경우 0 반환.
        """
        if sys.platform != 'win32' or not WIN32_AVAILABLE:
            return 0

        result = 0

        def enum_windows_callback(hwnd, result):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if window_name.lower() in window_title.lower():
                    result.append(hwnd)
            return True

        window_handles = []
        win32gui.EnumWindows(enum_windows_callback, window_handles)

        if window_handles:
            return window_handles[0]
        return 0

    def get_monitors_info(self) -> List[Dict[str, int]]:
        """
        연결된 모니터 정보를 가져옵니다.

        Returns:
            List[Dict[str, int]]: 모니터 정보 목록. 각 항목은 left, top, width, height 키를 포함합니다.
        """
        if not PYAUTOGUI_AVAILABLE:
            self.logger.error("pyautogui 라이브러리가 설치되지 않아 모니터 정보를 가져올 수 없습니다.")
            return []

        try:
            # Windows 환경
            if sys.platform == 'win32' and WIN32_AVAILABLE:
                monitors = []
                for i, monitor in enumerate(win32api.EnumDisplayMonitors()):
                    monitor_info = win32api.GetMonitorInfo(monitor[0])
                    monitor_rect = monitor_info['Monitor']
                    left, top, right, bottom = monitor_rect
                    monitors.append({
                        'left': left,
                        'top': top,
                        'width': right - left,
                        'height': bottom - top
                    })
                return monitors

            # macOS 환경
            elif sys.platform == 'darwin' and QUARTZ_AVAILABLE:
                monitors = []
                displays = Quartz.CGDisplayCopyAllDisplayModes(Quartz.CGMainDisplayID(), None)
                for i in range(Quartz.CGDisplayCount()):
                    display_id = Quartz.CGGetDisplaysWithRect(
                        Quartz.CGRectMake(0, 0, 100000, 100000), 
                        1, 
                        None, 
                        None)[i]

                    bounds = Quartz.CGDisplayBounds(display_id)
                    monitors.append({
                        'left': int(bounds.origin.x),
                        'top': int(bounds.origin.y),
                        'width': int(bounds.size.width),
                        'height': int(bounds.size.height)
                    })
                return monitors

            # 기타 환경 또는 라이브러리 미설치 시 pyautogui로 대체
            else:
                # pyautogui는 다중 모니터 정보를 직접 제공하지 않으므로, 전체 화면 크기만 반환
                width, height = pyautogui.size()
                return [{'left': 0, 'top': 0, 'width': width, 'height': height}]
        except Exception as e:
            self.logger.error(f"모니터 정보 가져오기 중 오류 발생: {str(e)}")
            # 오류 발생 시 기본값 반환
            width, height = pyautogui.size()
            return [{'left': 0, 'top': 0, 'width': width, 'height': height}]

# 전역 서비스 인스턴스
_screen_capture_service = None

def _get_service() -> ScreenCaptureService:
    """
    ScreenCaptureService 인스턴스를 가져옵니다.

    Returns:
        ScreenCaptureService: 서비스 인스턴스
    """
    global _screen_capture_service
    if _screen_capture_service is None:
        _screen_capture_service = ScreenCaptureService()
    return _screen_capture_service

@app.tool()
def capture_screen(output_path: str = None) -> dict:
    """
    전체 화면을 캡처합니다.

    Args:
        output_path (str, optional): 이미지를 저장할 경로. 지정하지 않으면 이미지 객체만 반환합니다.

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> capture_screen("/path/to/screenshot.png")
        {'result': {'action': 'capture_screen', 'path': '/path/to/screenshot.png', 'success': True}}
    """
    try:
        screenshot = _get_service().capture_screen(output_path)

        if screenshot is None:
            return {"error": "화면 캡처 실패"}

        return {
            "result": {
                "action": "capture_screen",
                "path": output_path if output_path else "이미지가 저장되지 않음",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"화면 캡처 중 오류 발생: {str(e)}"}

@app.tool()
def capture_monitor(monitor_num: int = 0, output_path: str = None) -> dict:
    """
    특정 모니터 화면을 캡처합니다.

    Args:
        monitor_num (int): 캡처할 모니터 번호 (0부터 시작)
        output_path (str, optional): 이미지를 저장할 경로

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> capture_monitor(0, "/path/to/monitor0.png")
        {'result': {'action': 'capture_monitor', 'monitor': 0, 'path': '/path/to/monitor0.png', 'success': True}}
    """
    try:
        screenshot = _get_service().capture_monitor(monitor_num, output_path)

        if screenshot is None:
            return {"error": f"모니터 {monitor_num} 캡처 실패"}

        return {
            "result": {
                "action": "capture_monitor",
                "monitor": monitor_num,
                "path": output_path if output_path else "이미지가 저장되지 않음",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"모니터 캡처 중 오류 발생: {str(e)}"}

@app.tool()
def capture_region(left: int, top: int, width: int, height: int, output_path: str = None) -> dict:
    """
    지정된 영역을 캡처합니다.

    Args:
        left (int): 왼쪽 좌표
        top (int): 위쪽 좌표
        width (int): 너비
        height (int): 높이
        output_path (str, optional): 이미지를 저장할 경로

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> capture_region(0, 0, 800, 600, "/path/to/region.png")
        {'result': {'action': 'capture_region', 'region': {'left': 0, 'top': 0, 'width': 800, 'height': 600}, 'path': '/path/to/region.png', 'success': True}}
    """
    try:
        screenshot = _get_service().capture_region(left, top, width, height, output_path)

        if screenshot is None:
            return {"error": f"영역 캡처 실패: ({left}, {top}, {width}, {height})"}

        return {
            "result": {
                "action": "capture_region",
                "region": {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height
                },
                "path": output_path if output_path else "이미지가 저장되지 않음",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"영역 캡처 중 오류 발생: {str(e)}"}

@app.tool()
def capture_window(window_name: str, output_path: str = None) -> dict:
    """
    특정 윈도우를 캡처합니다.

    Args:
        window_name (str): 캡처할 윈도우의 이름 (부분 일치)
        output_path (str, optional): 이미지를 저장할 경로

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> capture_window("Chrome", "/path/to/chrome_window.png")
        {'result': {'action': 'capture_window', 'window_name': 'Chrome', 'path': '/path/to/chrome_window.png', 'success': True}}
    """
    try:
        screenshot = _get_service().capture_window(window_name, output_path)

        if screenshot is None:
            return {"error": f"윈도우 '{window_name}' 캡처 실패"}

        return {
            "result": {
                "action": "capture_window",
                "window_name": window_name,
                "path": output_path if output_path else "이미지가 저장되지 않음",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"윈도우 캡처 중 오류 발생: {str(e)}"}

@app.tool()
def get_monitors_info() -> dict:
    """
    연결된 모니터 정보를 가져옵니다.

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> get_monitors_info()
        {'result': {'action': 'get_monitors_info', 'monitors': [{'left': 0, 'top': 0, 'width': 1920, 'height': 1080}, ...], 'count': 2, 'success': True}}
    """
    try:
        monitors = _get_service().get_monitors_info()

        if not monitors:
            return {"error": "모니터 정보를 가져오는데 실패했습니다."}

        return {
            "result": {
                "action": "get_monitors_info",
                "monitors": monitors,
                "count": len(monitors),
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"모니터 정보를 가져오는 중 오류 발생: {str(e)}"}

@app.tool()
def get_tool_info() -> dict:
    """
    스크린 캡처 도구 정보를 반환합니다.

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> get_tool_info()
        {'result': {'name': 'screen_tool', 'description': '화면 캡처 기능을 제공하는 도구', ...}}
    """
    try:
        tool_info = {
            "name": "screen_tool",
            "description": "화면 캡처 기능을 제공하는 도구",
            "version": "1.0.0",
            "author": "DS Pilot",
            "functions": [
                {
                    "name": "capture_screen",
                    "description": "전체 화면을 캡처합니다.",
                    "parameters": [
                        {
                            "name": "output_path",
                            "type": "str",
                            "description": "이미지를 저장할 경로 (선택사항)",
                            "required": False
                        }
                    ],
                    "returns": {
                        "type": "dict",
                        "description": "결과를 포함한 딕셔너리"
                    }
                },
                {
                    "name": "capture_monitor",
                    "description": "특정 모니터 화면을 캡처합니다.",
                    "parameters": [
                        {
                            "name": "monitor_num",
                            "type": "int",
                            "description": "캡처할 모니터 번호 (0부터 시작)",
                            "required": False,
                            "default": 0
                        },
                        {
                            "name": "output_path",
                            "type": "str",
                            "description": "이미지를 저장할 경로 (선택사항)",
                            "required": False
                        }
                    ],
                    "returns": {
                        "type": "dict",
                        "description": "결과를 포함한 딕셔너리"
                    }
                },
                {
                    "name": "capture_region",
                    "description": "지정된 영역을 캡처합니다.",
                    "parameters": [
                        {
                            "name": "left",
                            "type": "int",
                            "description": "왼쪽 좌표",
                            "required": True
                        },
                        {
                            "name": "top",
                            "type": "int",
                            "description": "위쪽 좌표",
                            "required": True
                        },
                        {
                            "name": "width",
                            "type": "int",
                            "description": "너비",
                            "required": True
                        },
                        {
                            "name": "height",
                            "type": "int",
                            "description": "높이",
                            "required": True
                        },
                        {
                            "name": "output_path",
                            "type": "str",
                            "description": "이미지를 저장할 경로 (선택사항)",
                            "required": False
                        }
                    ],
                    "returns": {
                        "type": "dict",
                        "description": "결과를 포함한 딕셔너리"
                    }
                },
                {
                    "name": "capture_window",
                    "description": "특정 윈도우를 캡처합니다.",
                    "parameters": [
                        {
                            "name": "window_name",
                            "type": "str",
                            "description": "캡처할 윈도우의 이름 (부분 일치)",
                            "required": True
                        },
                        {
                            "name": "output_path",
                            "type": "str",
                            "description": "이미지를 저장할 경로 (선택사항)",
                            "required": False
                        }
                    ],
                    "returns": {
                        "type": "dict",
                        "description": "결과를 포함한 딕셔너리"
                    }
                },
                {
                    "name": "get_monitors_info",
                    "description": "연결된 모니터 정보를 가져옵니다.",
                    "parameters": [],
                    "returns": {
                        "type": "dict",
                        "description": "결과를 포함한 딕셔너리"
                    }
                }
            ],
            "dependencies": [
                {
                    "name": "pyautogui",
                    "required": True,
                    "installed": PYAUTOGUI_AVAILABLE
                },
                {
                    "name": "PIL (Pillow)",
                    "required": True,
                    "installed": PIL_AVAILABLE
                },
                {
                    "name": "pywin32 (Windows only)",
                    "required": sys.platform == 'win32',
                    "installed": sys.platform != 'win32' or WIN32_AVAILABLE
                },
                {
                    "name": "Quartz (macOS only)",
                    "required": sys.platform == 'darwin',
                    "installed": sys.platform != 'darwin' or QUARTZ_AVAILABLE
                },
                {
                    "name": "Xlib (Linux only)",
                    "required": sys.platform != 'win32' and sys.platform != 'darwin',
                    "installed": (sys.platform == 'win32' or sys.platform == 'darwin') or XLIB_AVAILABLE
                }
            ]
        }

        return {
            "result": tool_info
        }
    except Exception as e:
        return {"error": f"도구 정보를 가져오는 중 오류 발생: {str(e)}"}


if __name__ == "__main__":
    try:
        logger.info("FastMCP app.run() 호출 시작...")
        app.run(transport=TRANSPORT)
        logger.info("FastMCP app.run() 정상 종료.")
    except Exception as e:
        logger.error("screen_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise
