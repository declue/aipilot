#!/usr/bin/env python3
"""
Remote Desktop MCP 서버 기능 데모
직접 함수 호출을 통한 테스트
"""

import sys
import os
import base64
from datetime import datetime

# remote_desktop 모듈의 함수들을 직접 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def demo_banner():
    """데모 배너"""
    print("=" * 60)
    print("🖥️  Remote Desktop Capture 기능 데모")
    print("📸 FastMCP 화면 캡처 및 멀티모달 분석 테스트")
    print("=" * 60)

def save_base64_image(base64_data, filename):
    """base64 이미지를 파일로 저장"""
    try:
        # output 디렉토리 생성
        os.makedirs("output", exist_ok=True)
        
        # base64 디코딩
        image_data = base64.b64decode(base64_data)
        
        # 파일로 저장
        filepath = os.path.join("output", filename)
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        print(f"  💾 이미지 저장됨: {filepath}")
        return filepath
    except Exception as e:
        print(f"  ❌ 이미지 저장 실패: {e}")
        return None

def demo_capture_functions():
    """화면 캡처 기능 데모"""
    print("\n📷 화면 캡처 기능 테스트")
    print("-" * 40)
      try:
        # remote_desktop_core 모듈에서 함수들 임포트
        from remote_desktop_core import (
            capture_full_screen, 
            get_screen_info, 
            capture_region,
            get_multimodal_analysis_data,
            capture_with_annotation,
            save_screenshot
        )
        
        # 1. 화면 정보 조회
        print("1️⃣  화면 정보 조회 중...")
        screen_info = get_screen_info()
        if screen_info["success"]:
            print(f"  📺 화면 크기: {screen_info['screen_width']}x{screen_info['screen_height']}")
            print(f"  🖱️  마우스 위치: ({screen_info['mouse_x']}, {screen_info['mouse_y']})")
        else:
            print(f"  ❌ 실패: {screen_info['error']}")
        
        # 2. 전체 화면 캡처
        print("\n2️⃣  전체 화면 캡처 중...")
        full_screen = capture_full_screen()
        if full_screen["success"]:
            print(f"  ✅ 성공: {full_screen['width']}x{full_screen['height']} 이미지 캡처")
            print(f"  📅 캡처 시간: {full_screen['timestamp']}")
            
            # 이미지 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_base64_image(full_screen["image"], f"full_screen_{timestamp}.png")
        else:
            print(f"  ❌ 실패: {full_screen['error']}")
        
        # 3. 영역 캡처 (화면 중앙 400x300)
        if screen_info["success"]:
            print("\n3️⃣  영역 캡처 중 (화면 중앙 400x300)...")
            center_x = screen_info['screen_width'] // 2 - 200
            center_y = screen_info['screen_height'] // 2 - 150
            
            region_capture = capture_region(center_x, center_y, 400, 300)
            if region_capture["success"]:
                print(f"  ✅ 성공: 영역 ({center_x}, {center_y}) 400x300 캡처")
                
                # 이미지 저장
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_base64_image(region_capture["image"], f"region_{timestamp}.png")
            else:
                print(f"  ❌ 실패: {region_capture['error']}")
        
        # 4. 멀티모달 분석용 데이터 준비
        print("\n4️⃣  멀티모달 분석용 데이터 준비 중...")
        multimodal_data = get_multimodal_analysis_data()
        if multimodal_data["success"]:
            print(f"  ✅ 성공: 멀티모달 데이터 준비 완료")
            print(f"  🤖 분석 준비: {multimodal_data['multimodal_ready']}")
            print(f"  📊 컨텍스트 정보:")
            for key, value in multimodal_data["context"].items():
                if key != "analysis_prompt":
                    print(f"    - {key}: {value}")
            
            # 이미지 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_base64_image(multimodal_data["image"], f"multimodal_{timestamp}.png")
        else:
            print(f"  ❌ 실패: {multimodal_data['error']}")
            
    except ImportError as e:
        print(f"❌ 모듈 임포트 실패: {e}")
        print("💡 remote_desktop.py 파일이 같은 디렉토리에 있는지 확인하세요.")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")

def demo_multimodal_integration():
    """멀티모달 통합 예제"""
    print("\n🤖 멀티모달 AI 통합 예제")
    print("-" * 40)
    
    # GPT-4V 통합 예제 코드
    gpt4v_example = '''
# OpenAI GPT-4V와 통합 예제
import openai

async def analyze_screen_with_gpt4v():
    # 화면 캡처
    screen_data = capture_full_screen()
    
    if screen_data["success"]:
        # GPT-4V로 분석
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "이 화면을 분석해주세요."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{screen_data['image']}"
                            }
                        }
                    ]
                }
            ]
        )
        return response.choices[0].message.content
'''
    
    # Claude 통합 예제 코드
    claude_example = '''
# Anthropic Claude와 통합 예제
import anthropic

def analyze_screen_with_claude():
    # 화면 캡처
    screen_data = capture_full_screen()
    
    if screen_data["success"]:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screen_data["image"]
                            }
                        },
                        {
                            "type": "text",
                            "text": "화면을 분석하고 UI 요소들을 설명해주세요."
                        }
                    ]
                }
            ]
        )
        return message.content[0].text
'''
    
    print("📝 GPT-4V 통합 예제:")
    print(gpt4v_example)
    
    print("\n📝 Claude 통합 예제:")
    print(claude_example)

def main():
    """메인 함수"""
    demo_banner()
    demo_capture_functions()
    demo_multimodal_integration()
    
    print("\n🎉 데모 완료!")
    print("\n📋 다음 단계:")
    print("  1. output 폴더에서 캡처된 이미지들을 확인하세요")
    print("  2. AI 모델과 통합하여 멀티모달 분석을 수행하세요")
    print("  3. MCP 클라이언트에서 이 도구들을 사용하세요")

if __name__ == "__main__":
    main()
