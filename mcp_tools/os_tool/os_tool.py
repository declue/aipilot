import logging
import os
import sys
import platform
import socket
import ssl
import json
import subprocess
import psutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, Tuple

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("psutil 라이브러리가 설치되지 않았습니다. 'pip install psutil'로 설치하세요.")

try:
    import cryptography
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    print("cryptography 라이브러리가 설치되지 않았습니다. 'pip install cryptography'로 설치하세요.")

from mcp.server.fastmcp import FastMCP

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 os_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "os_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("OS_TOOL_LOG_LEVEL", "WARNING").upper()
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
    logger.info("OS Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
    logger.info("운영체제: %s", sys.platform)
    logger.info("psutil 사용 가능: %s", PSUTIL_AVAILABLE)
    logger.info("cryptography 사용 가능: %s", CRYPTOGRAPHY_AVAILABLE)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="System Diagnostic Server",
    description="A server for system diagnostic operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

class SystemDiagnosticService:
    """시스템 진단 기능을 제공하는 서비스 클래스"""

    def __init__(self):
        """SystemDiagnosticService 초기화"""
        self.logger = logging.getLogger(__name__)
        self._check_dependencies()

    def _check_dependencies(self):
        """필요한 라이브러리가 설치되어 있는지 확인"""
        if not PSUTIL_AVAILABLE:
            self.logger.error("psutil 라이브러리가 설치되지 않았습니다.")
        if not CRYPTOGRAPHY_AVAILABLE:
            self.logger.error("cryptography 라이브러리가 설치되지 않았습니다.")

    def get_environment_variables(self) -> Dict[str, str]:
        """
        시스템 환경 변수를 가져옵니다.

        Returns:
            Dict[str, str]: 환경 변수 딕셔너리
        """
        try:
            # 환경 변수 복사
            env_vars = dict(os.environ)
            return env_vars
        except Exception as e:
            self.logger.error(f"환경 변수 가져오기 중 오류 발생: {str(e)}")
            return {}

    def get_cpu_info(self) -> Dict[str, Any]:
        """
        CPU 정보를 가져옵니다.

        Returns:
            Dict[str, Any]: CPU 정보
        """
        try:
            cpu_info = {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "architecture": platform.architecture(),
                "machine": platform.machine(),
                "python_build": platform.python_build(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version()
            }

            if PSUTIL_AVAILABLE:
                # psutil을 사용하여 더 자세한 CPU 정보 가져오기
                cpu_info.update({
                    "physical_cores": psutil.cpu_count(logical=False),
                    "logical_cores": psutil.cpu_count(logical=True),
                    "cpu_percent": psutil.cpu_percent(interval=1, percpu=True),
                    "cpu_freq": {
                        "current": psutil.cpu_freq().current if psutil.cpu_freq() else None,
                        "min": psutil.cpu_freq().min if psutil.cpu_freq() and hasattr(psutil.cpu_freq(), 'min') else None,
                        "max": psutil.cpu_freq().max if psutil.cpu_freq() and hasattr(psutil.cpu_freq(), 'max') else None
                    },
                    "cpu_stats": dict(psutil.cpu_stats()._asdict()),
                    "cpu_times": dict(psutil.cpu_times()._asdict()),
                    "cpu_times_percent": dict(psutil.cpu_times_percent()._asdict())
                })

            return cpu_info
        except Exception as e:
            self.logger.error(f"CPU 정보 가져오기 중 오류 발생: {str(e)}")
            return {"error": str(e)}

    def get_memory_info(self) -> Dict[str, Any]:
        """
        메모리 정보를 가져옵니다.

        Returns:
            Dict[str, Any]: 메모리 정보
        """
        try:
            memory_info = {}

            if PSUTIL_AVAILABLE:
                # 가상 메모리 정보
                virtual_memory = psutil.virtual_memory()
                memory_info["virtual_memory"] = {
                    "total": virtual_memory.total,
                    "available": virtual_memory.available,
                    "used": virtual_memory.used,
                    "free": virtual_memory.free,
                    "percent": virtual_memory.percent
                }

                # 스왑 메모리 정보
                swap_memory = psutil.swap_memory()
                memory_info["swap_memory"] = {
                    "total": swap_memory.total,
                    "used": swap_memory.used,
                    "free": swap_memory.free,
                    "percent": swap_memory.percent
                }

                # 메모리 단위 변환 함수 추가
                memory_info["formatted"] = {
                    "virtual_memory": {
                        "total": self._format_bytes(virtual_memory.total),
                        "available": self._format_bytes(virtual_memory.available),
                        "used": self._format_bytes(virtual_memory.used),
                        "free": self._format_bytes(virtual_memory.free)
                    },
                    "swap_memory": {
                        "total": self._format_bytes(swap_memory.total),
                        "used": self._format_bytes(swap_memory.used),
                        "free": self._format_bytes(swap_memory.free)
                    }
                }

            return memory_info
        except Exception as e:
            self.logger.error(f"메모리 정보 가져오기 중 오류 발생: {str(e)}")
            return {"error": str(e)}

    def get_disk_info(self) -> Dict[str, Any]:
        """
        디스크 정보를 가져옵니다.

        Returns:
            Dict[str, Any]: 디스크 정보
        """
        try:
            disk_info = {}

            if PSUTIL_AVAILABLE:
                # 디스크 파티션 정보
                disk_info["partitions"] = []
                for partition in psutil.disk_partitions():
                    partition_info = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "opts": partition.opts
                    }

                    # 디스크 사용량 정보 (일부 마운트 포인트는 접근 불가능할 수 있음)
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        partition_info["usage"] = {
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": usage.percent,
                            "formatted": {
                                "total": self._format_bytes(usage.total),
                                "used": self._format_bytes(usage.used),
                                "free": self._format_bytes(usage.free)
                            }
                        }
                    except (PermissionError, OSError):
                        partition_info["usage"] = "접근 불가"

                    disk_info["partitions"].append(partition_info)

                # 디스크 I/O 카운터
                disk_io = psutil.disk_io_counters(perdisk=True)
                disk_info["io_counters"] = {}
                for disk_name, counters in disk_io.items():
                    disk_info["io_counters"][disk_name] = dict(counters._asdict())

            return disk_info
        except Exception as e:
            self.logger.error(f"디스크 정보 가져오기 중 오류 발생: {str(e)}")
            return {"error": str(e)}

    def get_network_info(self) -> Dict[str, Any]:
        """
        네트워크 정보를 가져옵니다.

        Returns:
            Dict[str, Any]: 네트워크 정보
        """
        try:
            network_info = {}

            # 호스트 이름
            network_info["hostname"] = socket.gethostname()

            # IP 주소 정보
            try:
                network_info["ip_addresses"] = {
                    "hostname": socket.gethostbyname(socket.gethostname()),
                    "external": self._get_external_ip()
                }
            except:
                network_info["ip_addresses"] = {
                    "hostname": "알 수 없음",
                    "external": "알 수 없음"
                }

            # DNS 서버 정보
            network_info["dns_servers"] = self._get_dns_servers()

            if PSUTIL_AVAILABLE:
                # 네트워크 인터페이스 정보
                network_info["interfaces"] = {}
                for interface_name, addresses in psutil.net_if_addrs().items():
                    network_info["interfaces"][interface_name] = []
                    for address in addresses:
                        addr_info = {
                            "family": str(address.family),
                            "address": address.address,
                            "netmask": address.netmask,
                            "broadcast": address.broadcast,
                            "ptp": address.ptp
                        }
                        network_info["interfaces"][interface_name].append(addr_info)

                # 네트워크 인터페이스 통계
                network_info["interface_stats"] = {}
                for interface_name, stats in psutil.net_if_stats().items():
                    network_info["interface_stats"][interface_name] = dict(stats._asdict())

                # 네트워크 연결 정보
                try:
                    network_info["connections"] = []
                    for conn in psutil.net_connections(kind='inet'):
                        conn_info = {
                            "fd": conn.fd,
                            "family": conn.family,
                            "type": conn.type,
                            "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                            "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                            "status": conn.status,
                            "pid": conn.pid
                        }
                        network_info["connections"].append(conn_info)
                except (psutil.AccessDenied, PermissionError):
                    network_info["connections"] = "권한 부족으로 연결 정보를 가져올 수 없습니다."

            return network_info
        except Exception as e:
            self.logger.error(f"네트워크 정보 가져오기 중 오류 발생: {str(e)}")
            return {"error": str(e)}

    def get_ssl_certificates(self, domain: str = None) -> Dict[str, Any]:
        """
        SSL 인증서 정보를 가져옵니다.

        Args:
            domain (str, optional): 도메인 이름. 지정하면 해당 도메인의 인증서만 가져옵니다.

        Returns:
            Dict[str, Any]: SSL 인증서 정보
        """
        try:
            cert_info = {}

            if domain:
                # 특정 도메인의 인증서 정보 가져오기
                cert_info[domain] = self._get_domain_certificate(domain)
            else:
                # 시스템에 설치된 인증서 정보 가져오기
                cert_info["system_certificates"] = self._get_system_certificates()

            return cert_info
        except Exception as e:
            self.logger.error(f"SSL 인증서 정보 가져오기 중 오류 발생: {str(e)}")
            return {"error": str(e)}

    def _get_domain_certificate(self, domain: str, port: int = 443) -> Dict[str, Any]:
        """
        특정 도메인의 SSL 인증서 정보를 가져옵니다.

        Args:
            domain (str): 도메인 이름
            port (int, optional): 포트 번호. 기본값은 443입니다.

        Returns:
            Dict[str, Any]: 인증서 정보
        """
        try:
            # SSL 컨텍스트 생성
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # 연결 및 인증서 가져오기
            with socket.create_connection((domain, port)) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert_binary = ssock.getpeercert(binary_form=True)
                    cert_dict = ssock.getpeercert()

            # 인증서 정보 파싱
            if CRYPTOGRAPHY_AVAILABLE and cert_binary:
                cert = x509.load_der_x509_certificate(cert_binary, default_backend())
                cert_info = {
                    "subject": dict(cert_dict.get("subject", [])),
                    "issuer": dict(cert_dict.get("issuer", [])),
                    "version": cert.version,
                    "serial_number": cert.serial_number,
                    "not_valid_before": cert.not_valid_before.isoformat(),
                    "not_valid_after": cert.not_valid_after.isoformat(),
                    "has_expired": cert.not_valid_after < datetime.now(),
                    "signature_algorithm": cert.signature_algorithm_oid._name
                }
            else:
                cert_info = {
                    "subject": dict(cert_dict.get("subject", [])),
                    "issuer": dict(cert_dict.get("issuer", [])),
                    "version": cert_dict.get("version", "알 수 없음"),
                    "serial_number": cert_dict.get("serialNumber", "알 수 없음"),
                    "not_valid_before": cert_dict.get("notBefore", "알 수 없음"),
                    "not_valid_after": cert_dict.get("notAfter", "알 수 없음")
                }

            return cert_info
        except Exception as e:
            self.logger.error(f"{domain} 도메인의 인증서 정보 가져오기 중 오류 발생: {str(e)}")
            return {"error": str(e)}

    def _get_system_certificates(self) -> List[Dict[str, Any]]:
        """
        시스템에 설치된 인증서 정보를 가져옵니다.

        Returns:
            List[Dict[str, Any]]: 인증서 정보 목록
        """
        certs = []

        try:
            # 운영체제별 인증서 경로
            if sys.platform == 'win32':
                # Windows - 인증서 저장소 접근은 복잡하므로 간단한 정보만 제공
                certs.append({
                    "info": "Windows 인증서 저장소는 직접 접근이 어렵습니다. certmgr.msc를 실행하여 확인하세요."
                })
            elif sys.platform == 'darwin':
                # macOS - Keychain에서 인증서 정보 가져오기
                try:
                    output = subprocess.check_output(
                        ["security", "find-certificate", "-a", "-p", "/Library/Keychains/System.keychain"],
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                    certs.append({
                        "info": f"macOS 시스템 키체인에서 {output.count('-----BEGIN CERTIFICATE-----')}개의 인증서를 찾았습니다."
                    })
                except subprocess.CalledProcessError:
                    certs.append({
                        "info": "macOS 키체인에서 인증서를 가져올 수 없습니다."
                    })
            else:
                # Linux - /etc/ssl/certs 디렉토리 확인
                ssl_dir = "/etc/ssl/certs"
                if os.path.exists(ssl_dir):
                    cert_files = [f for f in os.listdir(ssl_dir) if os.path.isfile(os.path.join(ssl_dir, f))]
                    certs.append({
                        "info": f"Linux {ssl_dir} 디렉토리에서 {len(cert_files)}개의 인증서 파일을 찾았습니다."
                    })
                else:
                    certs.append({
                        "info": f"Linux {ssl_dir} 디렉토리가 존재하지 않습니다."
                    })
        except Exception as e:
            self.logger.error(f"시스템 인증서 정보 가져오기 중 오류 발생: {str(e)}")
            certs.append({"error": str(e)})

        return certs

    def _get_external_ip(self) -> str:
        """
        외부 IP 주소를 가져옵니다.

        Returns:
            str: 외부 IP 주소
        """
        try:
            # 외부 서비스를 사용하여 IP 주소 확인
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("ifconfig.me", 80))
                s.sendall(b"GET / HTTP/1.1\r\nHost: ifconfig.me\r\n\r\n")
                response = s.recv(4096)
            
            # 응답에서 IP 주소 추출
            ip = response.decode().split("\r\n\r\n")[1].strip()
            return ip
        except:
            try:
                # 대체 서비스 시도
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(("api.ipify.org", 80))
                    s.sendall(b"GET / HTTP/1.1\r\nHost: api.ipify.org\r\n\r\n")
                    response = s.recv(4096)
                
                # 응답에서 IP 주소 추출
                ip = response.decode().split("\r\n\r\n")[1].strip()
                return ip
            except:
                return "알 수 없음"

    def _get_dns_servers(self) -> List[str]:
        """
        DNS 서버 목록을 가져옵니다.

        Returns:
            List[str]: DNS 서버 목록
        """
        dns_servers = []

        try:
            if sys.platform == 'win32':
                # Windows
                output = subprocess.check_output(
                    ["ipconfig", "/all"],
                    stderr=subprocess.STDOUT,
                    text=True
                )
                for line in output.split('\n'):
                    if "DNS Servers" in line or "DNS 서버" in line:
                        dns_server = line.split(':')[-1].strip()
                        if dns_server and dns_server not in dns_servers:
                            dns_servers.append(dns_server)
            elif sys.platform == 'darwin':
                # macOS
                output = subprocess.check_output(
                    ["scutil", "--dns"],
                    stderr=subprocess.STDOUT,
                    text=True
                )
                for line in output.split('\n'):
                    if "nameserver" in line:
                        dns_server = line.split(':')[-1].strip()
                        if dns_server and dns_server not in dns_servers:
                            dns_servers.append(dns_server)
            else:
                # Linux
                if os.path.exists('/etc/resolv.conf'):
                    with open('/etc/resolv.conf', 'r') as f:
                        for line in f:
                            if line.startswith('nameserver'):
                                dns_server = line.split()[1].strip()
                                if dns_server and dns_server not in dns_servers:
                                    dns_servers.append(dns_server)
        except Exception as e:
            self.logger.error(f"DNS 서버 정보 가져오기 중 오류 발생: {str(e)}")

        return dns_servers

    def _format_bytes(self, bytes_value: int) -> str:
        """
        바이트 값을 읽기 쉬운 형식으로 변환합니다.

        Args:
            bytes_value (int): 바이트 값

        Returns:
            str: 변환된 문자열
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"

# 전역 서비스 인스턴스
_system_diagnostic_service = None

def _get_service() -> SystemDiagnosticService:
    """
    SystemDiagnosticService 인스턴스를 가져옵니다.

    Returns:
        SystemDiagnosticService: 서비스 인스턴스
    """
    global _system_diagnostic_service
    if _system_diagnostic_service is None:
        _system_diagnostic_service = SystemDiagnosticService()
    return _system_diagnostic_service

@app.tool()
def get_environment_variables() -> dict:
    """
    시스템 환경 변수를 가져옵니다.

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> get_environment_variables()
        {'result': {'action': 'get_environment_variables', 'variables': {...}, 'count': 50, 'success': True}}
    """
    try:
        env_vars = _get_service().get_environment_variables()

        return {
            "result": {
                "action": "get_environment_variables",
                "variables": env_vars,
                "count": len(env_vars),
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"환경 변수 가져오기 중 오류 발생: {str(e)}"}

@app.tool()
def get_cpu_info() -> dict:
    """
    CPU 정보를 가져옵니다.

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> get_cpu_info()
        {'result': {'action': 'get_cpu_info', 'cpu_info': {...}, 'success': True}}
    """
    try:
        cpu_info = _get_service().get_cpu_info()

        return {
            "result": {
                "action": "get_cpu_info",
                "cpu_info": cpu_info,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"CPU 정보 가져오기 중 오류 발생: {str(e)}"}

@app.tool()
def get_memory_info() -> dict:
    """
    메모리 정보를 가져옵니다.

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> get_memory_info()
        {'result': {'action': 'get_memory_info', 'memory_info': {...}, 'success': True}}
    """
    try:
        memory_info = _get_service().get_memory_info()

        return {
            "result": {
                "action": "get_memory_info",
                "memory_info": memory_info,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"메모리 정보 가져오기 중 오류 발생: {str(e)}"}

@app.tool()
def get_disk_info() -> dict:
    """
    디스크 정보를 가져옵니다.

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> get_disk_info()
        {'result': {'action': 'get_disk_info', 'disk_info': {...}, 'success': True}}
    """
    try:
        disk_info = _get_service().get_disk_info()

        return {
            "result": {
                "action": "get_disk_info",
                "disk_info": disk_info,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"디스크 정보 가져오기 중 오류 발생: {str(e)}"}

@app.tool()
def get_network_info() -> dict:
    """
    네트워크 정보를 가져옵니다.

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> get_network_info()
        {'result': {'action': 'get_network_info', 'network_info': {...}, 'success': True}}
    """
    try:
        network_info = _get_service().get_network_info()

        return {
            "result": {
                "action": "get_network_info",
                "network_info": network_info,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"네트워크 정보 가져오기 중 오류 발생: {str(e)}"}

@app.tool()
def get_ssl_certificates(domain: str = None) -> dict:
    """
    SSL 인증서 정보를 가져옵니다.

    Args:
        domain (str, optional): 도메인 이름. 지정하면 해당 도메인의 인증서만 가져옵니다.

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> get_ssl_certificates("google.com")
        {'result': {'action': 'get_ssl_certificates', 'certificates': {...}, 'success': True}}
    """
    try:
        certificates = _get_service().get_ssl_certificates(domain)

        return {
            "result": {
                "action": "get_ssl_certificates",
                "domain": domain,
                "certificates": certificates,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"SSL 인증서 정보 가져오기 중 오류 발생: {str(e)}"}

@app.tool()
def get_system_info() -> dict:
    """
    시스템 전체 정보를 가져옵니다.

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> get_system_info()
        {'result': {'action': 'get_system_info', 'system_info': {...}, 'success': True}}
    """
    try:
        system_info = {
            "cpu": _get_service().get_cpu_info(),
            "memory": _get_service().get_memory_info(),
            "disk": _get_service().get_disk_info(),
            "network": _get_service().get_network_info(),
            "environment_variables_count": len(_get_service().get_environment_variables())
        }

        return {
            "result": {
                "action": "get_system_info",
                "system_info": system_info,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"시스템 정보 가져오기 중 오류 발생: {str(e)}"}

@app.tool()
def get_tool_info() -> dict:
    """
    시스템 진단 도구 정보를 반환합니다.

    Returns:
        dict: 결과를 포함한 딕셔너리

    Examples:
        >>> get_tool_info()
        {'result': {'name': 'os_tool', 'description': '시스템 진단 기능을 제공하는 도구', ...}}
    """
    try:
        tool_info = {
            "name": "os_tool",
            "description": "시스템 진단 기능을 제공하는 도구",
            "version": "1.0.0",
            "author": "DS Pilot",
            "functions": [
                {
                    "name": "get_environment_variables",
                    "description": "시스템 환경 변수를 가져옵니다."
                },
                {
                    "name": "get_cpu_info",
                    "description": "CPU 정보를 가져옵니다."
                },
                {
                    "name": "get_memory_info",
                    "description": "메모리 정보를 가져옵니다."
                },
                {
                    "name": "get_disk_info",
                    "description": "디스크 정보를 가져옵니다."
                },
                {
                    "name": "get_network_info",
                    "description": "네트워크 정보를 가져옵니다."
                },
                {
                    "name": "get_ssl_certificates",
                    "description": "SSL 인증서 정보를 가져옵니다."
                },
                {
                    "name": "get_system_info",
                    "description": "시스템 전체 정보를 가져옵니다."
                }
            ],
            "dependencies": [
                {
                    "name": "psutil",
                    "required": True,
                    "installed": PSUTIL_AVAILABLE
                },
                {
                    "name": "cryptography",
                    "required": True,
                    "installed": CRYPTOGRAPHY_AVAILABLE
                }
            ]
        }

        return {
            "result": tool_info
        }
    except Exception as e:
        return {"error": f"도구 정보를 가져오는 중 오류 발생: {str(e)}"}

if __name__ == "__main__":
    try:
        logger.info("FastMCP app.run() 호출 시작...")
        app.run(transport=TRANSPORT)
        logger.info("FastMCP app.run() 정상 종료.")
    except Exception as e:
        logger.error("os_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise