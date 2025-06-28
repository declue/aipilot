#!/usr/bin/env python3
"""
SmartThings API MCP Server
SmartThings REST API를 통해 디바이스를 제어하고 다양한 정보를 조회하는 도구를 제공합니다.
LLM을 통한 SmartThings의 다양한 기능을 활용할 수 있는 도구입니다.
"""

import logging
import os
import sys
import time
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import requests
from mcp.server.fastmcp import FastMCP

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 smartthings_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "smartthings_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("SMARTTHINGS_TOOL_LOG_LEVEL", "WARNING").upper()
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
    logger.info("SmartThings Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="SmartThings API Server",
    description="A server for SmartThings API operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
SMARTTHINGS_API_URL = "https://api.smartthings.com/v1"
USER_AGENT = "SmartThings-API-MCP-Tool/1.0"


@dataclass
class SmartThingsLocation:
    """SmartThings 위치 정보를 담는 데이터 클래스"""
    id: str
    name: str
    country_code: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    region_radius: int = 0
    temperature_scale: str = "C"
    locale: str = "ko"
    timezone_id: str = "Asia/Seoul"
    created_date: str = ""
    parent_location_id: str = ""


@dataclass
class SmartThingsRoom:
    """SmartThings 방 정보를 담는 데이터 클래스"""
    id: str
    location_id: str
    name: str
    background_image: str = ""
    created_date: str = ""


@dataclass
class SmartThingsDeviceComponent:
    """SmartThings 디바이스 컴포넌트 정보를 담는 데이터 클래스"""
    id: str
    label: str
    capabilities: List[str] = field(default_factory=list)


@dataclass
class SmartThingsDeviceStatus:
    """SmartThings 디바이스 상태 정보를 담는 데이터 클래스"""
    component_id: str
    capability: str
    attribute: str
    value: Any
    unit: str = ""
    timestamp: str = ""


@dataclass
class SmartThingsDevice:
    """SmartThings 디바이스 정보를 담는 데이터 클래스"""
    id: str
    name: str
    label: str
    device_type: str
    device_type_name: str
    device_manufacturer_code: str = ""
    location_id: str = ""
    room_id: str = ""
    device_network_type: str = ""
    components: List[SmartThingsDeviceComponent] = field(default_factory=list)
    status: List[SmartThingsDeviceStatus] = field(default_factory=list)
    health_state: str = ""
    created_date: str = ""


@dataclass
class SmartThingsCapability:
    """SmartThings 기능 정보를 담는 데이터 클래스"""
    id: str
    version: int
    name: str = ""
    status: str = ""
    attributes: Dict = field(default_factory=dict)
    commands: Dict = field(default_factory=dict)


@dataclass
class SmartThingsScene:
    """SmartThings 씬 정보를 담는 데이터 클래스"""
    id: str
    name: str
    location_id: str
    icon: str = ""
    color: str = ""
    created_date: str = ""
    last_executed_date: str = ""
    editable: bool = True
    visible: bool = True


@dataclass
class SmartThingsRule:
    """SmartThings 규칙 정보를 담는 데이터 클래스"""
    id: str
    name: str
    location_id: str
    owner_type: str = ""
    owner_id: str = ""
    status: str = ""
    created_date: str = ""
    last_updated_date: str = ""


@dataclass
class SmartThingsSubscription:
    """SmartThings 구독 정보를 담는 데이터 클래스"""
    id: str
    source_type: str
    capability: str = ""
    attribute: str = ""
    value: Any = None
    state_change_only: bool = True
    subscription_name: str = ""
    location_id: str = ""
    device_id: str = ""


class SmartThingsAPIService:
    """SmartThings API 서비스 클래스"""

    def __init__(self, token: str = None):
        """
        SmartThings API 서비스 초기화
        
        Args:
            token: SmartThings API 토큰 (없으면 환경 변수에서 가져옴)
        """
        self.token = token or os.getenv("SMARTTHINGS_API_TOKEN", "")
        
        if not self.token:
            logger.warning("SmartThings API 토큰이 설정되지 않았습니다.")
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        
        # 인증 토큰 설정
        if self.token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}"
            })

    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """
        SmartThings API 요청을 수행합니다.
        
        Args:
            method: HTTP 메서드 (GET, POST, PUT, DELETE)
            endpoint: API 엔드포인트 경로
            params: URL 파라미터
            data: 요청 데이터
            
        Returns:
            Dict: API 응답 데이터
        """
        try:
            # API 요청 URL 구성
            url = f"{SMARTTHINGS_API_URL}/{endpoint.lstrip('/')}"
            
            # API 요청 수행
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            
            # 응답 확인
            response.raise_for_status()
            
            # JSON 응답 반환
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SmartThings API 요청 중 오류 발생: {e}")
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                error_message = f"HTTP 오류 {status_code}"
                
                try:
                    error_data = e.response.json()
                    if "message" in error_data:
                        error_message = f"{error_message}: {error_data['message']}"
                except:
                    pass
                
                logger.error(error_message)
                return {"error": error_message}
            
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"SmartThings API 요청 중 예외 발생: {e}")
            return {"error": str(e)}

    def get_locations(self) -> List[SmartThingsLocation]:
        """
        SmartThings 위치 목록을 가져옵니다.
        
        Returns:
            List[SmartThingsLocation]: 위치 목록
        """
        try:
            # 위치 API 호출
            response = self._make_request("GET", "locations")
            
            if "error" in response:
                logger.error(f"위치 목록 가져오기 중 오류: {response['error']}")
                return []
            
            # 위치 목록 파싱
            locations = []
            for item in response.get("items", []):
                location = SmartThingsLocation(
                    id=item.get("locationId", ""),
                    name=item.get("name", ""),
                    country_code=item.get("countryCode", ""),
                    latitude=item.get("latitude", 0.0),
                    longitude=item.get("longitude", 0.0),
                    region_radius=item.get("regionRadius", 0),
                    temperature_scale=item.get("temperatureScale", "C"),
                    locale=item.get("locale", "ko"),
                    timezone_id=item.get("timeZoneId", "Asia/Seoul"),
                    created_date=item.get("created", ""),
                    parent_location_id=item.get("parentLocationId", "")
                )
                locations.append(location)
            
            return locations
            
        except Exception as e:
            logger.error(f"위치 목록 가져오기 중 예외 발생: {e}")
            return []

    def get_location(self, location_id: str) -> Optional[SmartThingsLocation]:
        """
        SmartThings 위치 정보를 가져옵니다.
        
        Args:
            location_id: 위치 ID
            
        Returns:
            SmartThingsLocation: 위치 정보 객체 또는 None (실패 시)
        """
        try:
            # 위치 API 호출
            response = self._make_request("GET", f"locations/{location_id}")
            
            if "error" in response:
                logger.error(f"위치 정보 가져오기 중 오류: {response['error']}")
                return None
            
            # 위치 정보 파싱
            location = SmartThingsLocation(
                id=response.get("locationId", ""),
                name=response.get("name", ""),
                country_code=response.get("countryCode", ""),
                latitude=response.get("latitude", 0.0),
                longitude=response.get("longitude", 0.0),
                region_radius=response.get("regionRadius", 0),
                temperature_scale=response.get("temperatureScale", "C"),
                locale=response.get("locale", "ko"),
                timezone_id=response.get("timeZoneId", "Asia/Seoul"),
                created_date=response.get("created", ""),
                parent_location_id=response.get("parentLocationId", "")
            )
            
            return location
            
        except Exception as e:
            logger.error(f"위치 정보 가져오기 중 예외 발생: {e}")
            return None

    def get_rooms(self, location_id: str) -> List[SmartThingsRoom]:
        """
        SmartThings 방 목록을 가져옵니다.
        
        Args:
            location_id: 위치 ID
            
        Returns:
            List[SmartThingsRoom]: 방 목록
        """
        try:
            # 방 API 호출
            response = self._make_request("GET", f"locations/{location_id}/rooms")
            
            if "error" in response:
                logger.error(f"방 목록 가져오기 중 오류: {response['error']}")
                return []
            
            # 방 목록 파싱
            rooms = []
            for item in response.get("items", []):
                room = SmartThingsRoom(
                    id=item.get("roomId", ""),
                    location_id=location_id,
                    name=item.get("name", ""),
                    background_image=item.get("backgroundImage", ""),
                    created_date=item.get("created", "")
                )
                rooms.append(room)
            
            return rooms
            
        except Exception as e:
            logger.error(f"방 목록 가져오기 중 예외 발생: {e}")
            return []

    def get_room(self, location_id: str, room_id: str) -> Optional[SmartThingsRoom]:
        """
        SmartThings 방 정보를 가져옵니다.
        
        Args:
            location_id: 위치 ID
            room_id: 방 ID
            
        Returns:
            SmartThingsRoom: 방 정보 객체 또는 None (실패 시)
        """
        try:
            # 방 API 호출
            response = self._make_request("GET", f"locations/{location_id}/rooms/{room_id}")
            
            if "error" in response:
                logger.error(f"방 정보 가져오기 중 오류: {response['error']}")
                return None
            
            # 방 정보 파싱
            room = SmartThingsRoom(
                id=response.get("roomId", ""),
                location_id=location_id,
                name=response.get("name", ""),
                background_image=response.get("backgroundImage", ""),
                created_date=response.get("created", "")
            )
            
            return room
            
        except Exception as e:
            logger.error(f"방 정보 가져오기 중 예외 발생: {e}")
            return None

    def get_devices(self, location_id: str = None, capability: str = None) -> List[SmartThingsDevice]:
        """
        SmartThings 디바이스 목록을 가져옵니다.
        
        Args:
            location_id: 위치 ID (선택 사항)
            capability: 기능 ID (선택 사항)
            
        Returns:
            List[SmartThingsDevice]: 디바이스 목록
        """
        try:
            # 디바이스 요청 파라미터
            params = {}
            if location_id:
                params["locationId"] = location_id
            if capability:
                params["capability"] = capability
            
            # 디바이스 API 호출
            response = self._make_request("GET", "devices", params=params)
            
            if "error" in response:
                logger.error(f"디바이스 목록 가져오기 중 오류: {response['error']}")
                return []
            
            # 디바이스 목록 파싱
            devices = []
            for item in response.get("items", []):
                # 컴포넌트 파싱
                components = []
                for component_id, component_data in item.get("components", {}).items():
                    capabilities = []
                    for capability in component_data.get("capabilities", []):
                        capabilities.append(capability.get("id", ""))
                    
                    component = SmartThingsDeviceComponent(
                        id=component_id,
                        label=component_data.get("label", component_id),
                        capabilities=capabilities
                    )
                    components.append(component)
                
                # 디바이스 객체 생성
                device = SmartThingsDevice(
                    id=item.get("deviceId", ""),
                    name=item.get("name", ""),
                    label=item.get("label", ""),
                    device_type=item.get("deviceType", ""),
                    device_type_name=item.get("deviceTypeName", ""),
                    device_manufacturer_code=item.get("deviceManufacturerCode", ""),
                    location_id=item.get("locationId", ""),
                    room_id=item.get("roomId", ""),
                    device_network_type=item.get("deviceNetworkType", ""),
                    components=components,
                    health_state=item.get("healthState", ""),
                    created_date=item.get("created", "")
                )
                devices.append(device)
            
            return devices
            
        except Exception as e:
            logger.error(f"디바이스 목록 가져오기 중 예외 발생: {e}")
            return []

    def get_device(self, device_id: str) -> Optional[SmartThingsDevice]:
        """
        SmartThings 디바이스 정보를 가져옵니다.
        
        Args:
            device_id: 디바이스 ID
            
        Returns:
            SmartThingsDevice: 디바이스 정보 객체 또는 None (실패 시)
        """
        try:
            # 디바이스 API 호출
            response = self._make_request("GET", f"devices/{device_id}")
            
            if "error" in response:
                logger.error(f"디바이스 정보 가져오기 중 오류: {response['error']}")
                return None
            
            # 컴포넌트 파싱
            components = []
            for component_id, component_data in response.get("components", {}).items():
                capabilities = []
                for capability in component_data.get("capabilities", []):
                    capabilities.append(capability.get("id", ""))
                
                component = SmartThingsDeviceComponent(
                    id=component_id,
                    label=component_data.get("label", component_id),
                    capabilities=capabilities
                )
                components.append(component)
            
            # 디바이스 객체 생성
            device = SmartThingsDevice(
                id=response.get("deviceId", ""),
                name=response.get("name", ""),
                label=response.get("label", ""),
                device_type=response.get("deviceType", ""),
                device_type_name=response.get("deviceTypeName", ""),
                device_manufacturer_code=response.get("deviceManufacturerCode", ""),
                location_id=response.get("locationId", ""),
                room_id=response.get("roomId", ""),
                device_network_type=response.get("deviceNetworkType", ""),
                components=components,
                health_state=response.get("healthState", ""),
                created_date=response.get("created", "")
            )
            
            return device
            
        except Exception as e:
            logger.error(f"디바이스 정보 가져오기 중 예외 발생: {e}")
            return None

    def get_device_status(self, device_id: str) -> List[SmartThingsDeviceStatus]:
        """
        SmartThings 디바이스 상태를 가져옵니다.
        
        Args:
            device_id: 디바이스 ID
            
        Returns:
            List[SmartThingsDeviceStatus]: 디바이스 상태 목록
        """
        try:
            # 디바이스 상태 API 호출
            response = self._make_request("GET", f"devices/{device_id}/status")
            
            if "error" in response:
                logger.error(f"디바이스 상태 가져오기 중 오류: {response['error']}")
                return []
            
            # 디바이스 상태 파싱
            status_list = []
            for component_id, component_data in response.get("components", {}).items():
                for capability_id, capability_data in component_data.items():
                    for attribute, attribute_data in capability_data.items():
                        status = SmartThingsDeviceStatus(
                            component_id=component_id,
                            capability=capability_id,
                            attribute=attribute,
                            value=attribute_data.get("value"),
                            unit=attribute_data.get("unit", ""),
                            timestamp=attribute_data.get("timestamp", "")
                        )
                        status_list.append(status)
            
            return status_list
            
        except Exception as e:
            logger.error(f"디바이스 상태 가져오기 중 예외 발생: {e}")
            return []

    def execute_device_command(self, device_id: str, component_id: str, capability: str, command: str, arguments: List = None) -> Dict:
        """
        SmartThings 디바이스 명령을 실행합니다.
        
        Args:
            device_id: 디바이스 ID
            component_id: 컴포넌트 ID
            capability: 기능 ID
            command: 명령 ID
            arguments: 명령 인자 (선택 사항)
            
        Returns:
            Dict: 명령 실행 결과
        """
        try:
            # 명령 데이터 구성
            command_data = {
                "commands": [
                    {
                        "component": component_id,
                        "capability": capability,
                        "command": command,
                        "arguments": arguments or []
                    }
                ]
            }
            
            # 디바이스 명령 API 호출
            response = self._make_request("POST", f"devices/{device_id}/commands", data=command_data)
            
            if "error" in response:
                logger.error(f"디바이스 명령 실행 중 오류: {response['error']}")
                return {"error": response["error"]}
            
            return response
            
        except Exception as e:
            logger.error(f"디바이스 명령 실행 중 예외 발생: {e}")
            return {"error": str(e)}

    def get_capability(self, capability_id: str, version: int = 1) -> Optional[SmartThingsCapability]:
        """
        SmartThings 기능 정보를 가져옵니다.
        
        Args:
            capability_id: 기능 ID
            version: 기능 버전
            
        Returns:
            SmartThingsCapability: 기능 정보 객체 또는 None (실패 시)
        """
        try:
            # 기능 API 호출
            response = self._make_request("GET", f"capabilities/{capability_id}/{version}")
            
            if "error" in response:
                logger.error(f"기능 정보 가져오기 중 오류: {response['error']}")
                return None
            
            # 기능 정보 파싱
            capability = SmartThingsCapability(
                id=response.get("id", ""),
                version=response.get("version", 1),
                name=response.get("name", ""),
                status=response.get("status", ""),
                attributes=response.get("attributes", {}),
                commands=response.get("commands", {})
            )
            
            return capability
            
        except Exception as e:
            logger.error(f"기능 정보 가져오기 중 예외 발생: {e}")
            return None

    def get_scenes(self, location_id: str = None) -> List[SmartThingsScene]:
        """
        SmartThings 씬 목록을 가져옵니다.
        
        Args:
            location_id: 위치 ID (선택 사항)
            
        Returns:
            List[SmartThingsScene]: 씬 목록
        """
        try:
            # 씬 요청 파라미터
            params = {}
            if location_id:
                params["locationId"] = location_id
            
            # 씬 API 호출
            response = self._make_request("GET", "scenes", params=params)
            
            if "error" in response:
                logger.error(f"씬 목록 가져오기 중 오류: {response['error']}")
                return []
            
            # 씬 목록 파싱
            scenes = []
            for item in response.get("items", []):
                scene = SmartThingsScene(
                    id=item.get("sceneId", ""),
                    name=item.get("sceneName", ""),
                    location_id=item.get("locationId", ""),
                    icon=item.get("icon", ""),
                    color=item.get("color", ""),
                    created_date=item.get("createdDate", ""),
                    last_executed_date=item.get("lastExecutedDate", ""),
                    editable=item.get("editable", True),
                    visible=item.get("visible", True)
                )
                scenes.append(scene)
            
            return scenes
            
        except Exception as e:
            logger.error(f"씬 목록 가져오기 중 예외 발생: {e}")
            return []

    def execute_scene(self, scene_id: str) -> Dict:
        """
        SmartThings 씬을 실행합니다.
        
        Args:
            scene_id: 씬 ID
            
        Returns:
            Dict: 씬 실행 결과
        """
        try:
            # 씬 실행 API 호출
            response = self._make_request("POST", f"scenes/{scene_id}/execute")
            
            if "error" in response:
                logger.error(f"씬 실행 중 오류: {response['error']}")
                return {"error": response["error"]}
            
            return response
            
        except Exception as e:
            logger.error(f"씬 실행 중 예외 발생: {e}")
            return {"error": str(e)}

    def get_rules(self, location_id: str = None) -> List[SmartThingsRule]:
        """
        SmartThings 규칙 목록을 가져옵니다.
        
        Args:
            location_id: 위치 ID (선택 사항)
            
        Returns:
            List[SmartThingsRule]: 규칙 목록
        """
        try:
            # 규칙 요청 파라미터
            params = {}
            if location_id:
                params["locationId"] = location_id
            
            # 규칙 API 호출
            response = self._make_request("GET", "rules", params=params)
            
            if "error" in response:
                logger.error(f"규칙 목록 가져오기 중 오류: {response['error']}")
                return []
            
            # 규칙 목록 파싱
            rules = []
            for item in response.get("items", []):
                rule = SmartThingsRule(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    location_id=item.get("locationId", ""),
                    owner_type=item.get("ownerType", ""),
                    owner_id=item.get("ownerId", ""),
                    status=item.get("status", ""),
                    created_date=item.get("dateCreated", ""),
                    last_updated_date=item.get("dateUpdated", "")
                )
                rules.append(rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"규칙 목록 가져오기 중 예외 발생: {e}")
            return []

    def get_rule(self, rule_id: str) -> Optional[SmartThingsRule]:
        """
        SmartThings 규칙 정보를 가져옵니다.
        
        Args:
            rule_id: 규칙 ID
            
        Returns:
            SmartThingsRule: 규칙 정보 객체 또는 None (실패 시)
        """
        try:
            # 규칙 API 호출
            response = self._make_request("GET", f"rules/{rule_id}")
            
            if "error" in response:
                logger.error(f"규칙 정보 가져오기 중 오류: {response['error']}")
                return None
            
            # 규칙 정보 파싱
            rule = SmartThingsRule(
                id=response.get("id", ""),
                name=response.get("name", ""),
                location_id=response.get("locationId", ""),
                owner_type=response.get("ownerType", ""),
                owner_id=response.get("ownerId", ""),
                status=response.get("status", ""),
                created_date=response.get("dateCreated", ""),
                last_updated_date=response.get("dateUpdated", "")
            )
            
            return rule
            
        except Exception as e:
            logger.error(f"규칙 정보 가져오기 중 예외 발생: {e}")
            return None

    def execute_rule(self, rule_id: str) -> Dict:
        """
        SmartThings 규칙을 실행합니다.
        
        Args:
            rule_id: 규칙 ID
            
        Returns:
            Dict: 규칙 실행 결과
        """
        try:
            # 규칙 실행 API 호출
            response = self._make_request("POST", f"rules/{rule_id}/execute")
            
            if "error" in response:
                logger.error(f"규칙 실행 중 오류: {response['error']}")
                return {"error": response["error"]}
            
            return response
            
        except Exception as e:
            logger.error(f"규칙 실행 중 예외 발생: {e}")
            return {"error": str(e)}

    def get_subscriptions(self, location_id: str = None, device_id: str = None) -> List[SmartThingsSubscription]:
        """
        SmartThings 구독 목록을 가져옵니다.
        
        Args:
            location_id: 위치 ID (선택 사항)
            device_id: 디바이스 ID (선택 사항)
            
        Returns:
            List[SmartThingsSubscription]: 구독 목록
        """
        try:
            # 구독 요청 파라미터
            params = {}
            if location_id:
                params["locationId"] = location_id
            if device_id:
                params["deviceId"] = device_id
            
            # 구독 API 호출
            response = self._make_request("GET", "subscriptions", params=params)
            
            if "error" in response:
                logger.error(f"구독 목록 가져오기 중 오류: {response['error']}")
                return []
            
            # 구독 목록 파싱
            subscriptions = []
            for item in response.get("items", []):
                subscription = SmartThingsSubscription(
                    id=item.get("id", ""),
                    source_type=item.get("sourceType", ""),
                    capability=item.get("capability", ""),
                    attribute=item.get("attribute", ""),
                    value=item.get("value"),
                    state_change_only=item.get("stateChangeOnly", True),
                    subscription_name=item.get("subscriptionName", ""),
                    location_id=item.get("locationId", ""),
                    device_id=item.get("deviceId", "")
                )
                subscriptions.append(subscription)
            
            return subscriptions
            
        except Exception as e:
            logger.error(f"구독 목록 가져오기 중 예외 발생: {e}")
            return []


# 전역 서비스 인스턴스
smartthings_api = SmartThingsAPIService()


@app.tool()
def get_locations() -> dict:
    """
    SmartThings 위치 목록을 가져옵니다.
    
    Returns:
        dict: 위치 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_locations()
        {'result': {'locations': [...]}}
    """
    try:
        # 위치 목록 가져오기
        locations = smartthings_api.get_locations()
        
        # 결과 포맷팅
        formatted_locations = []
        for location in locations:
            formatted_location = {
                "id": location.id,
                "name": location.name,
                "country_code": location.country_code,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "temperature_scale": location.temperature_scale,
                "timezone_id": location.timezone_id,
                "created_date": location.created_date
            }
            formatted_locations.append(formatted_location)
            
        return {
            "result": {
                "count": len(formatted_locations),
                "locations": formatted_locations
            }
        }
        
    except Exception as e:
        return {"error": f"위치 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_rooms(location_id: str) -> dict:
    """
    SmartThings 방 목록을 가져옵니다.
    
    Args:
        location_id: 위치 ID
        
    Returns:
        dict: 방 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_rooms("location-id")
        {'result': {'location_id': 'location-id', 'rooms': [...]}}
    """
    try:
        if not location_id:
            return {"error": "위치 ID를 입력해주세요."}
            
        # 방 목록 가져오기
        rooms = smartthings_api.get_rooms(location_id)
        
        # 결과 포맷팅
        formatted_rooms = []
        for room in rooms:
            formatted_room = {
                "id": room.id,
                "name": room.name,
                "background_image": room.background_image,
                "created_date": room.created_date
            }
            formatted_rooms.append(formatted_room)
            
        return {
            "result": {
                "location_id": location_id,
                "count": len(formatted_rooms),
                "rooms": formatted_rooms
            }
        }
        
    except Exception as e:
        return {"error": f"방 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_devices(location_id: str = None, capability: str = None) -> dict:
    """
    SmartThings 디바이스 목록을 가져옵니다.
    
    Args:
        location_id: 위치 ID (선택 사항)
        capability: 기능 ID (선택 사항)
        
    Returns:
        dict: 디바이스 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_devices(location_id="location-id")
        {'result': {'count': 5, 'devices': [...]}}
        >>> get_devices(capability="switch")
        {'result': {'count': 3, 'devices': [...]}}
    """
    try:
        # 디바이스 목록 가져오기
        devices = smartthings_api.get_devices(location_id, capability)
        
        # 결과 포맷팅
        formatted_devices = []
        for device in devices:
            # 컴포넌트 포맷팅
            components = []
            for component in device.components:
                components.append({
                    "id": component.id,
                    "label": component.label,
                    "capabilities": component.capabilities
                })
            
            formatted_device = {
                "id": device.id,
                "name": device.name,
                "label": device.label,
                "type": device.device_type,
                "type_name": device.device_type_name,
                "location_id": device.location_id,
                "room_id": device.room_id,
                "components": components,
                "health_state": device.health_state,
                "created_date": device.created_date
            }
            formatted_devices.append(formatted_device)
            
        return {
            "result": {
                "location_id": location_id,
                "capability": capability,
                "count": len(formatted_devices),
                "devices": formatted_devices
            }
        }
        
    except Exception as e:
        return {"error": f"디바이스 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_device_status(device_id: str) -> dict:
    """
    SmartThings 디바이스 상태를 가져옵니다.
    
    Args:
        device_id: 디바이스 ID
        
    Returns:
        dict: 디바이스 상태를 포함한 딕셔너리
        
    Examples:
        >>> get_device_status("device-id")
        {'result': {'device_id': 'device-id', 'status': [...]}}
    """
    try:
        if not device_id:
            return {"error": "디바이스 ID를 입력해주세요."}
            
        # 디바이스 정보 가져오기
        device = smartthings_api.get_device(device_id)
        if not device:
            return {"error": f"디바이스를 찾을 수 없습니다: {device_id}"}
            
        # 디바이스 상태 가져오기
        status_list = smartthings_api.get_device_status(device_id)
        
        # 결과 포맷팅
        formatted_status = []
        for status in status_list:
            formatted_status.append({
                "component": status.component_id,
                "capability": status.capability,
                "attribute": status.attribute,
                "value": status.value,
                "unit": status.unit,
                "timestamp": status.timestamp
            })
            
        return {
            "result": {
                "device_id": device_id,
                "name": device.name,
                "label": device.label,
                "type": device.device_type,
                "status": formatted_status
            }
        }
        
    except Exception as e:
        return {"error": f"디바이스 상태 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def execute_device_command(device_id: str, component: str, capability: str, command: str, arguments: List = None) -> dict:
    """
    SmartThings 디바이스 명령을 실행합니다.
    
    Args:
        device_id: 디바이스 ID
        component: 컴포넌트 ID (일반적으로 "main")
        capability: 기능 ID (예: "switch", "switchLevel")
        command: 명령 ID (예: "on", "off", "setLevel")
        arguments: 명령 인자 (선택 사항)
        
    Returns:
        dict: 명령 실행 결과를 포함한 딕셔너리
        
    Examples:
        >>> execute_device_command("device-id", "main", "switch", "on")
        {'result': {'status': 'success', 'results': [...]}}
        >>> execute_device_command("device-id", "main", "switchLevel", "setLevel", [50])
        {'result': {'status': 'success', 'results': [...]}}
    """
    try:
        if not device_id:
            return {"error": "디바이스 ID를 입력해주세요."}
        if not component:
            return {"error": "컴포넌트 ID를 입력해주세요."}
        if not capability:
            return {"error": "기능 ID를 입력해주세요."}
        if not command:
            return {"error": "명령 ID를 입력해주세요."}
            
        # 디바이스 명령 실행
        result = smartthings_api.execute_device_command(device_id, component, capability, command, arguments)
        
        if "error" in result:
            return {"error": result["error"]}
            
        return {
            "result": {
                "device_id": device_id,
                "component": component,
                "capability": capability,
                "command": command,
                "arguments": arguments,
                "status": "success",
                "results": result.get("results", [])
            }
        }
        
    except Exception as e:
        return {"error": f"디바이스 명령 실행 중 오류 발생: {str(e)}"}


@app.tool()
def get_capability_info(capability_id: str, version: int = 1) -> dict:
    """
    SmartThings 기능 정보를 가져옵니다.
    
    Args:
        capability_id: 기능 ID
        version: 기능 버전 (기본값: 1)
        
    Returns:
        dict: 기능 정보를 포함한 딕셔너리
        
    Examples:
        >>> get_capability_info("switch")
        {'result': {'id': 'switch', 'version': 1, 'attributes': {...}, 'commands': {...}}}
    """
    try:
        if not capability_id:
            return {"error": "기능 ID를 입력해주세요."}
            
        # 기능 정보 가져오기
        capability = smartthings_api.get_capability(capability_id, version)
        
        if not capability:
            return {"error": f"기능을 찾을 수 없습니다: {capability_id} (버전: {version})"}
            
        return {
            "result": {
                "id": capability.id,
                "version": capability.version,
                "name": capability.name,
                "status": capability.status,
                "attributes": capability.attributes,
                "commands": capability.commands
            }
        }
        
    except Exception as e:
        return {"error": f"기능 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_scenes(location_id: str = None) -> dict:
    """
    SmartThings 씬 목록을 가져옵니다.
    
    Args:
        location_id: 위치 ID (선택 사항)
        
    Returns:
        dict: 씬 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_scenes(location_id="location-id")
        {'result': {'location_id': 'location-id', 'scenes': [...]}}
    """
    try:
        # 씬 목록 가져오기
        scenes = smartthings_api.get_scenes(location_id)
        
        # 결과 포맷팅
        formatted_scenes = []
        for scene in scenes:
            formatted_scene = {
                "id": scene.id,
                "name": scene.name,
                "location_id": scene.location_id,
                "icon": scene.icon,
                "color": scene.color,
                "created_date": scene.created_date,
                "last_executed_date": scene.last_executed_date,
                "editable": scene.editable,
                "visible": scene.visible
            }
            formatted_scenes.append(formatted_scene)
            
        return {
            "result": {
                "location_id": location_id,
                "count": len(formatted_scenes),
                "scenes": formatted_scenes
            }
        }
        
    except Exception as e:
        return {"error": f"씬 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def execute_scene(scene_id: str) -> dict:
    """
    SmartThings 씬을 실행합니다.
    
    Args:
        scene_id: 씬 ID
        
    Returns:
        dict: 씬 실행 결과를 포함한 딕셔너리
        
    Examples:
        >>> execute_scene("scene-id")
        {'result': {'scene_id': 'scene-id', 'status': 'success'}}
    """
    try:
        if not scene_id:
            return {"error": "씬 ID를 입력해주세요."}
            
        # 씬 실행
        result = smartthings_api.execute_scene(scene_id)
        
        if "error" in result:
            return {"error": result["error"]}
            
        return {
            "result": {
                "scene_id": scene_id,
                "status": "success"
            }
        }
        
    except Exception as e:
        return {"error": f"씬 실행 중 오류 발생: {str(e)}"}


@app.tool()
def get_rules(location_id: str = None) -> dict:
    """
    SmartThings 규칙 목록을 가져옵니다.
    
    Args:
        location_id: 위치 ID (선택 사항)
        
    Returns:
        dict: 규칙 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_rules(location_id="location-id")
        {'result': {'location_id': 'location-id', 'rules': [...]}}
    """
    try:
        # 규칙 목록 가져오기
        rules = smartthings_api.get_rules(location_id)
        
        # 결과 포맷팅
        formatted_rules = []
        for rule in rules:
            formatted_rule = {
                "id": rule.id,
                "name": rule.name,
                "location_id": rule.location_id,
                "owner_type": rule.owner_type,
                "status": rule.status,
                "created_date": rule.created_date,
                "last_updated_date": rule.last_updated_date
            }
            formatted_rules.append(formatted_rule)
            
        return {
            "result": {
                "location_id": location_id,
                "count": len(formatted_rules),
                "rules": formatted_rules
            }
        }
        
    except Exception as e:
        return {"error": f"규칙 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def execute_rule(rule_id: str) -> dict:
    """
    SmartThings 규칙을 실행합니다.
    
    Args:
        rule_id: 규칙 ID
        
    Returns:
        dict: 규칙 실행 결과를 포함한 딕셔너리
        
    Examples:
        >>> execute_rule("rule-id")
        {'result': {'rule_id': 'rule-id', 'status': 'success'}}
    """
    try:
        if not rule_id:
            return {"error": "규칙 ID를 입력해주세요."}
            
        # 규칙 실행
        result = smartthings_api.execute_rule(rule_id)
        
        if "error" in result:
            return {"error": result["error"]}
            
        return {
            "result": {
                "rule_id": rule_id,
                "status": "success"
            }
        }
        
    except Exception as e:
        return {"error": f"규칙 실행 중 오류 발생: {str(e)}"}


@app.tool()
def get_device_by_name(name: str, location_id: str = None) -> dict:
    """
    이름으로 SmartThings 디바이스를 검색합니다.
    
    Args:
        name: 디바이스 이름 또는 라벨
        location_id: 위치 ID (선택 사항)
        
    Returns:
        dict: 디바이스 정보를 포함한 딕셔너리
        
    Examples:
        >>> get_device_by_name("거실 조명")
        {'result': {'devices': [...]}}
    """
    try:
        if not name:
            return {"error": "디바이스 이름을 입력해주세요."}
            
        # 디바이스 목록 가져오기
        devices = smartthings_api.get_devices(location_id)
        
        # 이름으로 디바이스 검색
        matched_devices = []
        for device in devices:
            if name.lower() in device.name.lower() or name.lower() in device.label.lower():
                # 컴포넌트 포맷팅
                components = []
                for component in device.components:
                    components.append({
                        "id": component.id,
                        "label": component.label,
                        "capabilities": component.capabilities
                    })
                
                matched_devices.append({
                    "id": device.id,
                    "name": device.name,
                    "label": device.label,
                    "type": device.device_type,
                    "type_name": device.device_type_name,
                    "location_id": device.location_id,
                    "room_id": device.room_id,
                    "components": components,
                    "health_state": device.health_state,
                    "created_date": device.created_date
                })
        
        if not matched_devices:
            return {"error": f"'{name}' 이름의 디바이스를 찾을 수 없습니다."}
            
        return {
            "result": {
                "search_name": name,
                "count": len(matched_devices),
                "devices": matched_devices
            }
        }
        
    except Exception as e:
        return {"error": f"디바이스 검색 중 오류 발생: {str(e)}"}


@app.tool()
def get_devices_by_capability(capability: str, location_id: str = None) -> dict:
    """
    기능으로 SmartThings 디바이스를 검색합니다.
    
    Args:
        capability: 기능 ID (예: "switch", "switchLevel", "colorControl")
        location_id: 위치 ID (선택 사항)
        
    Returns:
        dict: 디바이스 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_devices_by_capability("switch")
        {'result': {'capability': 'switch', 'devices': [...]}}
    """
    try:
        if not capability:
            return {"error": "기능 ID를 입력해주세요."}
            
        # 기능으로 디바이스 목록 가져오기
        devices = smartthings_api.get_devices(location_id, capability)
        
        # 결과 포맷팅
        formatted_devices = []
        for device in devices:
            # 컴포넌트 포맷팅
            components = []
            for component in device.components:
                components.append({
                    "id": component.id,
                    "label": component.label,
                    "capabilities": component.capabilities
                })
            
            formatted_devices.append({
                "id": device.id,
                "name": device.name,
                "label": device.label,
                "type": device.device_type,
                "type_name": device.device_type_name,
                "location_id": device.location_id,
                "room_id": device.room_id,
                "components": components,
                "health_state": device.health_state,
                "created_date": device.created_date
            })
            
        return {
            "result": {
                "capability": capability,
                "location_id": location_id,
                "count": len(formatted_devices),
                "devices": formatted_devices
            }
        }
        
    except Exception as e:
        return {"error": f"기능으로 디바이스 검색 중 오류 발생: {str(e)}"}


@app.tool()
def get_devices_by_room(room_id: str, location_id: str) -> dict:
    """
    방에 있는 SmartThings 디바이스 목록을 가져옵니다.
    
    Args:
        room_id: 방 ID
        location_id: 위치 ID
        
    Returns:
        dict: 디바이스 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_devices_by_room("room-id", "location-id")
        {'result': {'room_id': 'room-id', 'devices': [...]}}
    """
    try:
        if not room_id:
            return {"error": "방 ID를 입력해주세요."}
        if not location_id:
            return {"error": "위치 ID를 입력해주세요."}
            
        # 방 정보 가져오기
        room = smartthings_api.get_room(location_id, room_id)
        if not room:
            return {"error": f"방을 찾을 수 없습니다: {room_id}"}
            
        # 위치의 모든 디바이스 가져오기
        all_devices = smartthings_api.get_devices(location_id)
        
        # 방에 있는 디바이스 필터링
        room_devices = []
        for device in all_devices:
            if device.room_id == room_id:
                # 컴포넌트 포맷팅
                components = []
                for component in device.components:
                    components.append({
                        "id": component.id,
                        "label": component.label,
                        "capabilities": component.capabilities
                    })
                
                room_devices.append({
                    "id": device.id,
                    "name": device.name,
                    "label": device.label,
                    "type": device.device_type,
                    "type_name": device.device_type_name,
                    "components": components,
                    "health_state": device.health_state,
                    "created_date": device.created_date
                })
            
        return {
            "result": {
                "location_id": location_id,
                "room_id": room_id,
                "room_name": room.name,
                "count": len(room_devices),
                "devices": room_devices
            }
        }
        
    except Exception as e:
        return {"error": f"방의 디바이스 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def control_switch(device_id: str, command: str) -> dict:
    """
    스위치 기능이 있는 디바이스를 제어합니다.
    
    Args:
        device_id: 디바이스 ID
        command: 명령 (on 또는 off)
        
    Returns:
        dict: 명령 실행 결과를 포함한 딕셔너리
        
    Examples:
        >>> control_switch("device-id", "on")
        {'result': {'device_id': 'device-id', 'command': 'on', 'status': 'success'}}
    """
    try:
        if not device_id:
            return {"error": "디바이스 ID를 입력해주세요."}
        if not command or command.lower() not in ["on", "off"]:
            return {"error": "명령은 'on' 또는 'off'여야 합니다."}
            
        # 디바이스 정보 가져오기
        device = smartthings_api.get_device(device_id)
        if not device:
            return {"error": f"디바이스를 찾을 수 없습니다: {device_id}"}
            
        # 스위치 기능 확인
        has_switch = False
        component_id = "main"
        for component in device.components:
            if "switch" in component.capabilities:
                has_switch = True
                component_id = component.id
                break
                
        if not has_switch:
            return {"error": f"디바이스 '{device.name}'에 스위치 기능이 없습니다."}
            
        # 명령 실행
        result = smartthings_api.execute_device_command(device_id, component_id, "switch", command.lower())
        
        if "error" in result:
            return {"error": result["error"]}
            
        return {
            "result": {
                "device_id": device_id,
                "device_name": device.name,
                "command": command.lower(),
                "status": "success"
            }
        }
        
    except Exception as e:
        return {"error": f"스위치 제어 중 오류 발생: {str(e)}"}


@app.tool()
def control_dimmer(device_id: str, level: int) -> dict:
    """
    디머(밝기 조절) 기능이 있는 디바이스를 제어합니다.
    
    Args:
        device_id: 디바이스 ID
        level: 밝기 레벨 (0-100)
        
    Returns:
        dict: 명령 실행 결과를 포함한 딕셔너리
        
    Examples:
        >>> control_dimmer("device-id", 50)
        {'result': {'device_id': 'device-id', 'level': 50, 'status': 'success'}}
    """
    try:
        if not device_id:
            return {"error": "디바이스 ID를 입력해주세요."}
        if not isinstance(level, int) or level < 0 or level > 100:
            return {"error": "밝기 레벨은 0에서 100 사이의 정수여야 합니다."}
            
        # 디바이스 정보 가져오기
        device = smartthings_api.get_device(device_id)
        if not device:
            return {"error": f"디바이스를 찾을 수 없습니다: {device_id}"}
            
        # 디머 기능 확인
        has_dimmer = False
        component_id = "main"
        for component in device.components:
            if "switchLevel" in component.capabilities:
                has_dimmer = True
                component_id = component.id
                break
                
        if not has_dimmer:
            return {"error": f"디바이스 '{device.name}'에 디머(밝기 조절) 기능이 없습니다."}
            
        # 명령 실행
        result = smartthings_api.execute_device_command(device_id, component_id, "switchLevel", "setLevel", [level])
        
        if "error" in result:
            return {"error": result["error"]}
            
        return {
            "result": {
                "device_id": device_id,
                "device_name": device.name,
                "level": level,
                "status": "success"
            }
        }
        
    except Exception as e:
        return {"error": f"디머 제어 중 오류 발생: {str(e)}"}


@app.tool()
def control_color(device_id: str, hue: int, saturation: int, level: int = None) -> dict:
    """
    색상 조절 기능이 있는 디바이스를 제어합니다.
    
    Args:
        device_id: 디바이스 ID
        hue: 색상 (0-100)
        saturation: 채도 (0-100)
        level: 밝기 레벨 (0-100, 선택 사항)
        
    Returns:
        dict: 명령 실행 결과를 포함한 딕셔너리
        
    Examples:
        >>> control_color("device-id", 50, 80, 70)
        {'result': {'device_id': 'device-id', 'hue': 50, 'saturation': 80, 'level': 70, 'status': 'success'}}
    """
    try:
        if not device_id:
            return {"error": "디바이스 ID를 입력해주세요."}
        if not isinstance(hue, int) or hue < 0 or hue > 100:
            return {"error": "색상(hue)은 0에서 100 사이의 정수여야 합니다."}
        if not isinstance(saturation, int) or saturation < 0 or saturation > 100:
            return {"error": "채도(saturation)는 0에서 100 사이의 정수여야 합니다."}
        if level is not None and (not isinstance(level, int) or level < 0 or level > 100):
            return {"error": "밝기 레벨은 0에서 100 사이의 정수여야 합니다."}
            
        # 디바이스 정보 가져오기
        device = smartthings_api.get_device(device_id)
        if not device:
            return {"error": f"디바이스를 찾을 수 없습니다: {device_id}"}
            
        # 색상 조절 기능 확인
        has_color = False
        component_id = "main"
        for component in device.components:
            if "colorControl" in component.capabilities:
                has_color = True
                component_id = component.id
                break
                
        if not has_color:
            return {"error": f"디바이스 '{device.name}'에 색상 조절 기능이 없습니다."}
            
        # 색상 명령 실행
        result = smartthings_api.execute_device_command(device_id, component_id, "colorControl", "setColor", [{"hue": hue, "saturation": saturation}])
        
        if "error" in result:
            return {"error": result["error"]}
            
        # 밝기 설정 (선택 사항)
        if level is not None:
            # 디머 기능 확인
            has_dimmer = False
            for component in device.components:
                if "switchLevel" in component.capabilities:
                    has_dimmer = True
                    component_id = component.id
                    break
                    
            if has_dimmer:
                level_result = smartthings_api.execute_device_command(device_id, component_id, "switchLevel", "setLevel", [level])
                if "error" in level_result:
                    return {"error": level_result["error"]}
            
        return {
            "result": {
                "device_id": device_id,
                "device_name": device.name,
                "hue": hue,
                "saturation": saturation,
                "level": level,
                "status": "success"
            }
        }
        
    except Exception as e:
        return {"error": f"색상 제어 중 오류 발생: {str(e)}"}


@app.tool()
def control_thermostat(device_id: str, mode: str = None, temperature: float = None) -> dict:
    """
    온도 조절 기능이 있는 디바이스를 제어합니다.
    
    Args:
        device_id: 디바이스 ID
        mode: 모드 (cool, heat, auto, off 중 하나, 선택 사항)
        temperature: 설정 온도 (선택 사항)
        
    Returns:
        dict: 명령 실행 결과를 포함한 딕셔너리
        
    Examples:
        >>> control_thermostat("device-id", "cool", 24.5)
        {'result': {'device_id': 'device-id', 'mode': 'cool', 'temperature': 24.5, 'status': 'success'}}
    """
    try:
        if not device_id:
            return {"error": "디바이스 ID를 입력해주세요."}
        if mode and mode.lower() not in ["cool", "heat", "auto", "off"]:
            return {"error": "모드는 'cool', 'heat', 'auto', 'off' 중 하나여야 합니다."}
            
        # 디바이스 정보 가져오기
        device = smartthings_api.get_device(device_id)
        if not device:
            return {"error": f"디바이스를 찾을 수 없습니다: {device_id}"}
            
        # 온도 조절 기능 확인
        has_thermostat = False
        component_id = "main"
        for component in device.components:
            if "thermostatMode" in component.capabilities:
                has_thermostat = True
                component_id = component.id
                break
                
        if not has_thermostat:
            return {"error": f"디바이스 '{device.name}'에 온도 조절 기능이 없습니다."}
            
        result_info = {
            "device_id": device_id,
            "device_name": device.name,
            "status": "success"
        }
            
        # 모드 설정 (선택 사항)
        if mode:
            mode_result = smartthings_api.execute_device_command(device_id, component_id, "thermostatMode", "setThermostatMode", [mode.lower()])
            if "error" in mode_result:
                return {"error": mode_result["error"]}
            result_info["mode"] = mode.lower()
            
        # 온도 설정 (선택 사항)
        if temperature is not None:
            # 현재 모드 확인
            current_mode = None
            status_list = smartthings_api.get_device_status(device_id)
            for status in status_list:
                if status.capability == "thermostatMode" and status.attribute == "thermostatMode":
                    current_mode = status.value
                    break
                    
            if not current_mode or current_mode == "off":
                return {"error": "온도를 설정하기 전에 온도 조절기 모드를 설정해야 합니다."}
                
            # 모드에 따른 온도 설정 명령 결정
            if current_mode == "cool":
                temp_command = "setCoolingSetpoint"
                capability = "thermostatCoolingSetpoint"
            elif current_mode == "heat":
                temp_command = "setHeatingSetpoint"
                capability = "thermostatHeatingSetpoint"
            else:  # auto
                temp_command = "setThermostatSetpoint"
                capability = "thermostat"
                
            # 온도 설정 명령 실행
            temp_result = smartthings_api.execute_device_command(device_id, component_id, capability, temp_command, [temperature])
            if "error" in temp_result:
                return {"error": temp_result["error"]}
            result_info["temperature"] = temperature
            
        return {
            "result": result_info
        }
        
    except Exception as e:
        return {"error": f"온도 조절기 제어 중 오류 발생: {str(e)}"}


@app.tool()
def get_tool_info() -> dict:
    """
    SmartThings API 도구 정보를 반환합니다.
    
    Returns:
        dict: 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "SmartThings API Tool",
                "description": "SmartThings REST API를 통해 디바이스를 제어하고 다양한 정보를 조회하는 도구",
                "auth_status": "인증됨" if smartthings_api.token else "인증되지 않음",
                "tools": [
                    {"name": "get_locations", "description": "SmartThings 위치 목록을 가져옵니다"},
                    {"name": "get_rooms", "description": "SmartThings 방 목록을 가져옵니다"},
                    {"name": "get_devices", "description": "SmartThings 디바이스 목록을 가져옵니다"},
                    {"name": "get_device_status", "description": "SmartThings 디바이스 상태를 가져옵니다"},
                    {"name": "execute_device_command", "description": "SmartThings 디바이스 명령을 실행합니다"},
                    {"name": "get_capability_info", "description": "SmartThings 기능 정보를 가져옵니다"},
                    {"name": "get_scenes", "description": "SmartThings 씬 목록을 가져옵니다"},
                    {"name": "execute_scene", "description": "SmartThings 씬을 실행합니다"},
                    {"name": "get_rules", "description": "SmartThings 규칙 목록을 가져옵니다"},
                    {"name": "execute_rule", "description": "SmartThings 규칙을 실행합니다"},
                    {"name": "get_device_by_name", "description": "이름으로 SmartThings 디바이스를 검색합니다"},
                    {"name": "get_devices_by_capability", "description": "기능으로 SmartThings 디바이스를 검색합니다"},
                    {"name": "get_devices_by_room", "description": "방에 있는 SmartThings 디바이스 목록을 가져옵니다"},
                    {"name": "control_switch", "description": "스위치 기능이 있는 디바이스를 제어합니다"},
                    {"name": "control_dimmer", "description": "디머(밝기 조절) 기능이 있는 디바이스를 제어합니다"},
                    {"name": "control_color", "description": "색상 조절 기능이 있는 디바이스를 제어합니다"},
                    {"name": "control_thermostat", "description": "온도 조절 기능이 있는 디바이스를 제어합니다"}
                ],
                "usage_examples": [
                    {"command": "get_locations()", "description": "모든 위치 목록 가져오기"},
                    {"command": "get_devices(location_id='location-id')", "description": "특정 위치의 모든 디바이스 가져오기"},
                    {"command": "get_device_status('device-id')", "description": "디바이스 상태 가져오기"},
                    {"command": "control_switch('device-id', 'on')", "description": "스위치 켜기"},
                    {"command": "execute_scene('scene-id')", "description": "씬 실행하기"}
                ],
                "authentication": {
                    "required": True,
                    "method": "Bearer Token",
                    "environment_variables": [
                        "SMARTTHINGS_API_TOKEN - SmartThings API 토큰"
                    ]
                },
                "common_capabilities": [
                    "switch - 스위치 기능 (on/off)",
                    "switchLevel - 밝기 조절 기능",
                    "colorControl - 색상 조절 기능",
                    "thermostatMode - 온도 조절기 모드 기능",
                    "thermostatCoolingSetpoint - 냉방 온도 설정 기능",
                    "thermostatHeatingSetpoint - 난방 온도 설정 기능",
                    "motionSensor - 동작 감지 센서",
                    "contactSensor - 접촉 센서",
                    "temperatureMeasurement - 온도 측정 센서",
                    "illuminanceMeasurement - 조도 측정 센서",
                    "battery - 배터리 상태"
                ]
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
        logger.error("smartthings_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise