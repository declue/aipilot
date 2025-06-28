#!/usr/bin/env python3
"""
Remote Desktop Screen Capture Tool using FastMCP
PC 화면을 캡처하고 멀티모달로 분석할 수 있는 MCP 서버
"""

import asyncio
import base64
import io
import os
from datetime import datetime
from typing import Any, Dict, Optional

import pyautogui
from fastmcp import FastMCP
from PIL import ImageDraw, ImageFont

# pyautogui 설정
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

# MCP 서버 초기화
mcp = FastMCP("Remote Desktop Capture")


@mcp.tool()
def capture_full_screen() -> Dict[str, Any]:
    """
    전체 화면을 캡처합니다.
    
    Returns:
        Dict containing base64 encoded image and metadata
    """
    try:
        # 전체 화면 캡처
        screenshot = pyautogui.screenshot()
        
        # 이미지를 base64로 인코딩
        buffer = io.BytesIO()
        screenshot.save(buffer, format='PNG')
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # 메타데이터 수집
        screen_size = pyautogui.size()
        timestamp = datetime.now().isoformat()
        
        return {
            "success": True,
            "image": image_base64,
            "format": "PNG",
            "width": screen_size.width,
            "height": screen_size.height,
            "timestamp": timestamp,
            "message": "Full screen captured successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to capture screen"
        }


@mcp.tool()
def capture_region(x: int, y: int, width: int, height: int) -> Dict[str, Any]:
    """
    화면의 특정 영역을 캡처합니다.
    
    Args:
        x: 캡처할 영역의 시작 x 좌표
        y: 캡처할 영역의 시작 y 좌표  
        width: 캡처할 영역의 너비
        height: 캡처할 영역의 높이
        
    Returns:
        Dict containing base64 encoded image and metadata
    """
    try:
        # 좌표 유효성 검사
        screen_size = pyautogui.size()
        if x < 0 or y < 0 or x + width > screen_size.width or y + height > screen_size.height:
            return {
                "success": False,
                "error": "Invalid coordinates or dimensions",
                "message": f"Screen size: {screen_size.width}x{screen_size.height}"
            }
        
        # 영역 캡처
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        
        # 이미지를 base64로 인코딩
        buffer = io.BytesIO()
        screenshot.save(buffer, format='PNG')
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        timestamp = datetime.now().isoformat()
        
        return {
            "success": True,
            "image": image_base64,
            "format": "PNG",
            "width": width,
            "height": height,
            "x": x,
            "y": y,
            "timestamp": timestamp,
            "message": f"Region captured: ({x}, {y}) {width}x{height}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to capture region"
        }


@mcp.tool()
def get_screen_info() -> Dict[str, Any]:
    """
    화면 정보를 가져옵니다.
    
    Returns:
        Dict containing screen information
    """
    try:
        screen_size = pyautogui.size()
        mouse_pos = pyautogui.position()
        
        return {
            "success": True,
            "screen_width": screen_size.width,
            "screen_height": screen_size.height,
            "mouse_x": mouse_pos.x,
            "mouse_y": mouse_pos.y,
            "message": "Screen info retrieved successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get screen info"
        }


@mcp.tool()
def save_screenshot(filename: Optional[str] = None, folder: Optional[str] = None) -> Dict[str, Any]:
    """
    스크린샷을 파일로 저장합니다.
    
    Args:
        filename: 저장할 파일명 (확장자 포함). None이면 자동 생성
        folder: 저장할 폴더 경로. None이면 현재 디렉토리의 output 폴더
        
    Returns:
        Dict containing save result and file path
    """
    try:
        # 기본 폴더 설정
        if folder is None:
            folder = os.path.join(os.getcwd(), "output")
        
        # 폴더가 없으면 생성
        os.makedirs(folder, exist_ok=True)
        
        # 파일명 설정
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        # 확장자 확인
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename += '.png'
        
        # 전체 경로
        file_path = os.path.join(folder, filename)
        
        # 스크린샷 캡처 및 저장
        screenshot = pyautogui.screenshot()
        screenshot.save(file_path)
        
        # 파일 크기 확인
        file_size = os.path.getsize(file_path)
        
        return {
            "success": True,
            "file_path": file_path,
            "filename": filename,
            "folder": folder,
            "file_size": file_size,
            "message": f"Screenshot saved to {file_path}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to save screenshot"
        }


@mcp.tool()
def capture_with_annotation(text: str, x: int, y: int, font_size: int = 20) -> Dict[str, Any]:
    """
    화면을 캡처하고 텍스트 주석을 추가합니다.
    
    Args:
        text: 추가할 텍스트
        x: 텍스트를 추가할 x 좌표
        y: 텍스트를 추가할 y 좌표
        font_size: 폰트 크기
        
    Returns:
        Dict containing annotated image in base64 format
    """
    try:
        # 화면 캡처
        screenshot = pyautogui.screenshot()
        
        # 이미지에 텍스트 추가
        draw = ImageDraw.Draw(screenshot)
        
        # 폰트 설정 (시스템 기본 폰트 사용)
        try:
            # Windows의 경우
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # 기본 폰트 사용
            font = ImageFont.load_default()
        
        # 텍스트 배경을 위한 사각형 그리기
        bbox = draw.textbbox((x, y), text, font=font)
        draw.rectangle(bbox, fill="yellow", outline="black")
        
        # 텍스트 그리기
        draw.text((x, y), text, fill="black", font=font)
        
        # 이미지를 base64로 인코딩
        buffer = io.BytesIO()
        screenshot.save(buffer, format='PNG')
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        timestamp = datetime.now().isoformat()
        
        return {
            "success": True,
            "image": image_base64,
            "format": "PNG",
            "annotation": text,
            "annotation_x": x,
            "annotation_y": y,
            "font_size": font_size,
            "timestamp": timestamp,
            "message": f"Screenshot with annotation captured: '{text}'"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to capture with annotation"
        }


@mcp.tool()
def find_element_on_screen(image_path: str, confidence: float = 0.8) -> Dict[str, Any]:
    """
    화면에서 특정 이미지 요소를 찾습니다.
    
    Args:
        image_path: 찾을 이미지 파일 경로
        confidence: 매칭 신뢰도 (0.0 ~ 1.0)
        
    Returns:
        Dict containing element location if found
    """
    try:
        # 이미지 파일 존재 확인
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image file not found: {image_path}",
                "message": "Please provide a valid image file path"
            }
        
        # 화면에서 이미지 찾기
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        
        if location:
            center = pyautogui.center(location)
            return {
                "success": True,
                "found": True,
                "x": location.left,
                "y": location.top,
                "width": location.width,
                "height": location.height,
                "center_x": center.x,
                "center_y": center.y,
                "confidence": confidence,
                "message": f"Element found at ({location.left}, {location.top})"
            }
        else:
            return {
                "success": True,
                "found": False,
                "confidence": confidence,
                "message": "Element not found on screen"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to find element on screen"
        }


@mcp.tool()
def get_multimodal_analysis_data() -> Dict[str, Any]:
    """
    멀티모달 분석을 위한 화면 데이터를 준비합니다.
    화면 캡처와 함께 컨텍스트 정보를 제공합니다.
    
    Returns:
        Dict containing image and context data for multimodal analysis
    """
    try:
        # 화면 캡처
        screenshot = pyautogui.screenshot()
        
        # 이미지를 base64로 인코딩
        buffer = io.BytesIO()
        screenshot.save(buffer, format='PNG')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # 시스템 정보 수집
        screen_size = pyautogui.size()
        mouse_pos = pyautogui.position()
        timestamp = datetime.now().isoformat()
        
        # 멀티모달 분석을 위한 컨텍스트 정보
        context = {
            "capture_type": "full_screen",
            "screen_resolution": f"{screen_size.width}x{screen_size.height}",
            "mouse_position": f"({mouse_pos.x}, {mouse_pos.y})",
            "timestamp": timestamp,
            "os_info": os.name,
            "analysis_prompt": "이 화면을 분석하여 다음 정보를 제공해주세요: 1) 현재 실행 중인 애플리케이션, 2) 화면의 주요 UI 요소들, 3) 사용자가 수행할 수 있는 액션들"
        }
        
        return {
            "success": True,
            "image": image_base64,
            "format": "PNG",
            "width": screen_size.width,
            "height": screen_size.height,
            "context": context,
            "multimodal_ready": True,
            "message": "Screen data prepared for multimodal analysis"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to prepare multimodal analysis data"
        }


async def main():
    """MCP 서버 실행"""
    # 서버 실행
    await mcp.run()


if __name__ == "__main__":
    print("🖥️  Remote Desktop Capture MCP Server")
    print("📸 FastMCP를 이용한 화면 캡처 및 멀티모달 분석 도구")
    print("🚀 서버를 시작합니다...")
    
    try:
        # 이미 실행 중인 이벤트 루프가 있는지 확인
        try:
            loop = asyncio.get_running_loop()
            print("⚠️  이미 실행 중인 이벤트 루프가 감지되었습니다.")
            print("🔧 nest_asyncio를 사용하여 중첩 이벤트 루프를 활성화합니다.")
            
            # nest_asyncio를 사용하여 중첩된 이벤트 루프 허용
            try:
                import nest_asyncio
                nest_asyncio.apply()
                asyncio.run(main())
            except ImportError:
                print("❌ nest_asyncio가 설치되지 않았습니다.")
                print("📦 설치 명령: pip install nest-asyncio")
                print("🔄 대신 create_task를 사용합니다.")
                loop.create_task(main())
                
        except RuntimeError:
            # 실행 중인 이벤트 루프가 없음
            asyncio.run(main())
            
    except KeyboardInterrupt:
        print("\n⏹️  서버를 종료합니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("💡 해결 방법:")
        print("   1. 새로운 터미널에서 실행해보세요")
        print("   2. pip install nest-asyncio 후 재시도하세요")
        print("   3. 다른 Python 환경에서 실행해보세요")