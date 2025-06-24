#!/usr/bin/env python3
"""
날씨 MCP 서버 사용 예시
실제 API 키 없이도 동작하는 예시 코드입니다.
"""

import os

from weather import (
    get_current_weather,
    get_detailed_weather,
    get_weather_forecast,
    list_major_cities,
)


def demo_without_api_key():
    """API 키 없이 동작하는 데모 (에러 메시지 표시)"""
    print("=== 날씨 MCP 서버 데모 ===\n")
    
    print("1. 현재 날씨 조회 (API 키 없음)")
    result = get_current_weather("Seoul")
    print(f"결과: {result}\n")
    
    print("2. 상세 날씨 정보 조회 (API 키 없음)")
    result = get_detailed_weather("Seoul")
    print(f"결과: {result}\n")
    
    print("3. 일기예보 조회 (API 키 없음)")
    result = get_weather_forecast("Seoul", 3)
    print(f"결과: {result}\n")
    
    print("4. 주요 도시 목록 조회 (API 키 불필요)")
    result = list_major_cities()
    print(f"결과: {result}\n")


def show_api_setup_guide():
    """API 설정 가이드 표시"""
    print("=== API 키 설정 가이드 ===\n")
    print("실제 날씨 정보를 받으려면 다음 단계를 따르세요:")
    print("1. https://openweathermap.org/api 에서 무료 API 키 발급")
    print("2. 환경변수 설정:")
    print("   Windows: set OPENWEATHER_API_KEY=your_api_key")
    print("   Linux/Mac: export OPENWEATHER_API_KEY=your_api_key")
    print("3. 또는 .env 파일 생성:")
    print("   OPENWEATHER_API_KEY=your_api_key")
    print()


if __name__ == "__main__":
    # API 키 설정 가이드 표시
    show_api_setup_guide()
    
    
    # 환경변수 확인
    api_key = os.getenv("OPENWEATHER_API_KEY", "bd5e378503939ddaee76f12ad7a97608")
    if api_key:
        print(f"=== API 키 감지됨 ===")
        result = get_current_weather("Seoul")
        print(f"실제 API 호출을 테스트해보세요! 결과: {result}")
        print("python weather.py 명령으로 MCP 서버를 시작할 수 있습니다.")
    else:
        print("=== API 키 미설정 ===")
        print("실제 날씨 데이터를 받으려면 위의 가이드를 따라 API 키를 설정하세요.") 