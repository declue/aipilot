#!/usr/bin/env python3
"""
Mouse Event MCP Server
마우스 이벤트를 처리하고 제어하는 도구를 제공합니다.
Windows와 macOS 모두에서 동작하는 크로스 플랫폼 마우스 이벤트 처리 기능을 제공합니다.
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
from typing import Dict, List, Optional, Any, Union, Callable, Tuple

try:
    from pynput import mouse
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
# 프로젝트 루트에 mouse_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "mouse_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("MOUSE_TOOL_LOG_LEVEL", "WARNING").upper()
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
    logger.info("Mouse Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
    logger.info("운영체제: %s", sys.platform)
    logger.info("pynput 사용 가능: %s", PYNPUT_AVAILABLE)
    logger.info("pyautogui 사용 가능: %s", PYAUTOGUI_AVAILABLE)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="Mouse Event Server",
    description="A server for mouse event operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 마우스 이벤트 타입 정의
class MouseEventType(str, Enum):
    """마우스 이벤트 타입"""
    MOVE = "move"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    SCROLL = "scroll"
    PRESS = "press"
    RELEASE = "release"
    DRAG = "drag"


# 마우스 버튼 정의
class MouseButton(str, Enum):
    """마우스 버튼"""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


@dataclass
class MouseEvent:
    """마우스 이벤트를 담는 데이터 클래스"""
    event_type: MouseEventType
    x: int
    y: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    button: MouseButton = None
    pressed: bool = False
    dx: int = 0  # 스크롤 또는 드래그 시 x 변화량
    dy: int = 0  # 스크롤 또는 드래그 시 y 변화량


@dataclass
class MouseState:
    """마우스 상태를 담는 데이터 클래스"""
    x: int
    y: int
    left_pressed: bool = False
    right_pressed: bool = False
    middle_pressed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MouseEventService:
    """마우스 이벤트 서비스 클래스"""

    def __init__(self):
        """마우스 이벤트 서비스 초기화"""
        self.listener = None
        self.is_listening = False
        self.stop_event = Event()
        self.callback = None
        self.lock = Lock()
        self.recorded_events = []
        self.recording = False
        self.left_pressed = False
        self.right_pressed = False
        self.middle_pressed = False
        self.last_position = (0, 0)
        
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
            logger.warning("마우스 이벤트 처리를 위한 라이브러리가 설치되지 않았습니다.")
        
        # 현재 마우스 위치 초기화
        if self.use_pyautogui:
            try:
                self.last_position = pyautogui.position()
            except:
                pass

    def start_listening(self, callback: Callable = None) -> bool:
        """
        마우스 이벤트 리스닝을 시작합니다.
        
        Args:
            callback: 이벤트 발생 시 호출할 콜백 함수 (선택 사항)
            
        Returns:
            bool: 성공 여부
        """
        if self.is_listening:
            logger.warning("이미 마우스 이벤트 리스닝 중입니다.")
            return False
            
        if not self.use_pynput:
            logger.error("pynput 라이브러리가 설치되지 않아 마우스 이벤트 리스닝을 시작할 수 없습니다.")
            return False
            
        self.callback = callback
        self.stop_event.clear()
        self.is_listening = True
        
        try:
            # 마우스 리스너 시작
            self.listener = mouse.Listener(
                on_move=self._on_move,
                on_click=self._on_click,
                on_scroll=self._on_scroll
            )
            self.listener.start()
            logger.info("마우스 이벤트 리스닝을 시작했습니다.")
            return True
        except Exception as e:
            logger.error(f"마우스 이벤트 리스닝 시작 중 오류 발생: {e}")
            self.is_listening = False
            return False

    def stop_listening(self) -> bool:
        """
        마우스 이벤트 리스닝을 중지합니다.
        
        Returns:
            bool: 성공 여부
        """
        if not self.is_listening:
            logger.warning("마우스 이벤트 리스닝 중이 아닙니다.")
            return False
            
        try:
            self.stop_event.set()
            if self.listener:
                self.listener.stop()
                self.listener = None
            self.is_listening = False
            logger.info("마우스 이벤트 리스닝을 중지했습니다.")
            return True
        except Exception as e:
            logger.error(f"마우스 이벤트 리스닝 중지 중 오류 발생: {e}")
            return False

    def _on_move(self, x, y):
        """
        마우스 이동 이벤트 핸들러
        
        Args:
            x: x 좌표
            y: y 좌표
        """
        try:
            with self.lock:
                # 이전 위치와 현재 위치의 차이 계산
                dx = x - self.last_position[0]
                dy = y - self.last_position[1]
                self.last_position = (x, y)
                
                # 이벤트 생성
                event = MouseEvent(
                    event_type=MouseEventType.MOVE,
                    x=x,
                    y=y,
                    dx=dx,
                    dy=dy
                )
                
                # 이벤트 기록 (녹화 중인 경우)
                if self.recording:
                    self.recorded_events.append(event)
                
                # 콜백 호출
                if self.callback:
                    self.callback(event)
                    
                logger.debug(f"마우스 이동: ({x}, {y}), 변화량: ({dx}, {dy})")
                
                # 리스닝 중지 확인
                if self.stop_event.is_set():
                    return False
        except Exception as e:
            logger.error(f"마우스 이동 이벤트 처리 중 오류 발생: {e}")

    def _on_click(self, x, y, button, pressed):
        """
        마우스 클릭 이벤트 핸들러
        
        Args:
            x: x 좌표
            y: y 좌표
            button: 버튼 (pynput.mouse.Button)
            pressed: 눌림 여부
        """
        try:
            with self.lock:
                # 버튼 변환
                button_str = self._convert_button(button)
                
                # 버튼 상태 업데이트
                if button_str == MouseButton.LEFT:
                    self.left_pressed = pressed
                elif button_str == MouseButton.RIGHT:
                    self.right_pressed = pressed
                elif button_str == MouseButton.MIDDLE:
                    self.middle_pressed = pressed
                
                # 이벤트 타입 결정
                event_type = MouseEventType.PRESS if pressed else MouseEventType.RELEASE
                
                # 이벤트 생성
                event = MouseEvent(
                    event_type=event_type,
                    x=x,
                    y=y,
                    button=button_str,
                    pressed=pressed
                )
                
                # 이벤트 기록 (녹화 중인 경우)
                if self.recording:
                    self.recorded_events.append(event)
                
                # 콜백 호출
                if self.callback:
                    self.callback(event)
                    
                logger.debug(f"마우스 {'눌림' if pressed else '뗌'}: {button_str} ({x}, {y})")
                
                # 리스닝 중지 확인
                if self.stop_event.is_set():
                    return False
        except Exception as e:
            logger.error(f"마우스 클릭 이벤트 처리 중 오류 발생: {e}")

    def _on_scroll(self, x, y, dx, dy):
        """
        마우스 스크롤 이벤트 핸들러
        
        Args:
            x: x 좌표
            y: y 좌표
            dx: 가로 스크롤 양
            dy: 세로 스크롤 양
        """
        try:
            with self.lock:
                # 이벤트 생성
                event = MouseEvent(
                    event_type=MouseEventType.SCROLL,
                    x=x,
                    y=y,
                    dx=dx,
                    dy=dy
                )
                
                # 이벤트 기록 (녹화 중인 경우)
                if self.recording:
                    self.recorded_events.append(event)
                
                # 콜백 호출
                if self.callback:
                    self.callback(event)
                    
                logger.debug(f"마우스 스크롤: ({x}, {y}), 변화량: ({dx}, {dy})")
                
                # 리스닝 중지 확인
                if self.stop_event.is_set():
                    return False
        except Exception as e:
            logger.error(f"마우스 스크롤 이벤트 처리 중 오류 발생: {e}")

    def _convert_button(self, button) -> MouseButton:
        """
        pynput 버튼을 MouseButton으로 변환합니다.
        
        Args:
            button: pynput.mouse.Button
            
        Returns:
            MouseButton: 변환된 버튼
        """
        try:
            if hasattr(button, 'name'):
                button_name = button.name.lower()
                if 'left' in button_name:
                    return MouseButton.LEFT
                elif 'right' in button_name:
                    return MouseButton.RIGHT
                elif 'middle' in button_name:
                    return MouseButton.MIDDLE
            return MouseButton.LEFT  # 기본값
        except Exception as e:
            logger.error(f"버튼 변환 중 오류 발생: {e}")
            return MouseButton.LEFT

    def get_mouse_position(self) -> Tuple[int, int]:
        """
        현재 마우스 위치를 가져옵니다.
        
        Returns:
            Tuple[int, int]: (x, y) 좌표
        """
        try:
            if self.use_pyautogui:
                return pyautogui.position()
            elif self.use_pynput:
                controller = mouse.Controller()
                return controller.position
            else:
                logger.error("마우스 위치를 가져오기 위한 라이브러리가 설치되지 않았습니다.")
                return (0, 0)
        except Exception as e:
            logger.error(f"마우스 위치 가져오기 중 오류 발생: {e}")
            return (0, 0)

    def get_mouse_state(self) -> MouseState:
        """
        현재 마우스 상태를 가져옵니다.
        
        Returns:
            MouseState: 마우스 상태 객체
        """
        with self.lock:
            # 현재 마우스 위치
            x, y = self.get_mouse_position()
            
            return MouseState(
                x=x,
                y=y,
                left_pressed=self.left_pressed,
                right_pressed=self.right_pressed,
                middle_pressed=self.middle_pressed
            )

    def move_mouse(self, x: int, y: int, duration: float = 0.0) -> bool:
        """
        마우스를 지정된 위치로 이동합니다.
        
        Args:
            x: 목표 x 좌표
            y: 목표 y 좌표
            duration: 이동 시간 (초)
            
        Returns:
            bool: 성공 여부
        """
        try:
            if self.use_pyautogui:
                pyautogui.moveTo(x, y, duration=duration)
                logger.debug(f"마우스 이동: ({x}, {y}), 시간: {duration}초")
                return True
            elif self.use_pynput:
                controller = mouse.Controller()
                if duration > 0:
                    # 부드러운 이동 구현
                    start_x, start_y = controller.position
                    steps = max(int(duration * 100), 1)
                    for i in range(1, steps + 1):
                        progress = i / steps
                        current_x = start_x + (x - start_x) * progress
                        current_y = start_y + (y - start_y) * progress
                        controller.position = (current_x, current_y)
                        time.sleep(duration / steps)
                else:
                    controller.position = (x, y)
                logger.debug(f"마우스 이동: ({x}, {y}), 시간: {duration}초")
                return True
            else:
                logger.error("마우스 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"마우스 이동 중 오류 발생: {e}")
            return False

    def move_mouse_relative(self, dx: int, dy: int, duration: float = 0.0) -> bool:
        """
        마우스를 현재 위치에서 상대적으로 이동합니다.
        
        Args:
            dx: x 변화량
            dy: y 변화량
            duration: 이동 시간 (초)
            
        Returns:
            bool: 성공 여부
        """
        try:
            if self.use_pyautogui:
                pyautogui.moveRel(dx, dy, duration=duration)
                logger.debug(f"마우스 상대 이동: ({dx}, {dy}), 시간: {duration}초")
                return True
            elif self.use_pynput:
                controller = mouse.Controller()
                current_x, current_y = controller.position
                target_x = current_x + dx
                target_y = current_y + dy
                
                if duration > 0:
                    # 부드러운 이동 구현
                    steps = max(int(duration * 100), 1)
                    for i in range(1, steps + 1):
                        progress = i / steps
                        new_x = current_x + dx * progress
                        new_y = current_y + dy * progress
                        controller.position = (new_x, new_y)
                        time.sleep(duration / steps)
                else:
                    controller.position = (target_x, target_y)
                logger.debug(f"마우스 상대 이동: ({dx}, {dy}), 시간: {duration}초")
                return True
            else:
                logger.error("마우스 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"마우스 상대 이동 중 오류 발생: {e}")
            return False

    def click_mouse(self, x: int = None, y: int = None, button: MouseButton = MouseButton.LEFT, clicks: int = 1, interval: float = 0.0) -> bool:
        """
        마우스를 클릭합니다.
        
        Args:
            x: 클릭할 x 좌표 (None이면 현재 위치)
            y: 클릭할 y 좌표 (None이면 현재 위치)
            button: 클릭할 버튼
            clicks: 클릭 횟수
            interval: 클릭 사이의 간격 (초)
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 위치가 지정되지 않은 경우 현재 위치 사용
            if x is None or y is None:
                current_x, current_y = self.get_mouse_position()
                x = x if x is not None else current_x
                y = y if y is not None else current_y
            
            if self.use_pyautogui:
                # 버튼 변환
                button_str = button.value if isinstance(button, MouseButton) else button
                
                # 클릭 수행
                if clicks == 1:
                    pyautogui.click(x, y, button=button_str)
                elif clicks == 2:
                    pyautogui.doubleClick(x, y, button=button_str)
                else:
                    for _ in range(clicks):
                        pyautogui.click(x, y, button=button_str)
                        if interval > 0 and _ < clicks - 1:
                            time.sleep(interval)
                
                logger.debug(f"마우스 클릭: ({x}, {y}), 버튼: {button_str}, 횟수: {clicks}")
                return True
            elif self.use_pynput:
                controller = mouse.Controller()
                
                # 위치 이동
                original_position = controller.position
                controller.position = (x, y)
                
                # 버튼 변환
                pynput_button = self._get_pynput_button(button)
                
                # 클릭 수행
                for _ in range(clicks):
                    controller.press(pynput_button)
                    controller.release(pynput_button)
                    if interval > 0 and _ < clicks - 1:
                        time.sleep(interval)
                
                logger.debug(f"마우스 클릭: ({x}, {y}), 버튼: {button}, 횟수: {clicks}")
                return True
            else:
                logger.error("마우스 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"마우스 클릭 중 오류 발생: {e}")
            return False

    def press_mouse_button(self, button: MouseButton = MouseButton.LEFT, x: int = None, y: int = None) -> bool:
        """
        마우스 버튼을 누릅니다.
        
        Args:
            button: 누를 버튼
            x: 버튼을 누를 x 좌표 (None이면 현재 위치)
            y: 버튼을 누를 y 좌표 (None이면 현재 위치)
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 위치가 지정되지 않은 경우 현재 위치 사용
            if x is not None and y is not None:
                self.move_mouse(x, y)
            
            if self.use_pyautogui:
                # 버튼 변환
                button_str = button.value if isinstance(button, MouseButton) else button
                
                # 버튼 누르기
                pyautogui.mouseDown(button=button_str)
                
                # 버튼 상태 업데이트
                if button_str == MouseButton.LEFT.value:
                    self.left_pressed = True
                elif button_str == MouseButton.RIGHT.value:
                    self.right_pressed = True
                elif button_str == MouseButton.MIDDLE.value:
                    self.middle_pressed = True
                
                logger.debug(f"마우스 버튼 누름: {button_str}")
                return True
            elif self.use_pynput:
                controller = mouse.Controller()
                
                # 버튼 변환
                pynput_button = self._get_pynput_button(button)
                
                # 버튼 누르기
                controller.press(pynput_button)
                
                # 버튼 상태 업데이트
                if button == MouseButton.LEFT:
                    self.left_pressed = True
                elif button == MouseButton.RIGHT:
                    self.right_pressed = True
                elif button == MouseButton.MIDDLE:
                    self.middle_pressed = True
                
                logger.debug(f"마우스 버튼 누름: {button}")
                return True
            else:
                logger.error("마우스 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"마우스 버튼 누름 중 오류 발생: {e}")
            return False

    def release_mouse_button(self, button: MouseButton = MouseButton.LEFT, x: int = None, y: int = None) -> bool:
        """
        마우스 버튼을 뗍니다.
        
        Args:
            button: 뗄 버튼
            x: 버튼을 뗄 x 좌표 (None이면 현재 위치)
            y: 버튼을 뗄 y 좌표 (None이면 현재 위치)
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 위치가 지정되지 않은 경우 현재 위치 사용
            if x is not None and y is not None:
                self.move_mouse(x, y)
            
            if self.use_pyautogui:
                # 버튼 변환
                button_str = button.value if isinstance(button, MouseButton) else button
                
                # 버튼 떼기
                pyautogui.mouseUp(button=button_str)
                
                # 버튼 상태 업데이트
                if button_str == MouseButton.LEFT.value:
                    self.left_pressed = False
                elif button_str == MouseButton.RIGHT.value:
                    self.right_pressed = False
                elif button_str == MouseButton.MIDDLE.value:
                    self.middle_pressed = False
                
                logger.debug(f"마우스 버튼 뗌: {button_str}")
                return True
            elif self.use_pynput:
                controller = mouse.Controller()
                
                # 버튼 변환
                pynput_button = self._get_pynput_button(button)
                
                # 버튼 떼기
                controller.release(pynput_button)
                
                # 버튼 상태 업데이트
                if button == MouseButton.LEFT:
                    self.left_pressed = False
                elif button == MouseButton.RIGHT:
                    self.right_pressed = False
                elif button == MouseButton.MIDDLE:
                    self.middle_pressed = False
                
                logger.debug(f"마우스 버튼 뗌: {button}")
                return True
            else:
                logger.error("마우스 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"마우스 버튼 뗌 중 오류 발생: {e}")
            return False

    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int, button: MouseButton = MouseButton.LEFT, duration: float = 0.1) -> bool:
        """
        마우스를 드래그합니다.
        
        Args:
            start_x: 시작 x 좌표
            start_y: 시작 y 좌표
            end_x: 끝 x 좌표
            end_y: 끝 y 좌표
            button: 드래그할 버튼
            duration: 드래그 시간 (초)
            
        Returns:
            bool: 성공 여부
        """
        try:
            if self.use_pyautogui:
                # 버튼 변환
                button_str = button.value if isinstance(button, MouseButton) else button
                
                # 드래그 수행
                pyautogui.moveTo(start_x, start_y)
                pyautogui.dragTo(end_x, end_y, duration=duration, button=button_str)
                
                logger.debug(f"마우스 드래그: ({start_x}, {start_y}) -> ({end_x}, {end_y}), 버튼: {button_str}")
                return True
            elif self.use_pynput:
                controller = mouse.Controller()
                
                # 버튼 변환
                pynput_button = self._get_pynput_button(button)
                
                # 시작 위치로 이동
                controller.position = (start_x, start_y)
                
                # 버튼 누르기
                controller.press(pynput_button)
                
                # 부드러운 이동 구현
                steps = max(int(duration * 100), 1)
                for i in range(1, steps + 1):
                    progress = i / steps
                    current_x = start_x + (end_x - start_x) * progress
                    current_y = start_y + (end_y - start_y) * progress
                    controller.position = (current_x, current_y)
                    time.sleep(duration / steps)
                
                # 버튼 떼기
                controller.release(pynput_button)
                
                logger.debug(f"마우스 드래그: ({start_x}, {start_y}) -> ({end_x}, {end_y}), 버튼: {button}")
                return True
            else:
                logger.error("마우스 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"마우스 드래그 중 오류 발생: {e}")
            return False

    def scroll_mouse(self, clicks: int, x: int = None, y: int = None) -> bool:
        """
        마우스 휠을 스크롤합니다.
        
        Args:
            clicks: 스크롤 클릭 수 (양수: 위로, 음수: 아래로)
            x: 스크롤할 x 좌표 (None이면 현재 위치)
            y: 스크롤할 y 좌표 (None이면 현재 위치)
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 위치가 지정되지 않은 경우 현재 위치 사용
            if x is not None and y is not None:
                self.move_mouse(x, y)
            
            if self.use_pyautogui:
                pyautogui.scroll(clicks)
                logger.debug(f"마우스 스크롤: {clicks} 클릭")
                return True
            elif self.use_pynput:
                controller = mouse.Controller()
                
                # pynput에서는 스크롤 방향이 반대
                controller.scroll(0, clicks)
                
                logger.debug(f"마우스 스크롤: {clicks} 클릭")
                return True
            else:
                logger.error("마우스 제어를 위한 라이브러리가 설치되지 않았습니다.")
                return False
        except Exception as e:
            logger.error(f"마우스 스크롤 중 오류 발생: {e}")
            return False

    def _get_pynput_button(self, button: MouseButton):
        """
        MouseButton을 pynput 버튼으로 변환합니다.
        
        Args:
            button: MouseButton
            
        Returns:
            pynput.mouse.Button: 변환된 버튼
        """
        if button == MouseButton.LEFT:
            return mouse.Button.left
        elif button == MouseButton.RIGHT:
            return mouse.Button.right
        elif button == MouseButton.MIDDLE:
            return mouse.Button.middle
        else:
            return mouse.Button.left

    def start_recording(self) -> bool:
        """
        마우스 이벤트 녹화를 시작합니다.
        
        Returns:
            bool: 성공 여부
        """
        try:
            if self.recording:
                logger.warning("이미 마우스 이벤트 녹화 중입니다.")
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
                
            logger.info("마우스 이벤트 녹화를 시작했습니다.")
            return True
        except Exception as e:
            logger.error(f"마우스 이벤트 녹화 시작 중 오류 발생: {e}")
            return False

    def stop_recording(self) -> List[MouseEvent]:
        """
        마우스 이벤트 녹화를 중지하고 녹화된 이벤트를 반환합니다.
        
        Returns:
            List[MouseEvent]: 녹화된 마우스 이벤트 목록
        """
        try:
            if not self.recording:
                logger.warning("마우스 이벤트 녹화 중이 아닙니다.")
                return []
                
            # 녹화 중지
            with self.lock:
                events = self.recorded_events.copy()
                self.recording = False
                
            logger.info(f"마우스 이벤트 녹화를 중지했습니다. {len(events)}개의 이벤트가 녹화되었습니다.")
            return events
        except Exception as e:
            logger.error(f"마우스 이벤트 녹화 중지 중 오류 발생: {e}")
            return []

    def play_recorded_events(self, events: List[MouseEvent], speed: float = 1.0) -> bool:
        """
        녹화된 마우스 이벤트를 재생합니다.
        
        Args:
            events: 재생할 마우스 이벤트 목록
            speed: 재생 속도 (1.0이 원래 속도)
            
        Returns:
            bool: 성공 여부
        """
        try:
            if not events:
                logger.warning("재생할 마우스 이벤트가 없습니다.")
                return False
                
            if not self.use_pyautogui and not self.use_pynput:
                logger.error("마우스 제어를 위한 라이브러리가 설치되지 않았습니다.")
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
                if event.event_type == MouseEventType.MOVE:
                    self.move_mouse(event.x, event.y)
                elif event.event_type == MouseEventType.CLICK:
                    self.click_mouse(event.x, event.y, event.button)
                elif event.event_type == MouseEventType.DOUBLE_CLICK:
                    self.click_mouse(event.x, event.y, event.button, clicks=2)
                elif event.event_type == MouseEventType.SCROLL:
                    self.scroll_mouse(event.dy, event.x, event.y)
                elif event.event_type == MouseEventType.PRESS:
                    self.press_mouse_button(event.button, event.x, event.y)
                elif event.event_type == MouseEventType.RELEASE:
                    self.release_mouse_button(event.button, event.x, event.y)
                elif event.event_type == MouseEventType.DRAG:
                    current_x, current_y = self.get_mouse_position()
                    self.drag_mouse(current_x, current_y, event.x, event.y, event.button)
                
                prev_time = datetime.fromisoformat(event.timestamp)
                
            logger.info(f"{len(events)}개의 마우스 이벤트를 재생했습니다.")
            return True
        except Exception as e:
            logger.error(f"마우스 이벤트 재생 중 오류 발생: {e}")
            return False


# 전역 서비스 인스턴스
mouse_service = MouseEventService()


@app.tool()
def get_mouse_position() -> dict:
    """
    현재 마우스 위치를 가져옵니다.
    
    Returns:
        dict: 마우스 위치를 포함한 딕셔너리
        
    Examples:
        >>> get_mouse_position()
        {'result': {'x': 100, 'y': 200}}
    """
    try:
        # 마우스 위치 가져오기
        x, y = mouse_service.get_mouse_position()
        
        return {
            "result": {
                "x": x,
                "y": y,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 위치 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_mouse_state() -> dict:
    """
    현재 마우스 상태를 가져옵니다.
    
    Returns:
        dict: 마우스 상태를 포함한 딕셔너리
        
    Examples:
        >>> get_mouse_state()
        {'result': {'x': 100, 'y': 200, 'left_pressed': False, 'right_pressed': False, 'middle_pressed': False}}
    """
    try:
        # 마우스 상태 가져오기
        state = mouse_service.get_mouse_state()
        
        return {
            "result": {
                "x": state.x,
                "y": state.y,
                "left_pressed": state.left_pressed,
                "right_pressed": state.right_pressed,
                "middle_pressed": state.middle_pressed,
                "timestamp": state.timestamp
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 상태 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def move_mouse(x: int, y: int, duration: float = 0.0) -> dict:
    """
    마우스를 지정된 위치로 이동합니다.
    
    Args:
        x: 목표 x 좌표
        y: 목표 y 좌표
        duration: 이동 시간 (초)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> move_mouse(100, 200)
        {'result': {'x': 100, 'y': 200, 'action': 'move', 'success': True}}
    """
    try:
        # 마우스 이동
        success = mouse_service.move_mouse(x, y, duration)
        
        if not success:
            return {"error": f"마우스 이동 실패: ({x}, {y})"}
            
        return {
            "result": {
                "x": x,
                "y": y,
                "duration": duration,
                "action": "move",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 이동 중 오류 발생: {str(e)}"}


@app.tool()
def move_mouse_relative(dx: int, dy: int, duration: float = 0.0) -> dict:
    """
    마우스를 현재 위치에서 상대적으로 이동합니다.
    
    Args:
        dx: x 변화량
        dy: y 변화량
        duration: 이동 시간 (초)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> move_mouse_relative(50, -20)
        {'result': {'dx': 50, 'dy': -20, 'action': 'move_relative', 'success': True}}
    """
    try:
        # 현재 위치 가져오기
        current_x, current_y = mouse_service.get_mouse_position()
        
        # 마우스 상대 이동
        success = mouse_service.move_mouse_relative(dx, dy, duration)
        
        if not success:
            return {"error": f"마우스 상대 이동 실패: ({dx}, {dy})"}
            
        # 새 위치 가져오기
        new_x, new_y = mouse_service.get_mouse_position()
            
        return {
            "result": {
                "from_x": current_x,
                "from_y": current_y,
                "to_x": new_x,
                "to_y": new_y,
                "dx": dx,
                "dy": dy,
                "duration": duration,
                "action": "move_relative",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 상대 이동 중 오류 발생: {str(e)}"}


@app.tool()
def click_mouse(x: int = None, y: int = None, button: str = "left", clicks: int = 1, interval: float = 0.0) -> dict:
    """
    마우스를 클릭합니다.
    
    Args:
        x: 클릭할 x 좌표 (None이면 현재 위치)
        y: 클릭할 y 좌표 (None이면 현재 위치)
        button: 클릭할 버튼 ("left", "right", "middle")
        clicks: 클릭 횟수
        interval: 클릭 사이의 간격 (초)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> click_mouse(100, 200)
        {'result': {'x': 100, 'y': 200, 'button': 'left', 'clicks': 1, 'action': 'click', 'success': True}}
    """
    try:
        # 버튼 변환
        try:
            mouse_button = MouseButton(button)
        except ValueError:
            return {"error": f"유효하지 않은 버튼: {button}. 'left', 'right', 'middle' 중 하나여야 합니다."}
        
        # 위치가 지정되지 않은 경우 현재 위치 사용
        if x is None or y is None:
            current_x, current_y = mouse_service.get_mouse_position()
            x = x if x is not None else current_x
            y = y if y is not None else current_y
        
        # 마우스 클릭
        success = mouse_service.click_mouse(x, y, mouse_button, clicks, interval)
        
        if not success:
            return {"error": f"마우스 클릭 실패: ({x}, {y}), 버튼: {button}, 횟수: {clicks}"}
            
        return {
            "result": {
                "x": x,
                "y": y,
                "button": button,
                "clicks": clicks,
                "interval": interval,
                "action": "click",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 클릭 중 오류 발생: {str(e)}"}


@app.tool()
def double_click_mouse(x: int = None, y: int = None, button: str = "left") -> dict:
    """
    마우스를 더블 클릭합니다.
    
    Args:
        x: 더블 클릭할 x 좌표 (None이면 현재 위치)
        y: 더블 클릭할 y 좌표 (None이면 현재 위치)
        button: 더블 클릭할 버튼 ("left", "right", "middle")
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> double_click_mouse(100, 200)
        {'result': {'x': 100, 'y': 200, 'button': 'left', 'action': 'double_click', 'success': True}}
    """
    try:
        # 버튼 변환
        try:
            mouse_button = MouseButton(button)
        except ValueError:
            return {"error": f"유효하지 않은 버튼: {button}. 'left', 'right', 'middle' 중 하나여야 합니다."}
        
        # 위치가 지정되지 않은 경우 현재 위치 사용
        if x is None or y is None:
            current_x, current_y = mouse_service.get_mouse_position()
            x = x if x is not None else current_x
            y = y if y is not None else current_y
        
        # 마우스 더블 클릭 (click_mouse 함수 재사용)
        success = mouse_service.click_mouse(x, y, mouse_button, clicks=2)
        
        if not success:
            return {"error": f"마우스 더블 클릭 실패: ({x}, {y}), 버튼: {button}"}
            
        return {
            "result": {
                "x": x,
                "y": y,
                "button": button,
                "action": "double_click",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 더블 클릭 중 오류 발생: {str(e)}"}


@app.tool()
def press_mouse_button(button: str = "left", x: int = None, y: int = None) -> dict:
    """
    마우스 버튼을 누릅니다.
    
    Args:
        button: 누를 버튼 ("left", "right", "middle")
        x: 버튼을 누를 x 좌표 (None이면 현재 위치)
        y: 버튼을 누를 y 좌표 (None이면 현재 위치)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> press_mouse_button("left")
        {'result': {'button': 'left', 'action': 'press', 'success': True}}
    """
    try:
        # 버튼 변환
        try:
            mouse_button = MouseButton(button)
        except ValueError:
            return {"error": f"유효하지 않은 버튼: {button}. 'left', 'right', 'middle' 중 하나여야 합니다."}
        
        # 마우스 버튼 누르기
        success = mouse_service.press_mouse_button(mouse_button, x, y)
        
        if not success:
            return {"error": f"마우스 버튼 누름 실패: {button}"}
            
        # 현재 위치 가져오기
        current_x, current_y = mouse_service.get_mouse_position()
            
        return {
            "result": {
                "x": current_x,
                "y": current_y,
                "button": button,
                "action": "press",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 버튼 누름 중 오류 발생: {str(e)}"}


@app.tool()
def release_mouse_button(button: str = "left", x: int = None, y: int = None) -> dict:
    """
    마우스 버튼을 뗍니다.
    
    Args:
        button: 뗄 버튼 ("left", "right", "middle")
        x: 버튼을 뗄 x 좌표 (None이면 현재 위치)
        y: 버튼을 뗄 y 좌표 (None이면 현재 위치)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> release_mouse_button("left")
        {'result': {'button': 'left', 'action': 'release', 'success': True}}
    """
    try:
        # 버튼 변환
        try:
            mouse_button = MouseButton(button)
        except ValueError:
            return {"error": f"유효하지 않은 버튼: {button}. 'left', 'right', 'middle' 중 하나여야 합니다."}
        
        # 마우스 버튼 떼기
        success = mouse_service.release_mouse_button(mouse_button, x, y)
        
        if not success:
            return {"error": f"마우스 버튼 뗌 실패: {button}"}
            
        # 현재 위치 가져오기
        current_x, current_y = mouse_service.get_mouse_position()
            
        return {
            "result": {
                "x": current_x,
                "y": current_y,
                "button": button,
                "action": "release",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 버튼 뗌 중 오류 발생: {str(e)}"}


@app.tool()
def drag_mouse(start_x: int, start_y: int, end_x: int, end_y: int, button: str = "left", duration: float = 0.1) -> dict:
    """
    마우스를 드래그합니다.
    
    Args:
        start_x: 시작 x 좌표
        start_y: 시작 y 좌표
        end_x: 끝 x 좌표
        end_y: 끝 y 좌표
        button: 드래그할 버튼 ("left", "right", "middle")
        duration: 드래그 시간 (초)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> drag_mouse(100, 200, 300, 400)
        {'result': {'start_x': 100, 'start_y': 200, 'end_x': 300, 'end_y': 400, 'button': 'left', 'action': 'drag', 'success': True}}
    """
    try:
        # 버튼 변환
        try:
            mouse_button = MouseButton(button)
        except ValueError:
            return {"error": f"유효하지 않은 버튼: {button}. 'left', 'right', 'middle' 중 하나여야 합니다."}
        
        # 마우스 드래그
        success = mouse_service.drag_mouse(start_x, start_y, end_x, end_y, mouse_button, duration)
        
        if not success:
            return {"error": f"마우스 드래그 실패: ({start_x}, {start_y}) -> ({end_x}, {end_y})"}
            
        return {
            "result": {
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "button": button,
                "duration": duration,
                "action": "drag",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 드래그 중 오류 발생: {str(e)}"}


@app.tool()
def scroll_mouse(clicks: int, x: int = None, y: int = None) -> dict:
    """
    마우스 휠을 스크롤합니다.
    
    Args:
        clicks: 스크롤 클릭 수 (양수: 위로, 음수: 아래로)
        x: 스크롤할 x 좌표 (None이면 현재 위치)
        y: 스크롤할 y 좌표 (None이면 현재 위치)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> scroll_mouse(10)
        {'result': {'clicks': 10, 'action': 'scroll', 'success': True}}
    """
    try:
        # 마우스 스크롤
        success = mouse_service.scroll_mouse(clicks, x, y)
        
        if not success:
            return {"error": f"마우스 스크롤 실패: {clicks} 클릭"}
            
        # 현재 위치 가져오기
        current_x, current_y = mouse_service.get_mouse_position()
            
        return {
            "result": {
                "x": current_x,
                "y": current_y,
                "clicks": clicks,
                "action": "scroll",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 스크롤 중 오류 발생: {str(e)}"}


@app.tool()
def start_recording() -> dict:
    """
    마우스 이벤트 녹화를 시작합니다.
    
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> start_recording()
        {'result': {'action': 'start_recording', 'success': True}}
    """
    try:
        # 녹화 시작
        success = mouse_service.start_recording()
        
        if not success:
            return {"error": "마우스 이벤트 녹화 시작 실패"}
            
        return {
            "result": {
                "action": "start_recording",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 이벤트 녹화 시작 중 오류 발생: {str(e)}"}


@app.tool()
def stop_recording() -> dict:
    """
    마우스 이벤트 녹화를 중지하고 녹화된 이벤트를 반환합니다.
    
    Returns:
        dict: 녹화된 이벤트를 포함한 딕셔너리
        
    Examples:
        >>> stop_recording()
        {'result': {'action': 'stop_recording', 'events': [...], 'count': 10}}
    """
    try:
        # 녹화 중지
        events = mouse_service.stop_recording()
        
        # 이벤트 포맷팅
        formatted_events = []
        for event in events:
            formatted_event = {
                "event_type": event.event_type,
                "x": event.x,
                "y": event.y,
                "timestamp": event.timestamp
            }
            
            # 이벤트 타입에 따라 추가 정보 포함
            if event.button:
                formatted_event["button"] = event.button
            if event.pressed is not None:
                formatted_event["pressed"] = event.pressed
            if event.dx != 0 or event.dy != 0:
                formatted_event["dx"] = event.dx
                formatted_event["dy"] = event.dy
                
            formatted_events.append(formatted_event)
            
        return {
            "result": {
                "action": "stop_recording",
                "events": formatted_events,
                "count": len(formatted_events),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 이벤트 녹화 중지 중 오류 발생: {str(e)}"}


@app.tool()
def play_recorded_events(events: List[Dict], speed: float = 1.0) -> dict:
    """
    녹화된 마우스 이벤트를 재생합니다.
    
    Args:
        events: 재생할 마우스 이벤트 목록
        speed: 재생 속도 (1.0이 원래 속도)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> play_recorded_events([{"event_type": "move", "x": 100, "y": 200, ...}, ...])
        {'result': {'action': 'play_recorded_events', 'count': 10, 'success': True}}
    """
    try:
        if not events:
            return {"error": "재생할 마우스 이벤트가 없습니다."}
            
        # 이벤트 변환
        mouse_events = []
        for event_dict in events:
            # 필수 필드 확인
            if "event_type" not in event_dict or "x" not in event_dict or "y" not in event_dict:
                continue
                
            # 이벤트 타입 변환
            try:
                event_type = MouseEventType(event_dict["event_type"])
            except ValueError:
                continue
                
            # 버튼 변환
            button = None
            if "button" in event_dict:
                try:
                    button = MouseButton(event_dict["button"])
                except ValueError:
                    pass
            
            # 이벤트 생성
            event = MouseEvent(
                event_type=event_type,
                x=event_dict["x"],
                y=event_dict["y"],
                timestamp=event_dict.get("timestamp", datetime.now().isoformat()),
                button=button,
                pressed=event_dict.get("pressed", False),
                dx=event_dict.get("dx", 0),
                dy=event_dict.get("dy", 0)
            )
            mouse_events.append(event)
            
        # 이벤트 재생
        success = mouse_service.play_recorded_events(mouse_events, speed)
        
        if not success:
            return {"error": "마우스 이벤트 재생 실패"}
            
        return {
            "result": {
                "action": "play_recorded_events",
                "count": len(mouse_events),
                "speed": speed,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"마우스 이벤트 재생 중 오류 발생: {str(e)}"}


@app.tool()
def get_screen_size() -> dict:
    """
    화면 크기를 가져옵니다.
    
    Returns:
        dict: 화면 크기를 포함한 딕셔너리
        
    Examples:
        >>> get_screen_size()
        {'result': {'width': 1920, 'height': 1080}}
    """
    try:
        if PYAUTOGUI_AVAILABLE:
            width, height = pyautogui.size()
            return {
                "result": {
                    "width": width,
                    "height": height
                }
            }
        else:
            return {"error": "화면 크기를 가져오기 위한 라이브러리가 설치되지 않았습니다."}
        
    except Exception as e:
        return {"error": f"화면 크기 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_tool_info() -> dict:
    """
    마우스 이벤트 도구 정보를 반환합니다.
    
    Returns:
        dict: 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "Mouse Event Tool",
                "description": "마우스 이벤트를 처리하고 제어하는 도구",
                "platform": mouse_service.platform_name,
                "libraries": {
                    "pynput": PYNPUT_AVAILABLE,
                    "pyautogui": PYAUTOGUI_AVAILABLE
                },
                "tools": [
                    {"name": "get_mouse_position", "description": "현재 마우스 위치를 가져옵니다"},
                    {"name": "get_mouse_state", "description": "현재 마우스 상태를 가져옵니다"},
                    {"name": "move_mouse", "description": "마우스를 지정된 위치로 이동합니다"},
                    {"name": "move_mouse_relative", "description": "마우스를 현재 위치에서 상대적으로 이동합니다"},
                    {"name": "click_mouse", "description": "마우스를 클릭합니다"},
                    {"name": "double_click_mouse", "description": "마우스를 더블 클릭합니다"},
                    {"name": "press_mouse_button", "description": "마우스 버튼을 누릅니다"},
                    {"name": "release_mouse_button", "description": "마우스 버튼을 뗍니다"},
                    {"name": "drag_mouse", "description": "마우스를 드래그합니다"},
                    {"name": "scroll_mouse", "description": "마우스 휠을 스크롤합니다"},
                    {"name": "start_recording", "description": "마우스 이벤트 녹화를 시작합니다"},
                    {"name": "stop_recording", "description": "마우스 이벤트 녹화를 중지하고 녹화된 이벤트를 반환합니다"},
                    {"name": "play_recorded_events", "description": "녹화된 마우스 이벤트를 재생합니다"},
                    {"name": "get_screen_size", "description": "화면 크기를 가져옵니다"}
                ],
                "usage_examples": [
                    {"command": "get_mouse_position()", "description": "현재 마우스 위치 가져오기"},
                    {"command": "move_mouse(100, 200)", "description": "마우스를 (100, 200) 위치로 이동하기"},
                    {"command": "click_mouse(100, 200)", "description": "(100, 200) 위치에서 마우스 클릭하기"},
                    {"command": "drag_mouse(100, 200, 300, 400)", "description": "(100, 200)에서 (300, 400)으로 드래그하기"},
                    {"command": "scroll_mouse(10)", "description": "마우스 휠을 위로 10칸 스크롤하기"}
                ],
                "mouse_buttons": {
                    "left": "왼쪽 버튼",
                    "right": "오른쪽 버튼",
                    "middle": "가운데 버튼 (휠)"
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
        logger.error("mouse_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise