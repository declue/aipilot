# 🖥️ Remote Desktop Capture MCP Server

FastMCP를 이용한 PC 화면 캡처 및 멀티모달 분석 도구입니다.

## ✨ 주요 기능

- 🖼️ **전체 화면 캡처**: 전체 데스크톱 화면을 캡처하여 base64 형식으로 반환
- 🎯 **영역별 캡처**: 지정된 좌표와 크기로 특정 영역만 캡처
- 📝 **주석 추가**: 캡처한 화면에 텍스트 주석 추가
- 🔍 **요소 검색**: 화면에서 특정 이미지 요소 위치 찾기
- 💾 **파일 저장**: 캡처한 이미지를 파일로 저장
- 🤖 **멀티모달 지원**: AI 모델과의 통합을 위한 컨텍스트 정보 제공

## 📦 설치

필요한 패키지를 설치합니다:

```bash
pip install fastmcp pillow pyautogui
```

## 🚀 사용 방법

### 1. MCP 서버 시작

```bash
python tools/remote_desktop.py
```

### 2. 사용 가능한 도구들

#### 📷 전체 화면 캡처
```python
result = await mcp_client.call_tool("capture_full_screen")
```

#### 🎯 특정 영역 캡처
```python
result = await mcp_client.call_tool("capture_region", {
    "x": 100,
    "y": 100, 
    "width": 500,
    "height": 300
})
```

#### ℹ️ 화면 정보 조회
```python
result = await mcp_client.call_tool("get_screen_info")
```

#### 💾 스크린샷 저장
```python
result = await mcp_client.call_tool("save_screenshot", {
    "filename": "my_screenshot.png",
    "folder": "./screenshots"
})
```

#### 📝 주석이 있는 캡처
```python
result = await mcp_client.call_tool("capture_with_annotation", {
    "text": "중요한 영역",
    "x": 200,
    "y": 150,
    "font_size": 24
})
```

#### 🔍 화면에서 요소 찾기
```python
result = await mcp_client.call_tool("find_element_on_screen", {
    "image_path": "./button.png",
    "confidence": 0.8
})
```

#### 🤖 멀티모달 분석용 데이터
```python
result = await mcp_client.call_tool("get_multimodal_analysis_data")
```

## 🔗 AI 모델과의 통합

### OpenAI GPT-4V
```python
import openai
import base64

# 화면 캡처
screen_data = await mcp_client.call_tool("get_multimodal_analysis_data")

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
```

### Google Gemini
```python
import google.generativeai as genai
from PIL import Image
import io

# 화면 캡처
screen_data = await mcp_client.call_tool("capture_full_screen")
image_data = base64.b64decode(screen_data["image"])

# Gemini로 분석
model = genai.GenerativeModel('gemini-pro-vision')
response = model.generate_content([
    "이 화면에서 무엇을 볼 수 있나요?",
    Image.open(io.BytesIO(image_data))
])
```

### Anthropic Claude
```python
import anthropic

# 화면 캡처
screen_data = await mcp_client.call_tool("get_multimodal_analysis_data")

# Claude로 분석
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
```

## 📊 응답 형식

모든 도구는 다음과 같은 형식으로 응답합니다:

```json
{
    "success": true,
    "image": "base64_encoded_image_data",
    "format": "PNG",
    "width": 1920,
    "height": 1080,
    "timestamp": "2024-06-24T10:30:00",
    "message": "Screenshot captured successfully"
}
```

오류 발생 시:

```json
{
    "success": false,
    "error": "Error description",
    "message": "Failed to capture screen"
}
```

## 🧪 테스트

테스트를 실행하려면:

```bash
python tools/test_remote_desktop.py
```

사용 예제를 보려면:

```bash
python tools/remote_desktop_example.py
```

## ⚙️ MCP 클라이언트 설정

`remote_desktop_mcp.json` 파일을 MCP 클라이언트의 설정에 추가:

```json
{
  "mcpServers": {
    "remote-desktop": {
      "command": "python",
      "args": ["tools/remote_desktop.py"],
      "env": {},
      "cwd": "."
    }
  }
}
```

## 🔧 고급 사용법

### 자동화된 UI 테스팅
```python
# 특정 버튼 찾기
button_location = await mcp_client.call_tool("find_element_on_screen", {
    "image_path": "./login_button.png"
})

if button_location["found"]:
    # 버튼 위치에서 스크린샷 캡처
    screenshot = await mcp_client.call_tool("capture_region", {
        "x": button_location["x"] - 50,
        "y": button_location["y"] - 50,
        "width": button_location["width"] + 100,
        "height": button_location["height"] + 100
    })
```

### 모니터링 및 로깅
```python
import asyncio

async def monitor_screen():
    while True:
        # 5초마다 화면 캡처
        screenshot = await mcp_client.call_tool("save_screenshot")
        print(f"Screenshot saved: {screenshot['file_path']}")
        await asyncio.sleep(5)
```

### 멀티모달 분석 파이프라인
```python
async def analyze_screen_with_ai():
    # 화면 캡처 및 컨텍스트 수집
    screen_data = await mcp_client.call_tool("get_multimodal_analysis_data")
    
    # AI 모델로 분석
    analysis = await analyze_with_gpt4v(screen_data["image"])
    
    # 결과를 기반으로 주석 추가
    annotated = await mcp_client.call_tool("capture_with_annotation", {
        "text": analysis["key_finding"],
        "x": analysis["important_area"]["x"],
        "y": analysis["important_area"]["y"]
    })
    
    return annotated
```

## 📋 요구사항

- Python 3.11+
- Windows, macOS, Linux 지원
- 화면 캡처 권한 필요

## 🛡️ 보안 고려사항

- 화면 캡처 시 민감한 정보가 포함될 수 있습니다
- base64 인코딩된 이미지 데이터는 메모리 사용량이 클 수 있습니다
- 프로덕션 환경에서는 적절한 접근 제어를 설정하세요

## 🤝 기여

1. 이 저장소를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/AmazingFeature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/AmazingFeature`)
5. Pull Request를 생성합니다

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 🔗 관련 링크

- [FastMCP](https://github.com/jlowin/fastmcp)
- [PyAutoGUI](https://pyautogui.readthedocs.io/)
- [Pillow](https://pillow.readthedocs.io/)
- [Model Context Protocol](https://github.com/modelcontextprotocol)
