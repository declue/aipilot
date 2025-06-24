#!/usr/bin/env python3
"""
Remote Desktop MCP 서버 사용 예제
FastMCP를 이용한 화면 캡처 도구 사용법 데모
"""

import sys


def print_banner():
    """배너 출력"""
    print("=" * 60)
    print("🖥️  Remote Desktop Capture MCP Server 사용 예제")
    print("📸 FastMCP를 이용한 화면 캡처 및 멀티모달 분석")
    print("=" * 60)

def print_available_tools():
    """사용 가능한 도구들 출력"""
    tools = [
        "📷 capture_full_screen - 전체 화면 캡처",
        "🎯 capture_region - 특정 영역 캡처",
        "ℹ️  get_screen_info - 화면 정보 조회",
        "💾 save_screenshot - 스크린샷 파일 저장",
        "📝 capture_with_annotation - 주석이 있는 화면 캡처",
        "🔍 find_element_on_screen - 화면에서 요소 찾기",
        "🤖 get_multimodal_analysis_data - 멀티모달 분석용 데이터 준비"
    ]
    
    print("\n📋 사용 가능한 도구들:")
    for tool in tools:
        print(f"  {tool}")

def print_usage_examples():
    """사용 예제 출력"""
    print("\n💡 사용 예제:")
    print("""
1. MCP 서버 시작:
   python tools/remote_desktop.py

2. MCP 클라이언트에서 사용:
   # 전체 화면 캡처
   result = await mcp_client.call_tool("capture_full_screen")
   
   # 특정 영역 캡처 (x=100, y=100, width=500, height=300)
   result = await mcp_client.call_tool("capture_region", {
       "x": 100, "y": 100, "width": 500, "height": 300
   })
   
   # 주석이 있는 화면 캡처
   result = await mcp_client.call_tool("capture_with_annotation", {
       "text": "중요한 영역", "x": 200, "y": 150, "font_size": 24
   })
   
   # 멀티모달 분석용 데이터 준비
   result = await mcp_client.call_tool("get_multimodal_analysis_data")
   
3. 반환된 base64 이미지 사용:
   import base64
   from PIL import Image
   import io
   
   # base64 디코딩
   image_data = base64.b64decode(result["image"])
   image = Image.open(io.BytesIO(image_data))
   image.show()
""")

def print_integration_guide():
    """통합 가이드 출력"""
    print("\n🔗 다른 AI 모델과의 통합:")
    print("""
1. OpenAI GPT-4V와 통합:
   # 화면 캡처 후 GPT-4V로 분석
   screen_data = await mcp_client.call_tool("get_multimodal_analysis_data")
   
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

2. Google Gemini와 통합:
   import google.generativeai as genai
   
   screen_data = await mcp_client.call_tool("capture_full_screen")
   image_data = base64.b64decode(screen_data["image"])
   
   model = genai.GenerativeModel('gemini-pro-vision')
   response = model.generate_content([
       "이 화면에서 무엇을 볼 수 있나요?",
       Image.open(io.BytesIO(image_data))
   ])

3. Claude와 통합:
   # Anthropic Claude API 사용
   screen_data = await mcp_client.call_tool("get_multimodal_analysis_data")
   
   message = anthropic.messages.create(
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
""")

def check_dependencies():
    """의존성 확인"""
    print("\n🔍 의존성 확인 중...")
    
    required_packages = [
        ("fastmcp", "fastmcp"),
        ("PIL", "pillow"), 
        ("pyautogui", "pyautogui")
    ]
    missing_packages = []
    
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name} (설치 필요)")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n📦 다음 패키지를 설치해주세요:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    else:
        print("  🎉 모든 의존성이 설치되어 있습니다!")
        return True

def main():
    """메인 함수"""
    print_banner()
    
    if not check_dependencies():
        sys.exit(1)
    
    print_available_tools()
    print_usage_examples()
    print_integration_guide()
    
    print("\n🚀 MCP 서버를 시작하려면:")
    print("   python tools/remote_desktop.py")
    
    print("\n📚 더 자세한 정보:")
    print("   - FastMCP 문서: https://github.com/jlowin/fastmcp")
    print("   - PyAutoGUI 문서: https://pyautogui.readthedocs.io/")
    print("   - PIL/Pillow 문서: https://pillow.readthedocs.io/")

if __name__ == "__main__":
    main()
