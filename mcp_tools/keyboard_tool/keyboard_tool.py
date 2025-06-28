#!/usr/bin/env python3
"""
Keyboard Event MCP Server
키보드 이벤트를 처리하고 제어하는 도구를 제공합니다.
Windows와 macOS 모두에서 동작하는 크로스 플랫폼 키보드 이벤트 처리 기능을 제공합니다.
"""

import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import Thread, Event, Lock
from typing import Dict, List, Optional, Any, Union, Callable

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("pynput 라이브러리가 설치되지 않았습니다. 'pip install pynput'로 설치하세요.")

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("pyautogui 라이브러리가 설치되지 않았습니다. 'pip install pyautogui'로 설치하세요.")

from mcp.server.fastmcp import FastMCP

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 keyboard_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "keyboard_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("KEYBOARD_TOOL_LOG_LEVEL", "WARNING").upper()
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
    logger.info("Keyboard Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
    logger.info("운영체제: %s", sys.platform)
    logger.info("pynput 사용 가능: %s", PYNPUT_AVAILABLE)
    logger.info("pyautogui 사용 가능: %s", PYAUTOGUI_AVAILABLE)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="Keyboard Event Server",
    description="A server for keyboard event operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 키보드 이벤트 타입 정의
class KeyEventType(str, Enum):
    """키보드 이벤트 타입"""
    PRESS = "press"
    RELEASE = "release"
    TAP = "tap"  # 누르고 떼기


@dataclass
class KeyEvent:
    """키보드 이벤트를 담는 데이터 클래스"""
    key: str
    event_type: KeyEventType
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    modifiers: List[str] = field(default_factory=list)
    character: str = ""
    scan_code: int = 0
    vk_code: int = 0


@dataclass
class KeyboardState:
    """키보드 상태를 담는 데이터 클래스"""
    pressed_keys: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    caps_lock: bool = False
    num_lock: bool = False
    scroll_lock: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class KeyboardEventService:
    """키보드 이벤트 서비스 클래스"""

    def __init__(self):
        """키보드 이벤트 서비스 초기화"""
        self.listener = None
        self.is_listening = False
        self.stop_event = Event()
        self.callback = None
        self.pressed_keys = set()
        self.lock = Lock()
        self.recorded_events = []
        self.recording = False
        
        # 플랫폼 확인
        self.platform = sys.platform
        if self.platform.startswith('win'):
            self.platform_name = 'Windows'
        elif self.platform.startswith('darwin'):
            self.platform_name = 'macOS'
        elif self.platform.startswith('linux'):
            self.platform_name = 'Linux'
        else:
            self.platform_name = 'Unknown'
            
        logger.info(f"플랫폼: {self.platform_name}")
        
        # 라이브러리 사용 가능 여부 확인
        self.use_pynput = PYNPUT_AVAILABLE
        self.use_pyautogui = PYAUTOGUI_AVAILABLE
        
        if not self.use_pynput and not self.use_pyautogui:
            logger.warning("키보드 이벤트 처리를 위한 라이브러리가 설치되지 않았습니다.")

    def start_listening(self, callback: Callable = None) -> bool:
        """
        키보드 이벤트 리스닝을 시작합니다.
        
        Args:
            callback: 이벤트 발생 시 호출할 콜백 함수 (선택 사항)
            
        Returns:
            bool: 성공 여부
        """
        if self.is_listening:
            logger.warning("이미 키보드 이벤트 리스닝 중입니다.")
            return False
            
        if not self.use_pynput:
            logger.error("pynput 라이브러리가 설치되지 않아 키보드 이벤트 리스닝을 시작할 수 없습니다.")
            return False
            
        self.callback = callback
        self.stop_event.clear()
        self.is_listening = True
        
        try:
            # 키보드 리스너 시작
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self.listener.start()
            logger.info("키보드 이벤트 리스닝을 시작했습니다.")
            return True
        except Exception as e:
            logger.error(f"키보드 이벤트 리스닝 시작 중 오류 발생: {e}")
            self.is_listening = False
            return False

    def stop_listening(self) -> bool:
        """
        키보드 이벤트 리스닝을 중지합니다.
        
        Returns:
            bool: 성공 여부
        """
        if not self.is_listening:
            logger.warning("키보드 이벤트 리스닝 중이 아닙니다.")
            return False
            
        try:
            self.stop_event.set()
            if self.listener:
                self.listener.stop()
                self.listener = None
            self.is_listening = False
            logger.info("키보드 이벤트 리스닝을 중지했습니다.")
            return True
        except Exception as e:
            logger.error(f"키보드 이벤트 리스닝 중지 중 오류 발생: {e}")
            return False

    def _on_press(self, key):
        """
        키 눌림 이벤트 핸들러
        
        Args:
            key: 눌린 키
        """
        try:
            with self.lock:
                # 키 정보 추출
                key_str, char, scan_code, vk = self._extract_key_info(key)
                
                # 이미 눌린 키인지 확인
                if key_str in self.pressed_keys:
                    return
                    
                # 눌린 키 추가
                self.pressed_keys.add(key_str)
                
                # 이벤트 생성
                modifiers = self._get_modifiers()
                event = KeyEvent(
                    key=key_str,
                    event_type=KeyEventType.PRESS,
                    modifiers=modifiers,
                    character=char,
                    scan_code=scan_code,
                    vk_code=vk
                )
                
                # 이벤트 기록 (녹화 중인 경우)
                if self.recording:
                    self.recorded_events.append(event)
                
                # 콜백 호출
                if self.callback:
                    self.callback(event)
                    
                logger.debug(f"키 눌림: {key_str}, 수정자: {modifiers}")
        except Exception as e:
            logger.error(f"키 눌림 이벤트 처리 중 오류 발생: {e}")

    def _on_release(self, key):
        """
        키 뗌 이벤트 핸들러
        
        Args:
            key: 떼진 키
        """
        try:
            with self.lock:
                # 키 정보 추출
                key_str, char, scan_code, vk = self._extract_key_info(key)
                
                # 눌린 키에서 제거
                if key_str in self.pressed_keys:
                    self.pressed_keys.remove(key_str)
                
                # 이벤트 생성
                modifiers = self._get_modifiers()
                event = KeyEvent(
                    key=key_str,
                    event_type=KeyEventType.RELEASE,
                    modifiers=modifiers,
                    character=char,
                    scan_code=scan_code,
                    vk_code=vk
                )
                
                # 이벤트 기록 (녹화 중인 경우)
                if self.recording:
                    self.recorded_events.append(event)
                
                # 콜백 호출
                if self.callback:
                    self.callback(event)
                    
                logger.debug(f"키 뗌: {key_str}, 수정자: {modifiers}")
                
                # 리스닝 중지 확인
                if self.stop_event.is_set():
                    return False
        except Exception as e:
            logger.error(f"키 뗌 이벤트 처리 중 오류 발생: {e}")

    def _extract_key_info(self, key) -> tuple:
        """
        키 정보를 추출합니다.
        
        Args:
            key: pynput 키 객체
            
        Returns:
            tuple: (key_str, character, scan_code, vk_code)
        """
        try:
            # 특수 키인 경우
            if hasattr(key, 'name'):
                return key.name, '', getattr(key, 'scan_code', 0), getattr(key, 'vk', 0)
            # 일반 문자 키인 경우
            else:
                char = key.char if hasattr(key, 'char') else ''
                return char, char, getattr(key, 'scan_code', 0), getattr(key, 'vk', 0)
        except Exception as e:
            logger.error(f"키 정보 추출 중 오류 발생: {e}")
            return str(key), '', 0, 0

    def _get_modifiers(self) -> List[str]:
        """
        현재 눌린 수정자 키 목록을 반환합니다.
        
        Returns:
            List[str]: 수정자 키 목록
        """
        modifiers = []
        if 'shift' in self.pressed_keys or 'shift_r' in self.pressed_keys or 'shift_l' in self.pressed_keys:
            modifiers.append('shift')
        if 'ctrl' in self.pressed_keys or 'ctrl_r' in self.pressed_keys or 'ctrl_l' in self.pressed_keys:
            modifiers.append('ctrl')
        if 'alt' in self.pressed_keys or 'alt_r' in self.pressed_keys or 'alt_l' in self.pressed_keys:
            modifiers.append('alt')
        if 'cmd' in self.pressed_keys or 'cmd_r' in self.pressed_keys or 'cmd_l' in self.pressed_keys:
            modifiers.append('cmd')
        return modifiers

    def get_keyboard_state(self) -> KeyboardState:
        """
        현재 키보드 상태를 반환합니다.
        
        Returns:
            KeyboardState: 키보드 상태 객체
        """
        with self.lock:
            # 현재 눌린 키 목록
            pressed_keys = list(self.pressed_keys)
            
            # 수정자 키 목록
            modifiers = self._get_modifiers()
            
            # 잠금 키 상태 (플랫폼에 따라 다름)
            caps_lock = False
            num_lock = False
            scroll_lock = False
            
            if PYAUTOGUI_AVAILABLE:
                try:
                    # pyautogui로 잠금 키 상태 확인 (일부 플랫폼에서만 지원)
                    if hasattr(pyautogui, 'isLocked'):
                        caps_lock = pyautogui.isLocked('capslock')
                        num_lock = pyautogui.isLocked('numlock')
                        scroll_lock = pyautogui.isLocked('scrolllock')
                except:
                    pass
            
            return KeyboardState(
                pressed_keys=pressed_keys,
                modifiers=modifiers,
                caps_lock=caps_lock,
                num_lock=num_lock,
                scroll_lock=scroll_lock
            )

    def press_key(self, key: str) -> bool:
        """
        키를 누릅니다.
        
        Args:
            key: 키 이름
            
        Returns:
            bool: 성공 여부
        """
        try:
            if not key:
                logger.error("키 이름이 지정되지 않았습니다.")
                return False
                
            if PYAUTOGUI_AVAILABLE:
                pyautogui.keyDown(key)
                logger.debug(f"키 누름: {key}")
                return True
            elif PYNPUT_AVAILABLE:
                controller = keyboard.Controller()
                # 특수 키 처리
                if hasattr(keyboard.Key, key):
                    special_key = getattr(keyboard.Key, key)
                    controller.press(special_key)
                else:
                    controller.press(key)
                logger.debug(f"키 누름: {key}")
                return True
            else:
                logger.error("키보드 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"키 누름 중 오류 발생: {e}")
            return False

    def release_key(self, key: str) -> bool:
        """
        키를 뗍니다.
        
        Args:
            key: 키 이름
            
        Returns:
            bool: 성공 여부
        """
        try:
            if not key:
                logger.error("키 이름이 지정되지 않았습니다.")
                return False
                
            if PYAUTOGUI_AVAILABLE:
                pyautogui.keyUp(key)
                logger.debug(f"키 뗌: {key}")
                return True
            elif PYNPUT_AVAILABLE:
                controller = keyboard.Controller()
                # 특수 키 처리
                if hasattr(keyboard.Key, key):
                    special_key = getattr(keyboard.Key, key)
                    controller.release(special_key)
                else:
                    controller.release(key)
                logger.debug(f"키 뗌: {key}")
                return True
            else:
                logger.error("키보드 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"키 뗌 중 오류 발생: {e}")
            return False

    def tap_key(self, key: str, interval: float = 0.1) -> bool:
        """
        키를 누르고 뗍니다.
        
        Args:
            key: 키 이름
            interval: 누르고 떼는 사이의 간격 (초)
            
        Returns:
            bool: 성공 여부
        """
        try:
            if not key:
                logger.error("키 이름이 지정되지 않았습니다.")
                return False
                
            if PYAUTOGUI_AVAILABLE:
                pyautogui.press(key)
                logger.debug(f"키 탭: {key}")
                return True
            elif PYNPUT_AVAILABLE:
                controller = keyboard.Controller()
                # 특수 키 처리
                if hasattr(keyboard.Key, key):
                    special_key = getattr(keyboard.Key, key)
                    controller.press(special_key)
                    time.sleep(interval)
                    controller.release(special_key)
                else:
                    controller.press(key)
                    time.sleep(interval)
                    controller.release(key)
                logger.debug(f"키 탭: {key}")
                return True
            else:
                logger.error("키보드 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"키 탭 중 오류 발생: {e}")
            return False

    def type_text(self, text: str, interval: float = 0.0) -> bool:
        """
        텍스트를 입력합니다.
        
        Args:
            text: 입력할 텍스트
            interval: 각 문자 사이의 간격 (초)
            
        Returns:
            bool: 성공 여부
        """
        try:
            if not text:
                logger.error("입력할 텍스트가 지정되지 않았습니다.")
                return False
                
            if PYAUTOGUI_AVAILABLE:
                pyautogui.write(text, interval=interval)
                logger.debug(f"텍스트 입력: {text}")
                return True
            elif PYNPUT_AVAILABLE:
                controller = keyboard.Controller()
                for char in text:
                    controller.press(char)
                    controller.release(char)
                    if interval > 0:
                        time.sleep(interval)
                logger.debug(f"텍스트 입력: {text}")
                return True
            else:
                logger.error("키보드 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"텍스트 입력 중 오류 발생: {e}")
            return False

    def hotkey(self, *keys) -> bool:
        """
        여러 키를 동시에 누르고 뗍니다.
        
        Args:
            *keys: 키 이름들
            
        Returns:
            bool: 성공 여부
        """
        try:
            if not keys:
                logger.error("키가 지정되지 않았습니다.")
                return False
                
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey(*keys)
                logger.debug(f"핫키: {keys}")
                return True
            elif PYNPUT_AVAILABLE:
                controller = keyboard.Controller()
                # 키 누르기
                pressed_keys = []
                for key in keys:
                    # 특수 키 처리
                    if hasattr(keyboard.Key, key):
                        k = getattr(keyboard.Key, key)
                    else:
                        k = key
                    controller.press(k)
                    pressed_keys.append(k)
                
                # 키 떼기 (역순)
                for key in reversed(pressed_keys):
                    controller.release(key)
                
                logger.debug(f"핫키: {keys}")
                return True
            else:
                logger.error("키보드 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"핫키 실행 중 오류 발생: {e}")
            return False

    def start_recording(self) -> bool:
        """
        키보드 이벤트 녹화를 시작합니다.
        
        Returns:
            bool: 성공 여부
        """
        try:
            if self.recording:
                logger.warning("이미 키보드 이벤트 녹화 중입니다.")
                return False
                
            # 리스닝 시작
            if not self.is_listening:
                success = self.start_listening()
                if not success:
                    return False
            
            # 녹화 시작
            with self.lock:
                self.recorded_events = []
                self.recording = True
                
            logger.info("키보드 이벤트 녹화를 시작했습니다.")
            return True
        except Exception as e:
            logger.error(f"키보드 이벤트 녹화 시작 중 오류 발생: {e}")
            return False

    def stop_recording(self) -> List[KeyEvent]:
        """
        키보드 이벤트 녹화를 중지하고 녹화된 이벤트를 반환합니다.
        
        Returns:
            List[KeyEvent]: 녹화된 키보드 이벤트 목록
        """
        try:
            if not self.recording:
                logger.warning("키보드 이벤트 녹화 중이 아닙니다.")
                return []
                
            # 녹화 중지
            with self.lock:
                events = self.recorded_events.copy()
                self.recording = False
                
            logger.info(f"키보드 이벤트 녹화를 중지했습니다. {len(events)}개의 이벤트가 녹화되었습니다.")
            return events
        except Exception as e:
            logger.error(f"키보드 이벤트 녹화 중지 중 오류 발생: {e}")
            return []

    def play_recorded_events(self, events: List[KeyEvent], speed: float = 1.0) -> bool:
        """
        녹화된 키보드 이벤트를 재생합니다.
        
        Args:
            events: 재생할 키보드 이벤트 목록
            speed: 재생 속도 (1.0이 원래 속도)
            
        Returns:
            bool: 성공 여부
        """
        try:
            if not events:
                logger.warning("재생할 키보드 이벤트가 없습니다.")
                return False
                
            if not PYAUTOGUI_AVAILABLE and not PYNPUT_AVAILABLE:
                logger.error("키보드 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
                
            # 이벤트 재생
            prev_time = None
            for event in events:
                # 이벤트 시간 간격 계산
                if prev_time:
                    event_time = datetime.fromisoformat(event.timestamp)
                    time_diff = (event_time - prev_time).total_seconds() / speed
                    if time_diff > 0:
                        time.sleep(time_diff)
                
                # 이벤트 타입에 따라 처리
                if event.event_type == KeyEventType.PRESS:
                    self.press_key(event.key)
                elif event.event_type == KeyEventType.RELEASE:
                    self.release_key(event.key)
                elif event.event_type == KeyEventType.TAP:
                    self.tap_key(event.key)
                
                prev_time = datetime.fromisoformat(event.timestamp)
                
            logger.info(f"{len(events)}개의 키보드 이벤트를 재생했습니다.")
            return True
        except Exception as e:
            logger.error(f"키보드 이벤트 재생 중 오류 발생: {e}")
            return False


# 전역 서비스 인스턴스
keyboard_service = KeyboardEventService()


@app.tool()
def press_key(key: str) -> dict:
    """
    키를 누릅니다.
    
    Args:
        key: 키 이름 (예: 'a', 'enter', 'space', 'shift', 'ctrl', 'alt', 'cmd')
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> press_key("a")
        {'result': {'key': 'a', 'action': 'press', 'success': True}}
    """
    try:
        if not key:
            return {"error": "키 이름을 입력해주세요."}
            
        # 키 누르기
        success = keyboard_service.press_key(key)
        
        if not success:
            return {"error": f"키 '{key}' 누르기 실패"}
            
        return {
            "result": {
                "key": key,
                "action": "press",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"키 누르기 중 오류 발생: {str(e)}"}


@app.tool()
def release_key(key: str) -> dict:
    """
    키를 뗍니다.
    
    Args:
        key: 키 이름 (예: 'a', 'enter', 'space', 'shift', 'ctrl', 'alt', 'cmd')
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> release_key("a")
        {'result': {'key': 'a', 'action': 'release', 'success': True}}
    """
    try:
        if not key:
            return {"error": "키 이름을 입력해주세요."}
            
        # 키 떼기
        success = keyboard_service.release_key(key)
        
        if not success:
            return {"error": f"키 '{key}' 떼기 실패"}
            
        return {
            "result": {
                "key": key,
                "action": "release",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"키 떼기 중 오류 발생: {str(e)}"}


@app.tool()
def tap_key(key: str, interval: float = 0.1) -> dict:
    """
    키를 누르고 뗍니다.
    
    Args:
        key: 키 이름 (예: 'a', 'enter', 'space', 'shift', 'ctrl', 'alt', 'cmd')
        interval: 누르고 떼는 사이의 간격 (초)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> tap_key("enter")
        {'result': {'key': 'enter', 'action': 'tap', 'success': True}}
    """
    try:
        if not key:
            return {"error": "키 이름을 입력해주세요."}
            
        # 키 탭
        success = keyboard_service.tap_key(key, interval)
        
        if not success:
            return {"error": f"키 '{key}' 탭 실패"}
            
        return {
            "result": {
                "key": key,
                "action": "tap",
                "interval": interval,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"키 탭 중 오류 발생: {str(e)}"}


@app.tool()
def type_text(text: str, interval: float = 0.0) -> dict:
    """
    텍스트를 입력합니다.
    
    Args:
        text: 입력할 텍스트
        interval: 각 문자 사이의 간격 (초)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> type_text("Hello, World!")
        {'result': {'text': 'Hello, World!', 'action': 'type', 'success': True}}
    """
    try:
        if not text:
            return {"error": "입력할 텍스트를 입력해주세요."}
            
        # 텍스트 입력
        success = keyboard_service.type_text(text, interval)
        
        if not success:
            return {"error": "텍스트 입력 실패"}
            
        return {
            "result": {
                "text": text,
                "action": "type",
                "interval": interval,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"텍스트 입력 중 오류 발생: {str(e)}"}


@app.tool()
def hotkey(*keys) -> dict:
    """
    여러 키를 동시에 누르고 뗍니다.
    
    Args:
        *keys: 키 이름들 (예: 'ctrl', 'c')
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> hotkey("ctrl", "c")
        {'result': {'keys': ['ctrl', 'c'], 'action': 'hotkey', 'success': True}}
    """
    try:
        if not keys:
            return {"error": "키를 하나 이상 입력해주세요."}
            
        # 핫키 실행
        success = keyboard_service.hotkey(*keys)
        
        if not success:
            return {"error": f"핫키 {keys} 실행 실패"}
            
        return {
            "result": {
                "keys": list(keys),
                "action": "hotkey",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"핫키 실행 중 오류 발생: {str(e)}"}


@app.tool()
def get_keyboard_state() -> dict:
    """
    현재 키보드 상태를 가져옵니다.
    
    Returns:
        dict: 키보드 상태를 포함한 딕셔너리
        
    Examples:
        >>> get_keyboard_state()
        {'result': {'pressed_keys': [...], 'modifiers': [...], ...}}
    """
    try:
        # 키보드 상태 가져오기
        state = keyboard_service.get_keyboard_state()
        
        return {
            "result": {
                "pressed_keys": state.pressed_keys,
                "modifiers": state.modifiers,
                "caps_lock": state.caps_lock,
                "num_lock": state.num_lock,
                "scroll_lock": state.scroll_lock,
                "timestamp": state.timestamp
            }
        }
        
    except Exception as e:
        return {"error": f"키보드 상태 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def start_recording() -> dict:
    """
    키보드 이벤트 녹화를 시작합니다.
    
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> start_recording()
        {'result': {'action': 'start_recording', 'success': True}}
    """
    try:
        # 녹화 시작
        success = keyboard_service.start_recording()
        
        if not success:
            return {"error": "키보드 이벤트 녹화 시작 실패"}
            
        return {
            "result": {
                "action": "start_recording",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"키보드 이벤트 녹화 시작 중 오류 발생: {str(e)}"}


@app.tool()
def stop_recording() -> dict:
    """
    키보드 이벤트 녹화를 중지하고 녹화된 이벤트를 반환합니다.
    
    Returns:
        dict: 녹화된 이벤트를 포함한 딕셔너리
        
    Examples:
        >>> stop_recording()
        {'result': {'action': 'stop_recording', 'events': [...], 'count': 10}}
    """
    try:
        # 녹화 중지
        events = keyboard_service.stop_recording()
        
        # 이벤트 포맷팅
        formatted_events = []
        for event in events:
            formatted_events.append({
                "key": event.key,
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "modifiers": event.modifiers,
                "character": event.character
            })
            
        return {
            "result": {
                "action": "stop_recording",
                "events": formatted_events,
                "count": len(formatted_events),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"키보드 이벤트 녹화 중지 중 오류 발생: {str(e)}"}


@app.tool()
def play_recorded_events(events: List[Dict], speed: float = 1.0) -> dict:
    """
    녹화된 키보드 이벤트를 재생합니다.
    
    Args:
        events: 재생할 키보드 이벤트 목록
        speed: 재생 속도 (1.0이 원래 속도)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> play_recorded_events([{"key": "a", "event_type": "press", ...}, ...])
        {'result': {'action': 'play_recorded_events', 'count': 10, 'success': True}}
    """
    try:
        if not events:
            return {"error": "재생할 키보드 이벤트가 없습니다."}
            
        # 이벤트 변환
        key_events = []
        for event_dict in events:
            event = KeyEvent(
                key=event_dict.get("key", ""),
                event_type=event_dict.get("event_type", KeyEventType.TAP),
                timestamp=event_dict.get("timestamp", datetime.now().isoformat()),
                modifiers=event_dict.get("modifiers", []),
                character=event_dict.get("character", "")
            )
            key_events.append(event)
            
        # 이벤트 재생
        success = keyboard_service.play_recorded_events(key_events, speed)
        
        if not success:
            return {"error": "키보드 이벤트 재생 실패"}
            
        return {
            "result": {
                "action": "play_recorded_events",
                "count": len(key_events),
                "speed": speed,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"키보드 이벤트 재생 중 오류 발생: {str(e)}"}


@app.tool()
def get_tool_info() -> dict:
    """
    키보드 이벤트 도구 정보를 반환합니다.
    
    Returns:
        dict: 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "Keyboard Event Tool",
                "description": "키보드 이벤트를 처리하고 제어하는 도구",
                "platform": keyboard_service.platform_name,
                "libraries": {
                    "pynput": PYNPUT_AVAILABLE,
                    "pyautogui": PYAUTOGUI_AVAILABLE
                },
                "tools": [
                    {"name": "press_key", "description": "키를 누릅니다"},
                    {"name": "release_key", "description": "키를 뗍니다"},
                    {"name": "tap_key", "description": "키를 누르고 뗍니다"},
                    {"name": "type_text", "description": "텍스트를 입력합니다"},
                    {"name": "hotkey", "description": "여러 키를 동시에 누르고 뗍니다"},
                    {"name": "get_keyboard_state", "description": "현재 키보드 상태를 가져옵니다"},
                    {"name": "start_recording", "description": "키보드 이벤트 녹화를 시작합니다"},
                    {"name": "stop_recording", "description": "키보드 이벤트 녹화를 중지하고 녹화된 이벤트를 반환합니다"},
                    {"name": "play_recorded_events", "description": "녹화된 키보드 이벤트를 재생합니다"}
                ],
                "usage_examples": [
                    {"command": "press_key('a')", "description": "a 키 누르기"},
                    {"command": "release_key('a')", "description": "a 키 떼기"},
                    {"command": "tap_key('enter')", "description": "Enter 키 누르고 떼기"},
                    {"command": "type_text('Hello, World!')", "description": "텍스트 입력하기"},
                    {"command": "hotkey('ctrl', 'c')", "description": "Ctrl+C 단축키 실행하기"},
                    {"command": "get_keyboard_state()", "description": "현재 키보드 상태 가져오기"}
                ],
                "common_keys": {
                    "letters": "a-z",
                    "numbers": "0-9",
                    "special": ["space", "enter", "tab", "backspace", "esc", "delete"],
                    "modifiers": ["shift", "ctrl", "alt", "cmd"],
                    "function": ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"],
                    "navigation": ["up", "down", "left", "right", "home", "end", "pageup", "pagedown"],
                    "locks": ["capslock", "numlock", "scrolllock"]
                }
            }
        }
        
    except Exception as e:
        return {"error": f"도구 정보를 가져오는 중 오류 발생: {str(e)}"}


if __name__ == "__main__":
    try:
        logger.info("FastMCP app.run() 호출 시작...")
        app.run(transport=TRANSPORT)
        logger.info("FastMCP app.run() 정상 종료.")
    except Exception as e:
        logger.error("keyboard_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise