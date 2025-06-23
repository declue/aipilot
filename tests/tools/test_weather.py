#!/usr/bin/env python3
"""
날씨 MCP 서버 테스트
"""

from unittest.mock import Mock, patch

import pytest
import requests

from tools.weather import (
    WeatherInfo,
    WeatherService,
    get_current_weather,
    get_detailed_weather,
    get_weather_forecast,
    list_major_cities,
)


class TestWeatherService:
    """WeatherService 클래스 테스트"""
    
    def setup_method(self) -> None:
        """테스트 메서드 실행 전 설정"""
        self.api_key = "test_api_key"
        self.weather_service = WeatherService(self.api_key)
    
    def test_init_with_api_key(self) -> None:
        """API 키가 있는 경우 초기화 테스트"""
        service = WeatherService("test_key")
        assert service.api_key == "test_key"
        assert service.session is not None
    
    def test_init_without_api_key(self) -> None:
        """API 키가 없는 경우 초기화 테스트"""
        service = WeatherService("")
        assert service.api_key == ""
        assert service.session is not None
    
    @patch('tools.weather.requests.Session.get')
    def test_get_coordinates_success(self, mock_get: Mock) -> None:
        """좌표 조회 성공 테스트"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.json.return_value = [
            {"lat": 37.5665, "lon": 126.9780}
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # 테스트 실행
        result = self.weather_service.get_coordinates("Seoul")
        
        # 검증
        assert result == (37.5665, 126.9780)
        mock_get.assert_called_once()
    
    @patch('tools.weather.requests.Session.get')
    def test_get_coordinates_city_not_found(self, mock_get: Mock) -> None:
        """도시를 찾을 수 없는 경우 테스트"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # 테스트 실행
        result = self.weather_service.get_coordinates("NonExistentCity")
        
        # 검증
        assert result is None
    
    def test_get_coordinates_no_api_key(self) -> None:
        """API 키가 없는 경우 테스트"""
        service = WeatherService("")
        result = service.get_coordinates("Seoul")
        assert result is None
    
    @patch('tools.weather.requests.Session.get')
    def test_get_coordinates_api_error(self, mock_get: Mock) -> None:
        """API 오류 발생 테스트"""
        mock_get.side_effect = requests.RequestException("API Error")
        
        result = self.weather_service.get_coordinates("Seoul")
        assert result is None
    
    @patch('tools.weather.requests.Session.get')
    def test_get_weather_data_success(self, mock_get: Mock) -> None:
        """날씨 데이터 조회 성공 테스트"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "Seoul",
            "sys": {"country": "KR"},
            "main": {
                "temp": 15.5,
                "feels_like": 13.2,
                "humidity": 65,
                "pressure": 1013
            },
            "weather": [{"description": "맑음"}],
            "wind": {"speed": 2.5, "deg": 180},
            "visibility": 10000
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # 테스트 실행
        result = self.weather_service.get_weather_data(37.5665, 126.9780)
        
        # 검증
        assert result is not None
        assert result["name"] == "Seoul"
        mock_get.assert_called_once()
    
    def test_get_weather_data_no_api_key(self) -> None:
        """API 키가 없는 경우 테스트"""
        service = WeatherService("")
        result = service.get_weather_data(37.5665, 126.9780)
        assert result is None
    
    @patch('tools.weather.requests.Session.get')
    def test_get_weather_data_api_error(self, mock_get: Mock) -> None:
        """API 오류 발생 테스트"""
        mock_get.side_effect = requests.RequestException("API Error")
        
        result = self.weather_service.get_weather_data(37.5665, 126.9780)
        assert result is None
    
    def test_parse_weather_info(self) -> None:
        """날씨 정보 파싱 테스트"""
        sample_data = {
            "name": "Seoul",
            "sys": {"country": "KR"},
            "main": {
                "temp": 15.5,
                "feels_like": 13.2,
                "humidity": 65,
                "pressure": 1013
            },
            "weather": [{"description": "맑음"}],
            "wind": {"speed": 2.5, "deg": 180},
            "visibility": 10000
        }
        
        weather_info = self.weather_service.parse_weather_info(sample_data)
        
        assert isinstance(weather_info, WeatherInfo)
        assert weather_info.city == "Seoul"
        assert weather_info.country == "KR"
        assert weather_info.temperature == 15.5
        assert weather_info.feels_like == 13.2
        assert weather_info.humidity == 65
        assert weather_info.pressure == 1013
        assert weather_info.description == "맑음"
        assert weather_info.wind_speed == 2.5
        assert weather_info.wind_direction == 180
        assert weather_info.visibility == 10.0  # km로 변환


class TestWeatherInfo:
    """WeatherInfo 데이터 클래스 테스트"""
    
    def test_weather_info_creation(self) -> None:
        """WeatherInfo 생성 테스트"""
        weather_info = WeatherInfo(
            city="Seoul",
            country="KR",
            temperature=15.5,
            feels_like=13.2,
            humidity=65,
            pressure=1013,
            description="맑음",
            wind_speed=2.5,
            wind_direction=180,
            visibility=10.0,
            timestamp="2024-01-15T14:30:45"
        )
        
        assert weather_info.city == "Seoul"
        assert weather_info.country == "KR"
        assert weather_info.temperature == 15.5
        assert weather_info.feels_like == 13.2
        assert weather_info.humidity == 65
        assert weather_info.pressure == 1013
        assert weather_info.description == "맑음"
        assert weather_info.wind_speed == 2.5
        assert weather_info.wind_direction == 180
        assert weather_info.visibility == 10.0
        assert weather_info.timestamp == "2024-01-15T14:30:45"


class TestWeatherTools:
    """날씨 도구 함수들 테스트"""
    
    @patch('tools.weather.API_KEY', 'test_key')
    @patch('tools.weather.weather_service')
    def test_get_current_weather_success(self, mock_service: Mock) -> None:
        """현재 날씨 조회 성공 테스트"""
        # Mock 설정
        mock_service.get_coordinates.return_value = (37.5665, 126.9780)
        mock_service.get_weather_data.return_value = {
            "name": "Seoul",
            "sys": {"country": "KR"},
            "main": {
                "temp": 15.5,
                "feels_like": 13.2,
                "humidity": 65,
                "pressure": 1013
            },
            "weather": [{"description": "맑음"}],
            "wind": {"speed": 2.5, "deg": 180},
            "visibility": 10000
        }
        mock_service.parse_weather_info.return_value = WeatherInfo(
            city="Seoul", country="KR", temperature=15.5, feels_like=13.2,
            humidity=65, pressure=1013, description="맑음", wind_speed=2.5,
            wind_direction=180, visibility=10.0, timestamp="2024-01-15T14:30:45"
        )
        
        # 테스트 실행
        result = get_current_weather("Seoul")
        
        # 검증
        assert "result" in result
        assert "Seoul 날씨: 맑음" in result["result"]
        assert "기온: 15.5°C" in result["result"]
        assert "체감온도: 13.2°C" in result["result"]
        assert "습도: 65%" in result["result"]
        assert "풍속: 2.5m/s" in result["result"]
    
    @patch('tools.weather.API_KEY', '')
    def test_get_current_weather_no_api_key(self):
        """API 키가 없는 경우 테스트"""
        result = get_current_weather("Seoul")
        
        assert "error" in result
        assert "API 키가 설정되지 않았습니다" in result["error"]
    
    @patch('tools.weather.API_KEY', 'test_key')
    @patch('tools.weather.weather_service')
    def test_get_current_weather_city_not_found(self, mock_service):
        """도시를 찾을 수 없는 경우 테스트"""
        mock_service.get_coordinates.return_value = None
        
        result = get_current_weather("NonExistentCity")
        
        assert "error" in result
        assert "도시 'NonExistentCity'를 찾을 수 없습니다" in result["error"]
    
    @patch('tools.weather.API_KEY', 'test_key')
    @patch('tools.weather.weather_service')
    def test_get_current_weather_api_error(self, mock_service):
        """API 오류 발생 테스트"""
        mock_service.get_coordinates.return_value = (37.5665, 126.9780)
        mock_service.get_weather_data.return_value = None
        
        result = get_current_weather("Seoul")
        
        assert "error" in result
        assert "날씨 정보를 가져올 수 없습니다" in result["error"]
    
    @patch('tools.weather.API_KEY', 'test_key')
    @patch('tools.weather.weather_service')
    def test_get_detailed_weather_success(self, mock_service):
        """상세 날씨 정보 조회 성공 테스트"""
        # Mock 설정
        mock_service.get_coordinates.return_value = (37.5665, 126.9780)
        mock_service.get_weather_data.return_value = {"dummy": "data"}
        mock_service.parse_weather_info.return_value = WeatherInfo(
            city="Seoul", country="KR", temperature=15.5, feels_like=13.2,
            humidity=65, pressure=1013, description="맑음", wind_speed=2.5,
            wind_direction=180, visibility=10.0, timestamp="2024-01-15T14:30:45"
        )
        
        # 테스트 실행
        result = get_detailed_weather("Seoul")
        
        # 검증
        assert "result" in result
        assert result["result"]["도시"] == "Seoul, KR"
        assert result["result"]["날씨"] == "맑음"
        assert result["result"]["현재기온"] == "15.5°C"
        assert result["result"]["체감온도"] == "13.2°C"
        assert result["result"]["습도"] == "65%"
        assert result["result"]["기압"] == "1013hPa"
        assert result["result"]["풍속"] == "2.5m/s"
        assert result["result"]["풍향"] == "180°"
        assert result["result"]["가시거리"] == "10.0km"
    
    @patch('tools.weather.API_KEY', 'test_key')
    @patch('tools.weather.requests.get')
    @patch('tools.weather.weather_service')
    def test_get_weather_forecast_success(self, mock_service, mock_get):
        """일기예보 조회 성공 테스트"""
        # Mock 설정
        mock_service.get_coordinates.return_value = (37.5665, 126.9780)
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "city": {"name": "Seoul", "country": "KR"},
            "list": [
                {
                    "dt_txt": "2024-01-15 12:00:00",
                    "weather": [{"description": "맑음"}],
                    "main": {
                        "temp_max": 18.0,
                        "temp_min": 10.0,
                        "humidity": 60
                    }
                },
                # 8개 더미 데이터 (하루에 8개씩)
                *[{"dummy": f"data_{i}"} for i in range(7)],
                {
                    "dt_txt": "2024-01-16 12:00:00",
                    "weather": [{"description": "흐림"}],
                    "main": {
                        "temp_max": 15.0,
                        "temp_min": 8.0,
                        "humidity": 70
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # 테스트 실행
        result = get_weather_forecast("Seoul", 2)
        
        # 검증
        assert "result" in result
        assert result["result"]["도시"] == "Seoul, KR"
        assert len(result["result"]["예보"]) == 2
        assert result["result"]["예보"][0]["날짜"] == "01월 15일"
        assert result["result"]["예보"][0]["날씨"] == "맑음"
        assert result["result"]["예보"][0]["최고기온"] == "18.0°C"
        assert result["result"]["예보"][0]["최저기온"] == "10.0°C"
        assert result["result"]["예보"][0]["습도"] == "60%"
    
    @patch('tools.weather.API_KEY', 'test_key')
    def test_get_weather_forecast_invalid_days(self):
        """잘못된 예보 일수 입력 테스트"""
        result = get_weather_forecast("Seoul", 6)
        
        assert "error" in result
        assert "예보 일수는 1-5일 사이여야 합니다" in result["error"]
    
    def test_list_major_cities_success(self):
        """주요 도시 목록 조회 성공 테스트"""
        result = list_major_cities()
        
        assert "result" in result
        assert "한국" in result["result"]
        assert "Seoul" in result["result"]["한국"]
        assert "일본" in result["result"]
        assert "Tokyo" in result["result"]["일본"]
        assert "미국" in result["result"]
        assert "New York" in result["result"]["미국"]


class TestIntegration:
    """통합 테스트"""
    
    @patch('tools.weather.API_KEY', 'test_key')
    @patch('tools.weather.requests.Session.get')
    def test_full_weather_flow(self, mock_get):
        """전체 날씨 조회 플로우 통합 테스트"""
        # 좌표 조회 Mock
        coord_response = Mock()
        coord_response.json.return_value = [
            {"lat": 37.5665, "lon": 126.9780}
        ]
        coord_response.raise_for_status.return_value = None
        
        # 날씨 데이터 Mock
        weather_response = Mock()
        weather_response.json.return_value = {
            "name": "Seoul",
            "sys": {"country": "KR"},
            "main": {
                "temp": 15.5,
                "feels_like": 13.2,
                "humidity": 65,
                "pressure": 1013
            },
            "weather": [{"description": "맑음"}],
            "wind": {"speed": 2.5, "deg": 180},
            "visibility": 10000
        }
        weather_response.raise_for_status.return_value = None
        
        # API 호출 순서에 따른 응답 설정
        mock_get.side_effect = [coord_response, weather_response]
        
        # 새로운 WeatherService 인스턴스로 테스트
        service = WeatherService("test_key")
        
        # 좌표 조회
        coords = service.get_coordinates("Seoul")
        assert coords == (37.5665, 126.9780)
        
        # 날씨 데이터 조회
        weather_data = service.get_weather_data(37.5665, 126.9780)
        assert weather_data["name"] == "Seoul"
        
        # 날씨 정보 파싱
        weather_info = service.parse_weather_info(weather_data)
        assert weather_info.city == "Seoul"
        assert weather_info.temperature == 15.5
        
        # Mock 호출 검증
        assert mock_get.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 