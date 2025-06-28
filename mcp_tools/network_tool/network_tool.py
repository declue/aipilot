#!/usr/bin/env python3
"""
Network Diagnostic MCP Server
다양한 네트워크 상황 진단을 도와주는 도구를 제공합니다.
DNS 조회, TCP 통신 테스트, 현재 IP 조회, 핑 테스트, 트레이스라우트, 포트 스캔 등의 기능을 포함합니다.
"""

import logging
import os
import sys
import time
import json
import socket
import ssl
import subprocess
import platform
import ipaddress
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import re
import urllib.request
import urllib.error
import requests
from mcp.server.fastmcp import FastMCP

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 network_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "network_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("NETWORK_TOOL_LOG_LEVEL", "WARNING").upper()
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
    logger.info("Network Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="Network Diagnostic Server",
    description="A server for network diagnostic operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
DEFAULT_TIMEOUT = 5  # 초
DEFAULT_PING_COUNT = 4
DEFAULT_TRACEROUTE_MAX_HOPS = 30
DEFAULT_PORT_SCAN_TIMEOUT = 1  # 초
DEFAULT_HTTP_TIMEOUT = 10  # 초
COMMON_PORTS = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    465: "SMTPS",
    587: "SMTP (Submission)",
    993: "IMAPS",
    995: "POP3S",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    8080: "HTTP Alternate",
    8443: "HTTPS Alternate"
}


@dataclass
class DNSResult:
    """DNS 조회 결과를 담는 데이터 클래스"""
    hostname: str
    ip_addresses: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    error: str = ""


@dataclass
class TCPConnectionResult:
    """TCP 연결 테스트 결과를 담는 데이터 클래스"""
    host: str
    port: int
    success: bool
    response_time: float = 0.0
    error: str = ""


@dataclass
class IPAddressInfo:
    """IP 주소 정보를 담는 데이터 클래스"""
    local_ip: str = ""
    public_ip: str = ""
    hostname: str = ""
    error: str = ""


@dataclass
class PingResult:
    """Ping 테스트 결과를 담는 데이터 클래스"""
    host: str
    success: bool
    min_time: float = 0.0
    avg_time: float = 0.0
    max_time: float = 0.0
    packet_loss: float = 0.0
    packets_sent: int = 0
    packets_received: int = 0
    raw_output: str = ""
    error: str = ""


@dataclass
class TracerouteHop:
    """Traceroute 홉 정보를 담는 데이터 클래스"""
    hop_number: int
    hostname: str = ""
    ip_address: str = ""
    rtt1: float = 0.0
    rtt2: float = 0.0
    rtt3: float = 0.0
    error: str = ""


@dataclass
class TracerouteResult:
    """Traceroute 결과를 담는 데이터 클래스"""
    host: str
    hops: List[TracerouteHop] = field(default_factory=list)
    raw_output: str = ""
    error: str = ""


@dataclass
class NetworkInterface:
    """네트워크 인터페이스 정보를 담는 데이터 클래스"""
    name: str
    ip_address: str = ""
    netmask: str = ""
    mac_address: str = ""
    is_up: bool = False
    is_loopback: bool = False
    mtu: int = 0


@dataclass
class PortScanResult:
    """포트 스캔 결과를 담는 데이터 클래스"""
    host: str
    open_ports: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""


@dataclass
class HTTPRequestResult:
    """HTTP 요청 결과를 담는 데이터 클래스"""
    url: str
    status_code: int = 0
    response_time: float = 0.0
    headers: Dict[str, str] = field(default_factory=dict)
    content_length: int = 0
    content_type: str = ""
    server: str = ""
    error: str = ""


@dataclass
class SSLCertificateInfo:
    """SSL 인증서 정보를 담는 데이터 클래스"""
    host: str
    port: int = 443
    issued_to: str = ""
    issued_by: str = ""
    valid_from: str = ""
    valid_until: str = ""
    serial_number: str = ""
    version: str = ""
    signature_algorithm: str = ""
    days_remaining: int = 0
    is_valid: bool = False
    error: str = ""


class NetworkDiagnosticService:
    """네트워크 진단 서비스 클래스"""

    def __init__(self):
        """네트워크 진단 서비스 초기화"""
        self.is_windows = platform.system().lower() == "windows"
        self.is_mac = platform.system().lower() == "darwin"
        self.is_linux = platform.system().lower() == "linux"

    def dns_lookup(self, hostname: str) -> DNSResult:
        """
        DNS 조회를 수행합니다.
        
        Args:
            hostname: 조회할 호스트 이름
            
        Returns:
            DNSResult: DNS 조회 결과
        """
        try:
            # getaddrinfo를 사용하여 IP 주소 조회
            addrinfo = socket.getaddrinfo(hostname, None)
            
            # 중복 제거를 위한 집합
            ip_addresses = set()
            
            # IP 주소 추출
            for info in addrinfo:
                ip_addresses.add(info[4][0])
            
            # gethostbyname_ex를 사용하여 별칭 조회
            try:
                _, aliases, ips = socket.gethostbyname_ex(hostname)
            except socket.gaierror:
                aliases = []
                ips = list(ip_addresses)
            
            # 결과 반환
            return DNSResult(
                hostname=hostname,
                ip_addresses=list(ip_addresses),
                aliases=aliases
            )
            
        except socket.gaierror as e:
            logger.error(f"DNS 조회 중 오류 발생: {e}")
            return DNSResult(
                hostname=hostname,
                error=f"DNS 조회 실패: {str(e)}"
            )
        except Exception as e:
            logger.error(f"DNS 조회 중 예외 발생: {e}")
            return DNSResult(
                hostname=hostname,
                error=f"DNS 조회 중 오류 발생: {str(e)}"
            )

    def reverse_dns_lookup(self, ip_address: str) -> DNSResult:
        """
        역방향 DNS 조회를 수행합니다.
        
        Args:
            ip_address: 조회할 IP 주소
            
        Returns:
            DNSResult: 역방향 DNS 조회 결과
        """
        try:
            # IP 주소 유효성 검사
            ipaddress.ip_address(ip_address)
            
            # 역방향 DNS 조회
            hostname, _, _ = socket.gethostbyaddr(ip_address)
            
            return DNSResult(
                hostname=hostname,
                ip_addresses=[ip_address]
            )
            
        except ValueError as e:
            logger.error(f"잘못된 IP 주소 형식: {e}")
            return DNSResult(
                hostname="",
                ip_addresses=[ip_address],
                error=f"잘못된 IP 주소 형식: {str(e)}"
            )
        except socket.herror as e:
            logger.error(f"역방향 DNS 조회 중 오류 발생: {e}")
            return DNSResult(
                hostname="",
                ip_addresses=[ip_address],
                error=f"역방향 DNS 조회 실패: {str(e)}"
            )
        except Exception as e:
            logger.error(f"역방향 DNS 조회 중 예외 발생: {e}")
            return DNSResult(
                hostname="",
                ip_addresses=[ip_address],
                error=f"역방향 DNS 조회 중 오류 발생: {str(e)}"
            )

    def test_tcp_connection(self, host: str, port: int, timeout: int = DEFAULT_TIMEOUT) -> TCPConnectionResult:
        """
        TCP 연결 테스트를 수행합니다.
        
        Args:
            host: 연결할 호스트
            port: 연결할 포트
            timeout: 연결 타임아웃 (초)
            
        Returns:
            TCPConnectionResult: TCP 연결 테스트 결과
        """
        try:
            # 소켓 생성
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            # 연결 시간 측정
            start_time = time.time()
            sock.connect((host, port))
            end_time = time.time()
            
            # 연결 성공
            response_time = (end_time - start_time) * 1000  # 밀리초 단위
            sock.close()
            
            return TCPConnectionResult(
                host=host,
                port=port,
                success=True,
                response_time=response_time
            )
            
        except socket.timeout:
            logger.error(f"TCP 연결 타임아웃: {host}:{port}")
            return TCPConnectionResult(
                host=host,
                port=port,
                success=False,
                error=f"연결 타임아웃 ({timeout}초)"
            )
        except socket.gaierror as e:
            logger.error(f"TCP 연결 중 DNS 오류 발생: {e}")
            return TCPConnectionResult(
                host=host,
                port=port,
                success=False,
                error=f"DNS 조회 실패: {str(e)}"
            )
        except ConnectionRefusedError:
            logger.error(f"TCP 연결 거부됨: {host}:{port}")
            return TCPConnectionResult(
                host=host,
                port=port,
                success=False,
                error="연결이 거부되었습니다"
            )
        except Exception as e:
            logger.error(f"TCP 연결 중 예외 발생: {e}")
            return TCPConnectionResult(
                host=host,
                port=port,
                success=False,
                error=f"연결 중 오류 발생: {str(e)}"
            )

    def get_ip_address_info(self) -> IPAddressInfo:
        """
        로컬 및 공인 IP 주소 정보를 가져옵니다.
        
        Returns:
            IPAddressInfo: IP 주소 정보
        """
        result = IPAddressInfo()
        
        try:
            # 로컬 호스트 이름
            result.hostname = socket.gethostname()
            
            # 로컬 IP 주소 (외부 연결용)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # 실제로 연결하지 않고 주소 정보만 가져옴
                s.connect(("8.8.8.8", 80))
                result.local_ip = s.getsockname()[0]
            except Exception as e:
                logger.error(f"로컬 IP 주소 가져오기 실패: {e}")
                # 대체 방법으로 시도
                result.local_ip = socket.gethostbyname(result.hostname)
            finally:
                s.close()
            
            # 공인 IP 주소
            try:
                response = requests.get("https://api.ipify.org", timeout=DEFAULT_TIMEOUT)
                if response.status_code == 200:
                    result.public_ip = response.text.strip()
                else:
                    # 대체 서비스 시도
                    response = requests.get("https://ifconfig.me", timeout=DEFAULT_TIMEOUT)
                    if response.status_code == 200:
                        result.public_ip = response.text.strip()
            except Exception as e:
                logger.error(f"공인 IP 주소 가져오기 실패: {e}")
                result.error = f"공인 IP 주소를 가져오는 중 오류 발생: {str(e)}"
            
            return result
            
        except Exception as e:
            logger.error(f"IP 주소 정보 가져오기 중 예외 발생: {e}")
            result.error = f"IP 주소 정보를 가져오는 중 오류 발생: {str(e)}"
            return result

    def ping(self, host: str, count: int = DEFAULT_PING_COUNT) -> PingResult:
        """
        Ping 테스트를 수행합니다.
        
        Args:
            host: Ping을 보낼 호스트
            count: Ping 패킷 수
            
        Returns:
            PingResult: Ping 테스트 결과
        """
        result = PingResult(host=host, success=False)
        
        try:
            # 운영체제별 ping 명령 구성
            if self.is_windows:
                cmd = ["ping", "-n", str(count), host]
            else:  # macOS 또는 Linux
                cmd = ["ping", "-c", str(count), host]
            
            # ping 명령 실행
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            # 결과 저장
            result.raw_output = stdout
            
            # 성공 여부 확인
            if process.returncode == 0:
                result.success = True
                result.packets_sent = count
                
                # 운영체제별 출력 파싱
                if self.is_windows:
                    # Windows 출력 파싱
                    loss_match = re.search(r"(\d+)% loss", stdout)
                    if loss_match:
                        result.packet_loss = float(loss_match.group(1))
                        result.packets_received = int(count * (1 - result.packet_loss / 100))
                    
                    time_match = re.search(r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms", stdout)
                    if time_match:
                        result.min_time = float(time_match.group(1))
                        result.max_time = float(time_match.group(2))
                        result.avg_time = float(time_match.group(3))
                else:
                    # macOS/Linux 출력 파싱
                    loss_match = re.search(r"(\d+)% packet loss", stdout)
                    if loss_match:
                        result.packet_loss = float(loss_match.group(1))
                        result.packets_received = int(count * (1 - result.packet_loss / 100))
                    
                    time_match = re.search(r"min/avg/max/(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)", stdout)
                    if time_match:
                        result.min_time = float(time_match.group(1))
                        result.avg_time = float(time_match.group(2))
                        result.max_time = float(time_match.group(3))
            else:
                result.error = f"Ping 실패 (반환 코드: {process.returncode}): {stderr}"
            
            return result
            
        except Exception as e:
            logger.error(f"Ping 테스트 중 예외 발생: {e}")
            result.error = f"Ping 테스트 중 오류 발생: {str(e)}"
            return result

    def traceroute(self, host: str, max_hops: int = DEFAULT_TRACEROUTE_MAX_HOPS) -> TracerouteResult:
        """
        Traceroute 테스트를 수행합니다.
        
        Args:
            host: Traceroute를 수행할 호스트
            max_hops: 최대 홉 수
            
        Returns:
            TracerouteResult: Traceroute 테스트 결과
        """
        result = TracerouteResult(host=host)
        
        try:
            # 운영체제별 traceroute 명령 구성
            if self.is_windows:
                cmd = ["tracert", "-d", "-h", str(max_hops), host]
            else:  # macOS 또는 Linux
                cmd = ["traceroute", "-m", str(max_hops), host]
            
            # traceroute 명령 실행
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            # 결과 저장
            result.raw_output = stdout
            
            # 오류 확인
            if process.returncode != 0 and stderr:
                result.error = f"Traceroute 실패 (반환 코드: {process.returncode}): {stderr}"
                return result
            
            # 운영체제별 출력 파싱
            lines = stdout.splitlines()
            hop_pattern = None
            
            if self.is_windows:
                # Windows tracert 출력 파싱
                hop_pattern = re.compile(r"^\s*(\d+)\s+(?:(<?\d+)\s+ms\s+)?(?:(<?\d+)\s+ms\s+)?(?:(<?\d+)\s+ms\s+)?(.+)$")
                start_line = 4  # 헤더 건너뛰기
            else:
                # macOS/Linux traceroute 출력 파싱
                hop_pattern = re.compile(r"^\s*(\d+)\s+(?:([^ ]+)\s+\(([\d.]+)\)|(\*))(?:\s+(?:([\d.]+)\s+ms|(\*)))?(?:\s+(?:([\d.]+)\s+ms|(\*)))?(?:\s+(?:([\d.]+)\s+ms|(\*)))?")
                start_line = 1  # 헤더 건너뛰기
            
            for i in range(start_line, len(lines)):
                line = lines[i]
                if not line.strip():
                    continue
                
                if self.is_windows:
                    match = hop_pattern.match(line)
                    if match:
                        hop_number = int(match.group(1))
                        rtt1 = float(match.group(2)) if match.group(2) and match.group(2) != "<1" else 0.5
                        rtt2 = float(match.group(3)) if match.group(3) and match.group(3) != "<1" else 0.5
                        rtt3 = float(match.group(4)) if match.group(4) and match.group(4) != "<1" else 0.5
                        
                        # IP 주소와 호스트 이름 추출
                        ip_hostname = match.group(5).strip()
                        if "Request timed out" in ip_hostname or "*" in ip_hostname:
                            ip_address = ""
                            hostname = ""
                        else:
                            ip_match = re.search(r"\[([\d.]+)\]", ip_hostname)
                            if ip_match:
                                ip_address = ip_match.group(1)
                                hostname = ip_hostname.replace(f"[{ip_address}]", "").strip()
                            else:
                                # IP 주소만 있는 경우
                                if re.match(r"^[\d.]+$", ip_hostname):
                                    ip_address = ip_hostname
                                    hostname = ""
                                else:
                                    ip_address = ""
                                    hostname = ip_hostname
                        
                        hop = TracerouteHop(
                            hop_number=hop_number,
                            hostname=hostname,
                            ip_address=ip_address,
                            rtt1=rtt1,
                            rtt2=rtt2,
                            rtt3=rtt3
                        )
                        result.hops.append(hop)
                else:
                    match = hop_pattern.match(line)
                    if match:
                        hop_number = int(match.group(1))
                        
                        # 호스트 이름과 IP 주소 추출
                        hostname = match.group(2) if match.group(2) else ""
                        ip_address = match.group(3) if match.group(3) else ""
                        
                        # 타임아웃된 경우
                        if match.group(4) == "*":
                            hop = TracerouteHop(
                                hop_number=hop_number,
                                error="Request timed out"
                            )
                            result.hops.append(hop)
                            continue
                        
                        # RTT 값 추출
                        rtt1 = float(match.group(5)) if match.group(5) else 0.0
                        rtt2 = float(match.group(7)) if match.group(7) else 0.0
                        rtt3 = float(match.group(9)) if match.group(9) else 0.0
                        
                        hop = TracerouteHop(
                            hop_number=hop_number,
                            hostname=hostname,
                            ip_address=ip_address,
                            rtt1=rtt1,
                            rtt2=rtt2,
                            rtt3=rtt3
                        )
                        result.hops.append(hop)
            
            return result
            
        except Exception as e:
            logger.error(f"Traceroute 테스트 중 예외 발생: {e}")
            result.error = f"Traceroute 테스트 중 오류 발생: {str(e)}"
            return result

    def get_network_interfaces(self) -> List[NetworkInterface]:
        """
        네트워크 인터페이스 정보를 가져옵니다.
        
        Returns:
            List[NetworkInterface]: 네트워크 인터페이스 목록
        """
        interfaces = []
        
        try:
            # 운영체제별 네트워크 인터페이스 정보 가져오기
            if self.is_windows:
                # Windows에서는 ipconfig 명령 사용
                cmd = ["ipconfig", "/all"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, _ = process.communicate()
                
                # 출력 파싱
                sections = re.split(r"\r?\n\r?\n", stdout)
                current_interface = None
                
                for section in sections:
                    if not section.strip():
                        continue
                    
                    # 인터페이스 이름 확인
                    name_match = re.search(r"^([\w\s\-\(\)]+):", section, re.MULTILINE)
                    if name_match:
                        if current_interface:
                            interfaces.append(current_interface)
                        
                        name = name_match.group(1).strip()
                        current_interface = NetworkInterface(name=name)
                        
                        # 상태 확인
                        current_interface.is_up = "Media disconnected" not in section
                        
                        # MAC 주소
                        mac_match = re.search(r"Physical Address[\.\s]*: ([\w\-:]+)", section)
                        if mac_match:
                            current_interface.mac_address = mac_match.group(1)
                        
                        # IP 주소
                        ip_match = re.search(r"IPv4 Address[\.\s]*: ([\d\.]+)", section)
                        if ip_match:
                            current_interface.ip_address = ip_match.group(1)
                        
                        # 서브넷 마스크
                        mask_match = re.search(r"Subnet Mask[\.\s]*: ([\d\.]+)", section)
                        if mask_match:
                            current_interface.netmask = mask_match.group(1)
                
                if current_interface:
                    interfaces.append(current_interface)
                
            else:  # macOS 또는 Linux
                # ifconfig 명령 사용
                try:
                    cmd = ["ifconfig"]
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, _ = process.communicate()
                    
                    # 출력 파싱
                    sections = re.split(r"\n(?=\w)", stdout)
                    
                    for section in sections:
                        if not section.strip():
                            continue
                        
                        # 인터페이스 이름 확인
                        name_match = re.match(r"^(\w+):", section)
                        if name_match:
                            name = name_match.group(1)
                            interface = NetworkInterface(name=name)
                            
                            # 상태 확인
                            interface.is_up = "UP" in section
                            interface.is_loopback = "LOOPBACK" in section
                            
                            # MAC 주소
                            mac_match = re.search(r"ether\s+([\w:]+)", section)
                            if mac_match:
                                interface.mac_address = mac_match.group(1)
                            
                            # IP 주소
                            ip_match = re.search(r"inet\s+([\d\.]+)", section)
                            if ip_match:
                                interface.ip_address = ip_match.group(1)
                            
                            # 서브넷 마스크
                            mask_match = re.search(r"netmask\s+([\w\.]+)", section)
                            if mask_match:
                                netmask = mask_match.group(1)
                                # 16진수 형식인 경우 변환
                                if "0x" in netmask:
                                    try:
                                        netmask_int = int(netmask, 16)
                                        netmask = ".".join([str((netmask_int >> i) & 0xff) for i in [24, 16, 8, 0]])
                                    except ValueError:
                                        pass
                                interface.netmask = netmask
                            
                            # MTU
                            mtu_match = re.search(r"mtu\s+(\d+)", section)
                            if mtu_match:
                                interface.mtu = int(mtu_match.group(1))
                            
                            interfaces.append(interface)
                except FileNotFoundError:
                    # ifconfig가 없는 경우 ip 명령 시도
                    cmd = ["ip", "addr"]
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, _ = process.communicate()
                    
                    # 출력 파싱
                    sections = re.split(r"\n(?=\d+: )", stdout)
                    
                    for section in sections:
                        if not section.strip():
                            continue
                        
                        # 인터페이스 이름 확인
                        name_match = re.match(r"^\d+: (\w+):", section)
                        if name_match:
                            name = name_match.group(1)
                            interface = NetworkInterface(name=name)
                            
                            # 상태 확인
                            interface.is_up = "UP" in section.split("\n")[0]
                            interface.is_loopback = "LOOPBACK" in section.split("\n")[0]
                            
                            # MAC 주소
                            mac_match = re.search(r"link/\w+\s+([\w:]+)", section)
                            if mac_match:
                                interface.mac_address = mac_match.group(1)
                            
                            # IP 주소
                            ip_match = re.search(r"inet\s+([\d\.]+)/(\d+)", section)
                            if ip_match:
                                interface.ip_address = ip_match.group(1)
                                # CIDR 표기를 넷마스크로 변환
                                prefix_len = int(ip_match.group(2))
                                netmask_int = (1 << 32) - (1 << (32 - prefix_len))
                                interface.netmask = ".".join([str((netmask_int >> i) & 0xff) for i in [24, 16, 8, 0]])
                            
                            # MTU
                            mtu_match = re.search(r"mtu\s+(\d+)", section)
                            if mtu_match:
                                interface.mtu = int(mtu_match.group(1))
                            
                            interfaces.append(interface)
            
            return interfaces
            
        except Exception as e:
            logger.error(f"네트워크 인터페이스 정보 가져오기 중 예외 발생: {e}")
            return interfaces

    def scan_ports(self, host: str, ports: List[int] = None, timeout: int = DEFAULT_PORT_SCAN_TIMEOUT) -> PortScanResult:
        """
        포트 스캔을 수행합니다.
        
        Args:
            host: 스캔할 호스트
            ports: 스캔할 포트 목록 (None이면 일반적인 포트 스캔)
            timeout: 연결 타임아웃 (초)
            
        Returns:
            PortScanResult: 포트 스캔 결과
        """
        result = PortScanResult(host=host)
        
        try:
            # 스캔할 포트 목록 설정
            if ports is None:
                ports = list(COMMON_PORTS.keys())
            
            # DNS 조회
            try:
                ip_address = socket.gethostbyname(host)
            except socket.gaierror as e:
                result.error = f"DNS 조회 실패: {str(e)}"
                return result
            
            # 각 포트 스캔
            for port in ports:
                try:
                    # 소켓 생성
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    
                    # 연결 시도
                    start_time = time.time()
                    connection_result = sock.connect_ex((ip_address, port))
                    end_time = time.time()
                    
                    # 연결 성공
                    if connection_result == 0:
                        response_time = (end_time - start_time) * 1000  # 밀리초 단위
                        
                        # 서비스 이름 확인
                        service = COMMON_PORTS.get(port, "Unknown")
                        
                        # 결과 추가
                        result.open_ports.append({
                            "port": port,
                            "service": service,
                            "response_time": response_time
                        })
                    
                    sock.close()
                    
                except Exception as e:
                    logger.error(f"포트 {port} 스캔 중 오류 발생: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"포트 스캔 중 예외 발생: {e}")
            result.error = f"포트 스캔 중 오류 발생: {str(e)}"
            return result

    def http_request(self, url: str, method: str = "GET", timeout: int = DEFAULT_HTTP_TIMEOUT) -> HTTPRequestResult:
        """
        HTTP 요청을 수행합니다.
        
        Args:
            url: 요청할 URL
            method: HTTP 메서드 (GET, HEAD)
            timeout: 요청 타임아웃 (초)
            
        Returns:
            HTTPRequestResult: HTTP 요청 결과
        """
        result = HTTPRequestResult(url=url)
        
        try:
            # URL 유효성 검사
            if not url.startswith(("http://", "https://")):
                url = "http://" + url
                result.url = url
            
            # HTTP 요청 수행
            start_time = time.time()
            
            if method.upper() == "HEAD":
                response = requests.head(url, timeout=timeout, allow_redirects=True)
            else:  # 기본값은 GET
                response = requests.get(url, timeout=timeout, allow_redirects=True)
            
            end_time = time.time()
            
            # 응답 시간 계산
            result.response_time = (end_time - start_time) * 1000  # 밀리초 단위
            
            # 응답 정보 저장
            result.status_code = response.status_code
            result.headers = dict(response.headers)
            result.content_length = int(response.headers.get("Content-Length", 0))
            result.content_type = response.headers.get("Content-Type", "")
            result.server = response.headers.get("Server", "")
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"HTTP 요청 타임아웃: {url}")
            result.error = f"요청 타임아웃 ({timeout}초)"
            return result
        except requests.exceptions.ConnectionError as e:
            logger.error(f"HTTP 연결 오류: {e}")
            result.error = f"연결 오류: {str(e)}"
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP 요청 중 오류 발생: {e}")
            result.error = f"요청 중 오류 발생: {str(e)}"
            return result
        except Exception as e:
            logger.error(f"HTTP 요청 중 예외 발생: {e}")
            result.error = f"요청 중 오류 발생: {str(e)}"
            return result

    def check_ssl_certificate(self, host: str, port: int = 443) -> SSLCertificateInfo:
        """
        SSL 인증서 정보를 확인합니다.
        
        Args:
            host: 확인할 호스트
            port: SSL 포트 (기본값: 443)
            
        Returns:
            SSLCertificateInfo: SSL 인증서 정보
        """
        result = SSLCertificateInfo(host=host, port=port)
        
        try:
            # SSL 컨텍스트 생성
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # SSL 연결
            with socket.create_connection((host, port), timeout=DEFAULT_TIMEOUT) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    # 인증서 가져오기
                    cert = ssock.getpeercert(binary_form=True)
                    x509 = ssl.DER_cert_to_PEM_cert(cert)
                    
                    # 인증서 정보 파싱
                    cert_dict = ssock.getpeercert()
                    
                    # 발급 대상
                    if "subject" in cert_dict:
                        for item in cert_dict["subject"]:
                            for key, value in item:
                                if key == "commonName":
                                    result.issued_to = value
                    
                    # 발급자
                    if "issuer" in cert_dict:
                        for item in cert_dict["issuer"]:
                            for key, value in item:
                                if key == "commonName":
                                    result.issued_by = value
                    
                    # 유효 기간
                    if "notBefore" in cert_dict:
                        result.valid_from = cert_dict["notBefore"]
                    if "notAfter" in cert_dict:
                        result.valid_until = cert_dict["notAfter"]
                    
                    # 시리얼 번호
                    if "serialNumber" in cert_dict:
                        result.serial_number = cert_dict["serialNumber"]
                    
                    # 버전
                    result.version = "Unknown"
                    
                    # 서명 알고리즘
                    result.signature_algorithm = "Unknown"
                    
                    # 남은 일수 계산
                    if result.valid_until:
                        try:
                            # 날짜 형식 파싱 (예: "May 30 00:00:00 2023 GMT")
                            expiry_date = datetime.strptime(result.valid_until, "%b %d %H:%M:%S %Y %Z")
                            now = datetime.now()
                            result.days_remaining = (expiry_date - now).days
                            result.is_valid = result.days_remaining > 0
                        except ValueError:
                            pass
            
            return result
            
        except ssl.SSLError as e:
            logger.error(f"SSL 인증서 확인 중 SSL 오류 발생: {e}")
            result.error = f"SSL 오류: {str(e)}"
            return result
        except socket.gaierror as e:
            logger.error(f"SSL 인증서 확인 중 DNS 오류 발생: {e}")
            result.error = f"DNS 조회 실패: {str(e)}"
            return result
        except socket.timeout:
            logger.error(f"SSL 인증서 확인 중 타임아웃 발생: {host}:{port}")
            result.error = f"연결 타임아웃 ({DEFAULT_TIMEOUT}초)"
            return result
        except ConnectionRefusedError:
            logger.error(f"SSL 인증서 확인 중 연결 거부됨: {host}:{port}")
            result.error = "연결이 거부되었습니다"
            return result
        except Exception as e:
            logger.error(f"SSL 인증서 확인 중 예외 발생: {e}")
            result.error = f"인증서 확인 중 오류 발생: {str(e)}"
            return result


# 싱글톤 인스턴스 생성
network_diagnostic = NetworkDiagnosticService()


@app.tool()
def dns_lookup(hostname: str) -> dict:
    """
    DNS 조회를 수행합니다.
    
    Args:
        hostname: 조회할 호스트 이름
        
    Returns:
        dict: DNS 조회 결과를 포함한 딕셔너리
    """
    try:
        result = network_diagnostic.dns_lookup(hostname)
        return {
            "result": result.__dict__
        }
    except Exception as e:
        logger.error(f"DNS 조회 중 오류 발생: {str(e)}")
        return {"error": f"DNS 조회 중 오류 발생: {str(e)}"}


@app.tool()
def reverse_dns_lookup(ip_address: str) -> dict:
    """
    역방향 DNS 조회를 수행합니다.
    
    Args:
        ip_address: 조회할 IP 주소
        
    Returns:
        dict: 역방향 DNS 조회 결과를 포함한 딕셔너리
    """
    try:
        result = network_diagnostic.reverse_dns_lookup(ip_address)
        return {
            "result": result.__dict__
        }
    except Exception as e:
        logger.error(f"역방향 DNS 조회 중 오류 발생: {str(e)}")
        return {"error": f"역방향 DNS 조회 중 오류 발생: {str(e)}"}


@app.tool()
def test_tcp_connection(host: str, port: int, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    TCP 연결 테스트를 수행합니다.
    
    Args:
        host: 연결할 호스트
        port: 연결할 포트
        timeout: 연결 타임아웃 (초)
        
    Returns:
        dict: TCP 연결 테스트 결과를 포함한 딕셔너리
    """
    try:
        result = network_diagnostic.test_tcp_connection(host, port, timeout)
        return {
            "result": result.__dict__
        }
    except Exception as e:
        logger.error(f"TCP 연결 테스트 중 오류 발생: {str(e)}")
        return {"error": f"TCP 연결 테스트 중 오류 발생: {str(e)}"}


@app.tool()
def get_ip_address_info() -> dict:
    """
    로컬 및 공인 IP 주소 정보를 가져옵니다.
    
    Returns:
        dict: IP 주소 정보를 포함한 딕셔너리
    """
    try:
        result = network_diagnostic.get_ip_address_info()
        return {
            "result": result.__dict__
        }
    except Exception as e:
        logger.error(f"IP 주소 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"IP 주소 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def ping(host: str, count: int = DEFAULT_PING_COUNT) -> dict:
    """
    Ping 테스트를 수행합니다.
    
    Args:
        host: Ping을 보낼 호스트
        count: Ping 패킷 수 (기본값: 4)
        
    Returns:
        dict: Ping 테스트 결과를 포함한 딕셔너리
    """
    try:
        result = network_diagnostic.ping(host, count)
        return {
            "result": result.__dict__
        }
    except Exception as e:
        logger.error(f"Ping 테스트 중 오류 발생: {str(e)}")
        return {"error": f"Ping 테스트 중 오류 발생: {str(e)}"}


@app.tool()
def traceroute(host: str, max_hops: int = DEFAULT_TRACEROUTE_MAX_HOPS) -> dict:
    """
    Traceroute 테스트를 수행합니다.
    
    Args:
        host: Traceroute를 수행할 호스트
        max_hops: 최대 홉 수 (기본값: 30)
        
    Returns:
        dict: Traceroute 테스트 결과를 포함한 딕셔너리
    """
    try:
        result = network_diagnostic.traceroute(host, max_hops)
        return {
            "result": {
                "host": result.host,
                "hops": [hop.__dict__ for hop in result.hops],
                "raw_output": result.raw_output,
                "error": result.error
            }
        }
    except Exception as e:
        logger.error(f"Traceroute 테스트 중 오류 발생: {str(e)}")
        return {"error": f"Traceroute 테스트 중 오류 발생: {str(e)}"}


@app.tool()
def get_network_interfaces() -> dict:
    """
    네트워크 인터페이스 정보를 가져옵니다.
    
    Returns:
        dict: 네트워크 인터페이스 목록을 포함한 딕셔너리
    """
    try:
        interfaces = network_diagnostic.get_network_interfaces()
        return {
            "result": [interface.__dict__ for interface in interfaces]
        }
    except Exception as e:
        logger.error(f"네트워크 인터페이스 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"네트워크 인터페이스 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def scan_ports(host: str, ports: List[int] = None, timeout: int = DEFAULT_PORT_SCAN_TIMEOUT) -> dict:
    """
    포트 스캔을 수행합니다.
    
    Args:
        host: 스캔할 호스트
        ports: 스캔할 포트 목록 (None이면 일반적인 포트 스캔)
        timeout: 연결 타임아웃 (초) (기본값: 1)
        
    Returns:
        dict: 포트 스캔 결과를 포함한 딕셔너리
    """
    try:
        result = network_diagnostic.scan_ports(host, ports, timeout)
        return {
            "result": result.__dict__
        }
    except Exception as e:
        logger.error(f"포트 스캔 중 오류 발생: {str(e)}")
        return {"error": f"포트 스캔 중 오류 발생: {str(e)}"}


@app.tool()
def http_request(url: str, method: str = "GET", timeout: int = DEFAULT_HTTP_TIMEOUT) -> dict:
    """
    HTTP 요청을 수행합니다.
    
    Args:
        url: 요청할 URL
        method: HTTP 메서드 (GET, HEAD) (기본값: GET)
        timeout: 요청 타임아웃 (초) (기본값: 10)
        
    Returns:
        dict: HTTP 요청 결과를 포함한 딕셔너리
    """
    try:
        result = network_diagnostic.http_request(url, method, timeout)
        # 헤더를 직렬화 가능한 형태로 변환
        headers_dict = {k: v for k, v in result.headers.items()} if result.headers else {}
        result_dict = result.__dict__
        result_dict["headers"] = headers_dict
        return {
            "result": result_dict
        }
    except Exception as e:
        logger.error(f"HTTP 요청 중 오류 발생: {str(e)}")
        return {"error": f"HTTP 요청 중 오류 발생: {str(e)}"}


@app.tool()
def check_ssl_certificate(host: str, port: int = 443) -> dict:
    """
    SSL 인증서 정보를 확인합니다.
    
    Args:
        host: 확인할 호스트
        port: SSL 포트 (기본값: 443)
        
    Returns:
        dict: SSL 인증서 정보를 포함한 딕셔너리
    """
    try:
        result = network_diagnostic.check_ssl_certificate(host, port)
        return {
            "result": result.__dict__
        }
    except Exception as e:
        logger.error(f"SSL 인증서 확인 중 오류 발생: {str(e)}")
        return {"error": f"SSL 인증서 확인 중 오류 발생: {str(e)}"}


@app.tool()
def get_tool_info() -> dict:
    """
    네트워크 진단 도구 정보를 반환합니다.
    
    Returns:
        dict: 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "Network Diagnostic Tool",
                "description": "다양한 네트워크 상황 진단을 도와주는 도구",
                "tools": [
                    {"name": "dns_lookup", "description": "DNS 조회를 수행합니다"},
                    {"name": "reverse_dns_lookup", "description": "역방향 DNS 조회를 수행합니다"},
                    {"name": "test_tcp_connection", "description": "TCP 연결 테스트를 수행합니다"},
                    {"name": "get_ip_address_info", "description": "로컬 및 공인 IP 주소 정보를 가져옵니다"},
                    {"name": "ping", "description": "Ping 테스트를 수행합니다"},
                    {"name": "traceroute", "description": "Traceroute 테스트를 수행합니다"},
                    {"name": "get_network_interfaces", "description": "네트워크 인터페이스 정보를 가져옵니다"},
                    {"name": "scan_ports", "description": "포트 스캔을 수행합니다"},
                    {"name": "http_request", "description": "HTTP 요청을 수행합니다"},
                    {"name": "check_ssl_certificate", "description": "SSL 인증서 정보를 확인합니다"}
                ],
                "usage_examples": [
                    {"command": "dns_lookup('example.com')", "description": "도메인 이름에 대한 DNS 조회"},
                    {"command": "get_ip_address_info()", "description": "현재 시스템의 IP 주소 정보 확인"},
                    {"command": "ping('google.com')", "description": "특정 호스트에 대한 Ping 테스트"},
                    {"command": "test_tcp_connection('example.com', 80)", "description": "TCP 연결 테스트"},
                    {"command": "scan_ports('example.com')", "description": "일반적인 포트 스캔 수행"}
                ],
                "platform": platform.system(),
                "python_version": platform.python_version()
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
        logger.error("network_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise