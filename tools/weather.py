#!/usr/bin/env python3
"""
날씨 정보 MCP 서버
현재 날씨, 일기예보, 특정 도시 날씨 정보를 제공하는 도구들을 제공합니다.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from mcp.server.fastmcp import FastMCP

# Create MCP Server
app = FastMCP(
    title="Weather Server",
    description="A server for weather-related operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# OpenWeatherMap API 설정
API_KEY = os.getenv("OPENWEATHER_API_KEY", "40c77b6946209551ef8273368a753822")
BASE_URL = "http://api.openweathermap.org/data/2.5"
GEO_URL = "http://api.openweathermap.org/geo/1.0"


@dataclass
class WeatherInfo:
    """날씨 정보를 담는 데이터 클래스"""
    city: str
    country: str
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    description: str
    wind_speed: float
    wind_direction: int
    visibility: float
    timestamp: str


class WeatherService:
    """날씨 서비스 클래스 - SOLID 원칙에 따른 단일 책임"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_coordinates(self, city: str) -> Optional[tuple[float, float]]:
        """도시명으로 좌표를 가져옵니다."""
        if not self.api_key:
            return None
            
        try:
            url = f"{GEO_URL}/direct"
            params = {
                "q": city,
                "limit": 1,
                "appid": self.api_key
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data:
                return data[0]["lat"], data[0]["lon"]
            return None
        except Exception:
            return None
    
    def get_weather_data(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """좌표로 날씨 데이터를 가져옵니다."""
        if not self.api_key:
            return None
            
        try:
            url = f"{BASE_URL}/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",
                "lang": "kr"
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
    
    def parse_weather_info(self, data: Dict[str, Any]) -> WeatherInfo:
        """날씨 데이터를 WeatherInfo 객체로 변환합니다."""
        return WeatherInfo(
            city=data["name"],
            country=data["sys"]["country"],
            temperature=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            humidity=data["main"]["humidity"],
            pressure=data["main"]["pressure"],
            description=data["weather"][0]["description"],
            wind_speed=data["wind"]["speed"],
            wind_direction=data["wind"]["deg"],
            visibility=data.get("visibility", 0) / 1000,  # km로 변환
            timestamp=datetime.now().isoformat()
        )


# 전역 서비스 인스턴스
weather_service = WeatherService(API_KEY)


@app.tool()
def get_current_weather(city: str = "Seoul") -> dict:
    """
    지정된 도시의 현재 날씨를 반환합니다.

    Args:
        city: 도시명 (기본값: Seoul)

    Returns:
        dict: 현재 날씨 정보를 포함한 딕셔너리

    Examples:
        >>> get_current_weather("Seoul")
        {'result': '서울 날씨: 맑음, 기온: 15°C, 체감온도: 13°C, 습도: 65%'}
    """
    try:
        if not API_KEY:
            return {"error": "OpenWeatherMap API 키가 설정되지 않았습니다. OPENWEATHER_API_KEY 환경변수를 설정해주세요."}
        
        # 좌표 가져오기
        coords = weather_service.get_coordinates(city)
        if not coords:
            return {"error": f"도시 '{city}'를 찾을 수 없습니다."}
        
        lat, lon = coords
        
        # 날씨 데이터 가져오기
        weather_data = weather_service.get_weather_data(lat, lon)
        if not weather_data:
            return {"error": "날씨 정보를 가져올 수 없습니다."}
        
        # 날씨 정보 파싱
        weather_info = weather_service.parse_weather_info(weather_data)
        
        result = (
            f"{weather_info.city} 날씨: {weather_info.description}, "
            f"기온: {weather_info.temperature:.1f}°C, "
            f"체감온도: {weather_info.feels_like:.1f}°C, "
            f"습도: {weather_info.humidity}%, "
            f"풍속: {weather_info.wind_speed:.1f}m/s"
        )
        
        return {"result": result}
        
    except Exception as e:
        return {"error": f"날씨 정보 조회 중 오류 발생: {str(e)}"}


@app.tool()
def get_detailed_weather(city: str = "Seoul") -> dict:
    """
    지정된 도시의 상세 날씨 정보를 반환합니다.

    Args:
        city: 도시명 (기본값: Seoul)

    Returns:
        dict: 상세 날씨 정보를 포함한 딕셔너리
    """
    try:
        if not API_KEY:
            return {"error": "OpenWeatherMap API 키가 설정되지 않았습니다."}
        
        coords = weather_service.get_coordinates(city)
        if not coords:
            return {"error": f"도시 '{city}'를 찾을 수 없습니다."}
        
        lat, lon = coords
        weather_data = weather_service.get_weather_data(lat, lon)
        if not weather_data:
            return {"error": "날씨 정보를 가져올 수 없습니다."}
        
        weather_info = weather_service.parse_weather_info(weather_data)
        
        result = {
            "도시": f"{weather_info.city}, {weather_info.country}",
            "날씨": weather_info.description,
            "현재기온": f"{weather_info.temperature:.1f}°C",
            "체감온도": f"{weather_info.feels_like:.1f}°C",
            "습도": f"{weather_info.humidity}%",
            "기압": f"{weather_info.pressure}hPa",
            "풍속": f"{weather_info.wind_speed:.1f}m/s",
            "풍향": f"{weather_info.wind_direction}°",
            "가시거리": f"{weather_info.visibility:.1f}km",
            "조회시간": weather_info.timestamp
        }
        
        return {"result": result}
        
    except Exception as e:
        return {"error": f"상세 날씨 정보 조회 중 오류 발생: {str(e)}"}


@app.tool()
def get_weather_forecast(city: str = "Seoul", days: int = 3) -> dict:
    """
    지정된 도시의 일기예보를 반환합니다.

    Args:
        city: 도시명 (기본값: Seoul)
        days: 예보 일수 (1-5일, 기본값: 3)

    Returns:
        dict: 일기예보 정보를 포함한 딕셔너리
    """
    try:
        if not API_KEY:
            return {"error": "OpenWeatherMap API 키가 설정되지 않았습니다."}
        
        if days < 1 or days > 5:
            return {"error": "예보 일수는 1-5일 사이여야 합니다."}
        
        coords = weather_service.get_coordinates(city)
        if not coords:
            return {"error": f"도시 '{city}'를 찾을 수 없습니다."}
        
        lat, lon = coords
        
        # 5일 예보 API 호출
        url = f"{BASE_URL}/forecast"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY,
            "units": "metric",
            "lang": "kr"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 일별 예보 정리 (하루에 8개 데이터 중 낮 12시 데이터만 선택)
        forecasts = []
        for i in range(0, min(days * 8, len(data["list"])), 8):
            if i < len(data["list"]):
                forecast = data["list"][i]
                date = datetime.fromisoformat(forecast["dt_txt"]).strftime("%m월 %d일")
                forecasts.append({
                    "날짜": date,
                    "날씨": forecast["weather"][0]["description"],
                    "최고기온": f"{forecast['main']['temp_max']:.1f}°C",
                    "최저기온": f"{forecast['main']['temp_min']:.1f}°C",
                    "습도": f"{forecast['main']['humidity']}%"
                })
        
        return {
            "result": {
                "도시": f"{data['city']['name']}, {data['city']['country']}",
                "예보": forecasts
            }
        }
        
    except Exception as e:
        return {"error": f"일기예보 조회 중 오류 발생: {str(e)}"}


@app.tool()
def list_major_cities() -> dict:
    """
    주요 도시 목록을 반환합니다.

    Returns:
        dict: 주요 도시들의 목록
    """
    try:
        major_cities = {
            "한국": ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju"],
            "일본": ["Tokyo", "Osaka", "Kyoto", "Yokohama", "Nagoya"],
            "중국": ["Beijing", "Shanghai", "Guangzhou", "Shenzhen"],
            "미국": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
            "유럽": ["London", "Paris", "Berlin", "Rome", "Madrid", "Amsterdam"]
        }
        return {"result": major_cities}
    except Exception as e:
        return {"error": f"도시 목록 조회 중 오류 발생: {str(e)}"}


if __name__ == "__main__":
    app.run(transport="stdio")
