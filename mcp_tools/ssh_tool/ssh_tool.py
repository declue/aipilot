import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, Tuple

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    print("paramiko 라이브러리가 설치되지 않았습니다. 'pip install paramiko'로 설치하세요.")

from mcp.server.fastmcp import FastMCP

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 ssh_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "ssh_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("SSH_TOOL_LOG_LEVEL", "WARNING").upper()
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
    logger.info("SSH Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
    logger.info("운영체제: %s", sys.platform)
    logger.info("paramiko 사용 가능: %s", PARAMIKO_AVAILABLE)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="SSH Command Server",
    description="A server for executing commands on SSH hosts",
    version="1.0.0",
)

TRANSPORT = "stdio"

class AuthMethod(str, Enum):
    """인증 방법"""
    PASSWORD = "password"
    KEY_FILE = "key_file"
    KEY_AGENT = "key_agent"

@dataclass
class SSHConnectionInfo:
    """SSH 연결 정보"""
    host: str
    port: int = 22
    username: str = ""
    password: str = ""
    key_file_path: str = ""
    passphrase: str = ""
    timeout: int = 30
    auth_method: AuthMethod = AuthMethod.PASSWORD

    def validate(self) -> tuple[bool, str]:
        """연결 정보 유효성 검사"""
        if not self.host:
            return False, "호스트 주소가 필요합니다"
        
        if not self.username:
            return False, "사용자 이름이 필요합니다"
        
        if self.port <= 0 or self.port > 65535:
            return False, "포트 번호가 유효하지 않습니다 (1-65535)"
        
        if self.auth_method == AuthMethod.PASSWORD and not self.password:
            return False, "비밀번호가 필요합니다"
        
        if self.auth_method == AuthMethod.KEY_FILE and not self.key_file_path:
            return False, "키 파일 경로가 필요합니다"
        
        if self.timeout <= 0:
            return False, "타임아웃은 0보다 커야 합니다"
        
        return True, ""

class SSHCommandService:
    """SSH 명령 실행 서비스 클래스"""

    def __init__(self):
        """SSHCommandService 초기화"""
        self.logger = logging.getLogger(__name__)
        self._check_dependencies()
        self.ssh_clients = {}  # 연결 캐싱을 위한 딕셔너리

    def _check_dependencies(self):
        """필요한 라이브러리가 설치되어 있는지 확인"""
        if not PARAMIKO_AVAILABLE:
            self.logger.error("paramiko 라이브러리가 설치되지 않았습니다.")

    def _get_connection_key(self, connection_info: SSHConnectionInfo) -> str:
        """연결 정보에 대한 고유 키 생성"""
        return f"{connection_info.username}@{connection_info.host}:{connection_info.port}"

    def _connect(self, connection_info: SSHConnectionInfo) -> Optional[paramiko.SSHClient]:
        """
        SSH 서버에 연결합니다.
        
        Args:
            connection_info (SSHConnectionInfo): SSH 연결 정보
            
        Returns:
            Optional[paramiko.SSHClient]: SSH 클라이언트 객체. 실패 시 None 반환.
        """
        if not PARAMIKO_AVAILABLE:
            self.logger.error("paramiko 라이브러리가 설치되지 않아 SSH 연결을 수행할 수 없습니다.")
            return None
        
        # 연결 정보 유효성 검사
        is_valid, error_msg = connection_info.validate()
        if not is_valid:
            self.logger.error(f"SSH 연결 정보가 유효하지 않습니다: {error_msg}")
            return None
        
        # 연결 키 생성
        connection_key = self._get_connection_key(connection_info)
        
        # 이미 연결된 클라이언트가 있는지 확인
        if connection_key in self.ssh_clients:
            client = self.ssh_clients[connection_key]
            try:
                # 연결 상태 확인
                transport = client.get_transport()
                if transport and transport.is_active():
                    self.logger.info(f"기존 SSH 연결 재사용: {connection_key}")
                    return client
                else:
                    self.logger.info(f"기존 SSH 연결이 비활성 상태입니다. 새로 연결합니다: {connection_key}")
                    # 연결이 끊어진 경우 삭제
                    del self.ssh_clients[connection_key]
            except Exception as e:
                self.logger.error(f"기존 SSH 연결 확인 중 오류 발생: {str(e)}")
                # 오류 발생 시 삭제
                del self.ssh_clients[connection_key]
        
        try:
            self.logger.info(f"SSH 연결 시도: {connection_key}")
            
            # SSH 클라이언트 생성
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 연결 설정
            connect_kwargs = {
                'hostname': connection_info.host,
                'port': connection_info.port,
                'username': connection_info.username,
                'timeout': connection_info.timeout,
                'allow_agent': True,  # SSH 에이전트 허용
                'look_for_keys': True,  # 기본 키 위치 확인
            }
            
            # 인증 설정
            if connection_info.auth_method == AuthMethod.PASSWORD:
                connect_kwargs['password'] = connection_info.password
                # 키 기반 인증 비활성화 (비밀번호만 사용)
                connect_kwargs['allow_agent'] = False
                connect_kwargs['look_for_keys'] = False
                self.logger.info(f"비밀번호 인증 사용 (키 인증 비활성화)")
            elif connection_info.auth_method == AuthMethod.KEY_FILE:
                connect_kwargs['key_filename'] = connection_info.key_file_path
                if connection_info.passphrase:
                    connect_kwargs['passphrase'] = connection_info.passphrase
                self.logger.info(f"키 파일 인증 사용: {connection_info.key_file_path}")
            
            # 연결 시도
            client.connect(**connect_kwargs)
            
            # 연결 성공 시 캐시에 저장
            self.ssh_clients[connection_key] = client
            
            self.logger.info(f"SSH 연결 성공: {connection_key}")
            return client
            
        except Exception as e:
            self.logger.error(f"SSH 연결 실패: {str(e)}")
            return None

    def execute_command(self, connection_info: SSHConnectionInfo, command: str) -> Dict[str, Any]:
        """
        SSH 서버에서 명령을 실행합니다.
        
        Args:
            connection_info (SSHConnectionInfo): SSH 연결 정보
            command (str): 실행할 명령어
            
        Returns:
            Dict[str, Any]: 명령 실행 결과
        """
        if not PARAMIKO_AVAILABLE:
            return {
                "success": False,
                "error": "paramiko 라이브러리가 설치되지 않아 SSH 명령을 실행할 수 없습니다."
            }
        
        if not command:
            return {
                "success": False,
                "error": "실행할 명령어가 지정되지 않았습니다."
            }
        
        # SSH 연결
        client = self._connect(connection_info)
        if not client:
            return {
                "success": False,
                "error": "SSH 연결에 실패했습니다."
            }
        
        try:
            self.logger.info(f"명령 실행: {command}")
            
            # 명령 실행
            stdin, stdout, stderr = client.exec_command(command)
            
            # 결과 읽기
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            exit_status = stdout.channel.recv_exit_status()
            
            self.logger.info(f"명령 실행 완료. 종료 코드: {exit_status}")
            
            return {
                "success": exit_status == 0,
                "exit_status": exit_status,
                "stdout": stdout_data,
                "stderr": stderr_data,
                "command": command,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"명령 실행 중 오류 발생: {str(e)}")
            return {
                "success": False,
                "error": f"명령 실행 중 오류 발생: {str(e)}",
                "command": command,
                "timestamp": datetime.now().isoformat()
            }

    def close_connection(self, connection_info: SSHConnectionInfo) -> bool:
        """
        SSH 연결을 닫습니다.
        
        Args:
            connection_info (SSHConnectionInfo): SSH 연결 정보
            
        Returns:
            bool: 성공 여부
        """
        connection_key = self._get_connection_key(connection_info)
        
        if connection_key in self.ssh_clients:
            try:
                client = self.ssh_clients[connection_key]
                client.close()
                del self.ssh_clients[connection_key]
                self.logger.info(f"SSH 연결 닫기 성공: {connection_key}")
                return True
            except Exception as e:
                self.logger.error(f"SSH 연결 닫기 중 오류 발생: {str(e)}")
                return False
        else:
            self.logger.warning(f"닫을 SSH 연결을 찾을 수 없습니다: {connection_key}")
            return False

    def close_all_connections(self) -> bool:
        """
        모든 SSH 연결을 닫습니다.
        
        Returns:
            bool: 성공 여부
        """
        try:
            for key, client in list(self.ssh_clients.items()):
                try:
                    client.close()
                    self.logger.info(f"SSH 연결 닫기 성공: {key}")
                except Exception as e:
                    self.logger.error(f"SSH 연결 닫기 중 오류 발생: {key}, {str(e)}")
            
            self.ssh_clients.clear()
            return True
        except Exception as e:
            self.logger.error(f"모든 SSH 연결 닫기 중 오류 발생: {str(e)}")
            return False

# 전역 서비스 인스턴스
_ssh_command_service = None

def _get_service() -> SSHCommandService:
    """
    SSHCommandService 인스턴스를 가져옵니다.
    
    Returns:
        SSHCommandService: 서비스 인스턴스
    """
    global _ssh_command_service
    if _ssh_command_service is None:
        _ssh_command_service = SSHCommandService()
    return _ssh_command_service

@app.tool()
def execute_command(
    host: str,
    command: str,
    username: str = "",
    password: str = "",
    port: int = 22,
    key_file_path: str = "",
    passphrase: str = "",
    timeout: int = 30,
    auth_method: str = "password"
) -> dict:
    """
    SSH 서버에서 명령을 실행합니다.
    
    Args:
        host (str): SSH 서버 호스트
        command (str): 실행할 명령어
        username (str, optional): SSH 사용자 이름
        password (str, optional): SSH 비밀번호 (auth_method가 'password'인 경우)
        port (int, optional): SSH 포트 (기본값: 22)
        key_file_path (str, optional): SSH 키 파일 경로 (auth_method가 'key_file'인 경우)
        passphrase (str, optional): SSH 키 파일 암호 (필요한 경우)
        timeout (int, optional): 연결 타임아웃 (초) (기본값: 30)
        auth_method (str, optional): 인증 방법 ('password', 'key_file', 'key_agent') (기본값: 'password')
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> execute_command("example.com", "ls -la", username="user", password="pass")
        {'result': {'success': True, 'exit_status': 0, 'stdout': '...', 'stderr': '', 'command': 'ls -la'}}
    """
    try:
        if not PARAMIKO_AVAILABLE:
            return {"error": "paramiko 라이브러리가 설치되지 않아 SSH 명령을 실행할 수 없습니다."}
        
        # 인증 방법 확인
        try:
            auth_method_enum = AuthMethod(auth_method)
        except ValueError:
            return {"error": f"유효하지 않은 인증 방법: {auth_method}. 'password', 'key_file', 'key_agent' 중 하나여야 합니다."}
        
        # 연결 정보 생성
        connection_info = SSHConnectionInfo(
            host=host,
            port=port,
            username=username,
            password=password,
            key_file_path=key_file_path,
            passphrase=passphrase,
            timeout=timeout,
            auth_method=auth_method_enum
        )
        
        # 연결 정보 유효성 검사
        is_valid, error_msg = connection_info.validate()
        if not is_valid:
            return {"error": f"SSH 연결 정보가 유효하지 않습니다: {error_msg}"}
        
        # 명령 실행
        result = _get_service().execute_command(connection_info, command)
        
        return {
            "result": result
        }
    except Exception as e:
        return {"error": f"SSH 명령 실행 중 오류 발생: {str(e)}"}

@app.tool()
def close_connection(
    host: str,
    username: str = "",
    port: int = 22
) -> dict:
    """
    SSH 연결을 닫습니다.
    
    Args:
        host (str): SSH 서버 호스트
        username (str, optional): SSH 사용자 이름
        port (int, optional): SSH 포트 (기본값: 22)
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> close_connection("example.com", username="user")
        {'result': {'action': 'close_connection', 'success': True}}
    """
    try:
        if not PARAMIKO_AVAILABLE:
            return {"error": "paramiko 라이브러리가 설치되지 않아 SSH 연결을 닫을 수 없습니다."}
        
        # 연결 정보 생성 (최소한의 정보만 필요)
        connection_info = SSHConnectionInfo(
            host=host,
            port=port,
            username=username
        )
        
        # 연결 닫기
        success = _get_service().close_connection(connection_info)
        
        return {
            "result": {
                "action": "close_connection",
                "host": host,
                "port": port,
                "username": username,
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"SSH 연결 닫기 중 오류 발생: {str(e)}"}

@app.tool()
def close_all_connections() -> dict:
    """
    모든 SSH 연결을 닫습니다.
    
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> close_all_connections()
        {'result': {'action': 'close_all_connections', 'success': True}}
    """
    try:
        if not PARAMIKO_AVAILABLE:
            return {"error": "paramiko 라이브러리가 설치되지 않아 SSH 연결을 닫을 수 없습니다."}
        
        # 모든 연결 닫기
        success = _get_service().close_all_connections()
        
        return {
            "result": {
                "action": "close_all_connections",
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"모든 SSH 연결 닫기 중 오류 발생: {str(e)}"}

@app.tool()
def get_tool_info() -> dict:
    """
    SSH 명령 도구 정보를 반환합니다.
    
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> get_tool_info()
        {'result': {'name': 'ssh_tool', 'description': 'SSH 명령 실행 기능을 제공하는 도구', ...}}
    """
    try:
        tool_info = {
            "name": "ssh_tool",
            "description": "SSH 명령 실행 기능을 제공하는 도구",
            "version": "1.0.0",
            "author": "DS Pilot",
            "functions": [
                {
                    "name": "execute_command",
                    "description": "SSH 서버에서 명령을 실행합니다.",
                    "parameters": [
                        {
                            "name": "host",
                            "type": "str",
                            "description": "SSH 서버 호스트",
                            "required": True
                        },
                        {
                            "name": "command",
                            "type": "str",
                            "description": "실행할 명령어",
                            "required": True
                        },
                        {
                            "name": "username",
                            "type": "str",
                            "description": "SSH 사용자 이름",
                            "required": False,
                            "default": ""
                        },
                        {
                            "name": "password",
                            "type": "str",
                            "description": "SSH 비밀번호 (auth_method가 'password'인 경우)",
                            "required": False,
                            "default": ""
                        },
                        {
                            "name": "port",
                            "type": "int",
                            "description": "SSH 포트",
                            "required": False,
                            "default": 22
                        },
                        {
                            "name": "key_file_path",
                            "type": "str",
                            "description": "SSH 키 파일 경로 (auth_method가 'key_file'인 경우)",
                            "required": False,
                            "default": ""
                        },
                        {
                            "name": "passphrase",
                            "type": "str",
                            "description": "SSH 키 파일 암호 (필요한 경우)",
                            "required": False,
                            "default": ""
                        },
                        {
                            "name": "timeout",
                            "type": "int",
                            "description": "연결 타임아웃 (초)",
                            "required": False,
                            "default": 30
                        },
                        {
                            "name": "auth_method",
                            "type": "str",
                            "description": "인증 방법 ('password', 'key_file', 'key_agent')",
                            "required": False,
                            "default": "password"
                        }
                    ],
                    "returns": {
                        "type": "dict",
                        "description": "결과를 포함한 딕셔너리"
                    }
                },
                {
                    "name": "close_connection",
                    "description": "SSH 연결을 닫습니다.",
                    "parameters": [
                        {
                            "name": "host",
                            "type": "str",
                            "description": "SSH 서버 호스트",
                            "required": True
                        },
                        {
                            "name": "username",
                            "type": "str",
                            "description": "SSH 사용자 이름",
                            "required": False,
                            "default": ""
                        },
                        {
                            "name": "port",
                            "type": "int",
                            "description": "SSH 포트",
                            "required": False,
                            "default": 22
                        }
                    ],
                    "returns": {
                        "type": "dict",
                        "description": "결과를 포함한 딕셔너리"
                    }
                },
                {
                    "name": "close_all_connections",
                    "description": "모든 SSH 연결을 닫습니다.",
                    "parameters": [],
                    "returns": {
                        "type": "dict",
                        "description": "결과를 포함한 딕셔너리"
                    }
                }
            ],
            "dependencies": [
                {
                    "name": "paramiko",
                    "required": True,
                    "installed": PARAMIKO_AVAILABLE
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
        logger.error("ssh_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise