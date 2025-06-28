"""
SSH 연결 모델
"""
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any
from enum import Enum


class ConnectionStatus(Enum):
    """연결 상태"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AuthMethod(Enum):
    """인증 방법"""
    PASSWORD = "password"
    KEY_FILE = "key_file"
    KEY_AGENT = "key_agent"


@dataclass
class SSHConnection:
    """SSH 연결 정보"""
    
    # 기본 연결 정보
    name: str
    host: str
    port: int = 22
    username: str = ""
    
    # 인증 정보
    auth_method: AuthMethod = AuthMethod.PASSWORD
    password: str = ""
    key_file_path: str = ""
    passphrase: str = ""
    
    # 연결 옵션
    timeout: int = 30
    keep_alive: bool = True
    compression: bool = False
    
    # 터미널 설정
    terminal_type: str = "xterm-256color"
    encoding: str = "utf-8"
    
    # 고급 옵션
    proxy_host: str = ""
    proxy_port: int = 0
    proxy_username: str = ""
    proxy_password: str = ""
    
    # 실행시 설정
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ConnectionStatus = field(default=ConnectionStatus.DISCONNECTED)
    last_error: str = ""
    
    # 세션 정보
    session_info: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 처리"""
        if not self.name:
            self.name = f"{self.username}@{self.host}"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (설정 저장용)"""
        return {
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'auth_method': self.auth_method.value,
            'key_file_path': self.key_file_path,
            'timeout': self.timeout,
            'keep_alive': self.keep_alive,
            'compression': self.compression,
            'terminal_type': self.terminal_type,
            'encoding': self.encoding,
            'proxy_host': self.proxy_host,
            'proxy_port': self.proxy_port,
            'proxy_username': self.proxy_username,
            # 보안상 password는 저장하지 않음
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SSHConnection':
        """딕셔너리에서 생성 (설정 로드용)"""
        # 기본값 설정
        connection_data = {
            'name': data.get('name', ''),
            'host': data.get('host', ''),
            'port': data.get('port', 22),
            'username': data.get('username', ''),
            'auth_method': AuthMethod(data.get('auth_method', 'password')),
            'key_file_path': data.get('key_file_path', ''),
            'timeout': data.get('timeout', 30),
            'keep_alive': data.get('keep_alive', True),
            'compression': data.get('compression', False),
            'terminal_type': data.get('terminal_type', 'xterm-256color'),
            'encoding': data.get('encoding', 'utf-8'),
            'proxy_host': data.get('proxy_host', ''),
            'proxy_port': data.get('proxy_port', 0),
            'proxy_username': data.get('proxy_username', ''),
        }
        
        return cls(**connection_data)
    
    def validate(self) -> tuple[bool, str]:
        """연결 정보 유효성 검사"""
        if not self.host:
            return False, "호스트 주소가 필요합니다"
        
        if not self.username:
            return False, "사용자 이름이 필요합니다"
        
        if self.port <= 0 or self.port > 65535:
            return False, "포트 번호가 유효하지 않습니다 (1-65535)"
        
        if self.auth_method == AuthMethod.KEY_FILE and not self.key_file_path:
            return False, "키 파일 경로가 필요합니다"
        
        if self.timeout <= 0:
            return False, "타임아웃은 0보다 커야 합니다"
        
        return True, ""
    
    def get_display_name(self) -> str:
        """화면 표시용 이름"""
        if self.name and self.name != f"{self.username}@{self.host}":
            return f"{self.name} ({self.username}@{self.host}:{self.port})"
        else:
            return f"{self.username}@{self.host}:{self.port}"
    
    def get_connection_string(self) -> str:
        """연결 문자열"""
        return f"{self.username}@{self.host}:{self.port}"
