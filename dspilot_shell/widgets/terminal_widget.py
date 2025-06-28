"""
SSH 터미널 위젯
"""
import logging
import socket
import time
from typing import Optional

try:
    import paramiko
except ImportError:
    paramiko = None

from PySide6.QtCore import QThread, QTimer, Signal, Slot, Qt, QEvent, QObject
from PySide6.QtGui import QFont, QFontMetrics, QKeyEvent, QTextCursor, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dspilot_shell.models.ssh_connection import SSHConnection, ConnectionStatus
from dspilot_shell.ansi_parser import AnsiParser


class SSHTerminalThread(QThread):
    """SSH 터미널 스레드"""
    
    # 시그널 정의
    data_received = Signal(str)
    connection_status_changed = Signal(str)  # ConnectionStatus
    error_occurred = Signal(str)
    
    def __init__(self, connection: SSHConnection):
        super().__init__()
        self.connection = connection
        self.ssh_client = None
        self.channel = None
        self.running = False
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """스레드 실행"""
        try:
            self._connect_ssh()
            if self.channel:
                self._read_loop()
        except Exception as e:
            self.logger.error(f"SSH 터미널 스레드 오류: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self._cleanup()
    
    def _connect_ssh(self):
        """SSH 연결"""
        try:
            if paramiko is None:
                raise ImportError("paramiko 라이브러리가 설치되지 않았습니다.")
            
            self.connection_status_changed.emit(ConnectionStatus.CONNECTING.value)
            self.logger.info(f"SSH 연결 시도: {self.connection.get_connection_string()}")
            
            # SSH 클라이언트 생성
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 디버그 로깅 활성화
            import logging
            paramiko_logger = logging.getLogger("paramiko")
            paramiko_logger.setLevel(logging.DEBUG)
            
            # 서버 정보 미리 확인
            self._diagnose_ssh_server()
            
            # 연결 설정
            connect_kwargs = {
                'hostname': self.connection.host,
                'port': self.connection.port,
                'username': self.connection.username,
                'timeout': self.connection.timeout,
                'allow_agent': True,  # SSH 에이전트 허용
                'look_for_keys': True,  # 기본 키 위치 확인
            }
            
            # 인증 설정
            self.logger.info(f"인증 방법: {self.connection.auth_method.value}")
            if self.connection.auth_method.value == 'password':
                if not self.connection.password:
                    raise ValueError("비밀번호가 설정되지 않았습니다.")
                connect_kwargs['password'] = self.connection.password
                # 키 기반 인증 비활성화 (비밀번호만 사용)
                connect_kwargs['allow_agent'] = False
                connect_kwargs['look_for_keys'] = False
                self.logger.info(f"비밀번호 인증 사용 (키 인증 비활성화), 비밀번호 길이: {len(self.connection.password)}자")
            elif self.connection.auth_method.value == 'key_file':
                if not self.connection.key_file_path:
                    raise ValueError("키 파일 경로가 설정되지 않았습니다.")
                connect_kwargs['key_filename'] = self.connection.key_file_path
                if self.connection.passphrase:
                    connect_kwargs['passphrase'] = self.connection.passphrase
                self.logger.info(f"키 파일 인증 사용: {self.connection.key_file_path}")
            
            # 연결 시도
            self.logger.info("SSH 연결 중...")
            self.logger.info(f"연결 매개변수: 호스트={connect_kwargs['hostname']}, 포트={connect_kwargs['port']}, 사용자={connect_kwargs['username']}")
            
            # 수동 인증으로 더 세밀한 제어
            if self.connection.auth_method.value == 'password':
                self._manual_password_auth(connect_kwargs)
            else:
                try:
                    self.ssh_client.connect(**connect_kwargs)
                except paramiko.AuthenticationException as e:
                    self.logger.error(f"인증 실패: {e}")
                    self._diagnose_auth_failure()
                    raise e
            
            # 터미널 채널 생성
            self.logger.info("터미널 채널 생성 중...")
            
            # 안전하고 표준적인 터미널 크기 사용
            initial_cols, initial_rows = 80, 24  
            initial_width_px = initial_cols * 8   # 문자당 8픽셀 (일반적인 값)
            initial_height_px = initial_rows * 16  # 줄당 16픽셀 (일반적인 값)
            
            self.logger.info(f"초기 터미널 크기: {initial_cols}x{initial_rows} ({initial_width_px}x{initial_height_px} 픽셀)")
            
            # 기본적인 터미널 채널 생성
            self.channel = self.ssh_client.invoke_shell(
                term=self.connection.terminal_type,
                width=initial_cols,
                height=initial_rows,
                width_pixels=initial_width_px,
                height_pixels=initial_height_px
            )
            
            # 논블로킹 모드 설정
            self.channel.setblocking(0)
            
            self.logger.info(f"터미널 채널 초기화 완료: {self.connection.terminal_type} {initial_cols}x{initial_rows}")
            
            self.running = True
            self.connection.status = ConnectionStatus.CONNECTED
            self.connection_status_changed.emit(ConnectionStatus.CONNECTED.value)
            
            self.logger.info(f"SSH 연결 성공: {self.connection.get_connection_string()}")
            
        except Exception as e:
            self.connection.status = ConnectionStatus.FAILED
            self.connection.last_error = str(e)
            self.connection_status_changed.emit(ConnectionStatus.FAILED.value)
            self.logger.error(f"SSH 연결 실패: {e}")
            self.logger.error(f"연결 정보: 호스트={self.connection.host}, 포트={self.connection.port}, 사용자={self.connection.username}")
            raise
    
    def _read_loop(self):
        """데이터 읽기 루프"""
        self.logger.info("데이터 읽기 루프 시작")
        
        while self.running and self.channel and not self.channel.closed:
            try:
                if self.channel.recv_ready():
                    data = self.channel.recv(1024)
                    if data:
                        text = data.decode(self.connection.encoding, errors='replace')
                        self.data_received.emit(text)
                    elif len(data) == 0:
                        # 연결이 서버에서 종료됨
                        self.logger.info("서버에서 연결 종료됨 (빈 데이터 수신)")
                        break
                
                # 채널이 닫혔는지 확인
                if self.channel.closed:
                    self.logger.info("채널이 닫혔음")
                    break
                
                # CPU 사용률을 줄이기 위한 짧은 대기
                time.sleep(0.01)
                
            except socket.timeout:
                # 타임아웃은 정상적인 상황
                continue
            except socket.error as e:
                if self.running:
                    self.logger.error(f"소켓 오류: {e}")
                    self.error_occurred.emit(f"소켓 오류: {e}")
                break
            except Exception as e:
                if self.running:  # 정상 종료가 아닌 경우만 에러로 처리
                    self.logger.error(f"데이터 읽기 오류: {e}")
                    self.error_occurred.emit(str(e))
                break
        
        self.logger.info("데이터 읽기 루프 종료")
    
    def send_data(self, data: str):
        """데이터 전송"""
        if self.channel and not self.channel.closed:
            try:
                encoded_data = data.encode(self.connection.encoding)
                # self.logger.info(f"데이터 전송: '{repr(data)}' -> {len(encoded_data)} bytes")
                self.channel.send(encoded_data)
            except Exception as e:
                self.logger.error(f"데이터 전송 오류: {e}")
                self.error_occurred.emit(str(e))
    
    def resize_terminal(self, width: int, height: int):
        """터미널 크기 조정"""
        if self.channel and not self.channel.closed:
            try:
                # 이전 크기와 동일한지 확인 (불필요한 조정 방지)
                if hasattr(self, '_last_size'):
                    if self._last_size == (width, height):
                        self.logger.debug(f"터미널 크기 변경 없음: {width}x{height}")
                        return
                
                self.logger.info(f"터미널 PTY 크기 조정 시도: {width}x{height}")
                
                # PTY 크기 조정 (paramiko의 resize_pty 메서드 사용)
                self.channel.resize_pty(width, height, width * 8, height * 16)  # 픽셀 크기도 추가
                
                # 크기 정보 저장
                self._last_size = (width, height)
                
                self.logger.info(f"✅ PTY 크기 조정 성공: {width}x{height}")
                
            except Exception as e:
                self.logger.error(f"터미널 크기 조정 오류: {e}")
        else:
            self.logger.warning("터미널 채널이 없거나 닫혀있어 크기 조정 불가")
    
    def disconnect_ssh_connection(self):
        """연결 종료"""
        self.running = False
        
        # 채널 종료
        if self.channel:
            try:
                self.channel.close()
            except:
                pass
        
        # SSH 클라이언트 종료
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except:
                pass
        
        # 스레드 종료 대기
        if self.isRunning():
            self.wait(3000)  # 3초 대기
    
    def _cleanup(self):
        """정리 작업"""
        self.logger.info("SSH 연결 정리 중...")
        
        if self.connection.status == ConnectionStatus.CONNECTED:
            self.connection.status = ConnectionStatus.DISCONNECTED
            self.connection_status_changed.emit(ConnectionStatus.DISCONNECTED.value)
        
        self.logger.info("SSH 연결 정리 완료")
    
    def _diagnose_ssh_server(self):
        """SSH 서버 연결 가능성 진단"""
        try:
            import socket
            
            self.logger.info(f"서버 연결 테스트: {self.connection.host}:{self.connection.port}")
            
            # 포트 연결 테스트
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.connection.host, self.connection.port))
            sock.close()
            
            if result == 0:
                self.logger.info("✅ 서버 포트 연결 가능")
            else:
                self.logger.warning(f"❌ 서버 포트 연결 실패: {result}")
                
        except Exception as e:
            self.logger.error(f"서버 진단 오류: {e}")
    
    def _manual_password_auth(self, connect_kwargs):
        """수동 비밀번호 인증 (더 세밀한 제어)"""
        try:
            # 단순한 연결 방식으로 변경 (진단 도구와 동일하게)
            self.logger.info("단순 비밀번호 인증 방식 사용...")
            
            if not self.ssh_client:
                raise Exception("SSH 클라이언트가 초기화되지 않았습니다")
            
            self.ssh_client.connect(
                hostname=connect_kwargs['hostname'],
                port=connect_kwargs['port'],
                username=connect_kwargs['username'],
                password=connect_kwargs['password'],
                timeout=connect_kwargs['timeout'],
                allow_agent=False,
                look_for_keys=False,
                auth_timeout=30  # 인증 타임아웃 증가
            )
            
            self.logger.info("✅ 비밀번호 인증 성공!")
                
        except Exception as e:
            self.logger.error(f"수동 비밀번호 인증 오류: {e}")
            raise e
    
    def _diagnose_auth_failure(self):
        """인증 실패 원인 진단"""
        self.logger.info("🔍 인증 실패 원인 진단 중...")
        
        # 일반적인 인증 실패 원인들
        common_causes = [
            "1. 잘못된 사용자명 또는 비밀번호",
            "2. 서버 설정에서 PasswordAuthentication no",
            "3. 사용자 계정이 SSH 로그인을 허용하지 않음",
            "4. 서버의 AllowUsers/DenyUsers 설정",
            "5. 계정이 잠겨있거나 만료됨",
            "6. 서버의 MaxAuthTries 초과",
            "7. 서버의 특정 호스트/IP 제한",
            "8. PAM 인증 설정 문제"
        ]
        
        self.logger.info("일반적인 SSH 인증 실패 원인들:")
        for cause in common_causes:
            self.logger.info(f"  {cause}")
        
        self.logger.info("")
        self.logger.info("해결 방법:")
        self.logger.info("  • SSH 서버에 직접 로그인해보세요: ssh username@hostname")
        self.logger.info("  • 서버 로그 확인: /var/log/auth.log 또는 /var/log/secure")
        self.logger.info("  • SSH 설정 확인: /etc/ssh/sshd_config")
        self.logger.info("  • 다른 SSH 클라이언트로 테스트해보세요")
    
    def _calculate_terminal_size(self):
        """터미널 크기 계산 (문자 단위)"""
        try:
            # SSH 스레드에서 호출되므로 기본값 반환
            # 실제 크기는 연결 후 UI 스레드에서 업데이트
            return 80, 24  # 기본값
        except:
            return 80, 24

class TerminalWidget(QWidget):
    """터미널 위젯"""
    
    def __init__(self, connection: SSHConnection, parent=None):
        super().__init__(parent)
        
        self.connection = connection
        self.ssh_thread: Optional[SSHTerminalThread] = None
        self.logger = logging.getLogger(__name__)
        
        # ANSI 파서 초기화
        self.ansi_parser = AnsiParser()
        
        # UI 설정
        self._setup_ui()
        
        # 상태 관리
        self._setup_status_management()
    
    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 터미널 텍스트 에디터 (완전한 읽기 전용)
        self.terminal_display = QTextEdit()
        self.terminal_display.setReadOnly(True)
        self.terminal_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)  # 줄바꿈 비활성화
        self.terminal_display.setAcceptRichText(True)  # 서식 있는 텍스트 허용
        
        # 모든 텍스트 상호작용 비활성화 (SSH를 통해서만 입력)
        self.terminal_display.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.terminal_display.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # 포커스는 받되 텍스트 편집은 안함
        
        # 커서 깜빡임 비활성화
        self.terminal_display.setCursorWidth(0)
        
        # 폰트 설정 (모노스페이스)
        font = QFont("Monaco", 12)  # macOS 기본 모노스페이스 폰트
        if not font.exactMatch():
            font = QFont("Menlo", 12)  # macOS의 다른 모노스페이스 폰트
        if not font.exactMatch():
            font = QFont("Courier New", 12)  # 범용 모노스페이스 폰트
        
        font.setFixedPitch(True)
        self.terminal_display.setFont(font)
        
        # 색상 설정 (터미널 스타일)
        self.terminal_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: none;
                selection-background-color: #3399ff;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                line-height: 1.2;
                padding: 4px;
            }
        """)
        
        # ANSI 파서의 기본 색상도 설정
        from dspilot_shell.ansi_parser import TerminalStyle
        from PySide6.QtGui import QColor
        self.ansi_parser.default_style = TerminalStyle(foreground=QColor(255, 255, 255))
        self.ansi_parser.current_style = self.ansi_parser._copy_style(self.ansi_parser.default_style)
        
        # 스크롤바 설정
        self.terminal_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.terminal_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        layout.addWidget(self.terminal_display)
        
        # 키 이벤트 처리를 위한 커스텀 텍스트 에디터 설정
        self.terminal_display.installEventFilter(self)
    
    def _setup_status_management(self):
        """상태 관리 설정"""
        # 연결 상태 초기화
        self.connection.status = ConnectionStatus.DISCONNECTED
        
        # 크기 조정 타이머
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._update_terminal_size)
    
    def connect_ssh(self):
        """SSH 연결 시작"""
        if self.ssh_thread and self.ssh_thread.isRunning():
            return
        
        try:
            # SSH 스레드 생성 및 시작
            self.ssh_thread = SSHTerminalThread(self.connection)
            
            # 시그널 연결
            self.ssh_thread.data_received.connect(self._on_data_received)
            self.ssh_thread.connection_status_changed.connect(self._on_connection_status_changed)
            self.ssh_thread.error_occurred.connect(self._on_error_occurred)
            
            # 스레드 시작
            self.ssh_thread.start()
            
            self.logger.info(f"SSH 연결 시작: {self.connection.get_connection_string()}")
            
        except Exception as e:
            self.logger.error(f"SSH 연결 시작 실패: {e}")
            self._append_terminal_text(f"\nSSH 연결 시작 실패: {str(e)}\n", error=True)
    
    def disconnect_ssh(self):
        """SSH 연결 종료"""
        if self.ssh_thread:
            self.ssh_thread.disconnect_ssh_connection()
            self.ssh_thread = None
        
        self.logger.info(f"SSH 연결 종료: {self.connection.get_connection_string()}")
    
    @Slot(str)
    def _on_data_received(self, data: str):
        """데이터 수신 처리 (ANSI 파싱 적용)"""
        try:
            # ANSI 이스케이프 시퀀스 파싱
            parsed_chunks = self.ansi_parser.parse_text(data)
            
            # 각 청크를 스타일과 함께 터미널에 추가
            cursor = self.terminal_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            
            for text, style in parsed_chunks:
                if text:  # 빈 텍스트가 아닌 경우만 추가
                    # 스타일 적용
                    text_format = self.ansi_parser.create_text_format(style)
                    cursor.setCharFormat(text_format)
                    cursor.insertText(text)
            
            # 커서를 텍스트 끝으로 이동
            self.terminal_display.setTextCursor(cursor)
            
            # 스크롤을 맨 아래로
            scrollbar = self.terminal_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            self.logger.error(f"데이터 파싱 오류: {e}")
            # 파싱 실패 시 원본 텍스트 그대로 표시
            self._append_terminal_text(data, error=False)
    
    @Slot(str)
    def _on_connection_status_changed(self, status: str):
        """연결 상태 변경 처리"""
        status_enum = ConnectionStatus(status)
        self.connection.status = status_enum
        
        if status_enum == ConnectionStatus.CONNECTED:
            self._append_terminal_text(f"\n✅ 연결됨: {self.connection.get_connection_string()}\n", success=True)
            # 연결 후 한 번만 터미널 크기 업데이트
            QTimer.singleShot(500, self._update_terminal_size)   # 0.5초 후 한 번만
        elif status_enum == ConnectionStatus.DISCONNECTED:
            self._append_terminal_text(f"\n❌ 연결 종료됨: {self.connection.get_connection_string()}\n", info=True)
        elif status_enum == ConnectionStatus.FAILED:
            self._append_terminal_text(f"\n🚫 연결 실패: {self.connection.last_error}\n", error=True)
        elif status_enum == ConnectionStatus.CONNECTING:
            self._append_terminal_text(f"\n🔄 연결 중: {self.connection.get_connection_string()}\n", info=True)
    
    @Slot(str)
    def _on_error_occurred(self, error: str):
        """에러 발생 처리"""
        self.connection.last_error = error
        self._append_terminal_text(f"\n오류: {error}\n", error=True)
    
    def _append_terminal_text(self, text: str, error: bool = False, success: bool = False, info: bool = False):
        """터미널에 시스템 메시지 추가 (색상 구분)"""
        cursor = self.terminal_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 텍스트 포맷 생성
        text_format = QTextCharFormat()
        
        # 색상 설정
        if error:
            text_format.setForeground(self.terminal_display.palette().color(self.terminal_display.palette().ColorRole.Highlight))
        elif success:
            text_format.setForeground(self.terminal_display.palette().color(self.terminal_display.palette().ColorRole.Link))
        elif info:
            text_format.setForeground(self.terminal_display.palette().color(self.terminal_display.palette().ColorRole.BrightText))
        else:
            text_format.setForeground(self.terminal_display.palette().color(self.terminal_display.palette().ColorRole.Text))
        
        # 포맷 적용하여 텍스트 삽입
        cursor.setCharFormat(text_format)
        cursor.insertText(text)
        
        # 커서 설정
        self.terminal_display.setTextCursor(cursor)
        
        # 스크롤을 맨 아래로
        scrollbar = self.terminal_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _handle_key_press(self, event):
        """표준 터미널 에뮬레이터 키 입력 처리"""
        if not self.ssh_thread or not self.ssh_thread.channel:
            return
        
        # QKeyEvent로 캐스팅
        if not isinstance(event, QKeyEvent):
            return
        
        # 키와 텍스트 정보
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()
        
        # 전송할 데이터
        data_to_send = None
        
        # Ctrl 조합 처리 (ASCII 제어 문자)
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if key >= Qt.Key.Key_A and key <= Qt.Key.Key_Z:
                # Ctrl+A부터 Ctrl+Z까지 (ASCII 제어 문자)
                ctrl_char = chr(key - Qt.Key.Key_A + 1)
                data_to_send = ctrl_char
            elif key == Qt.Key.Key_Space:  # Ctrl+Space (NUL)
                data_to_send = '\x00'
            elif key == Qt.Key.Key_BracketLeft:  # Ctrl+[ (ESC)
                data_to_send = '\x1b'
            elif key == Qt.Key.Key_Backslash:  # Ctrl+\ (FS)
                data_to_send = '\x1c'
            elif key == Qt.Key.Key_BracketRight:  # Ctrl+] (GS)
                data_to_send = '\x1d'
            elif key == Qt.Key.Key_AsciiCircum:  # Ctrl+^ (RS)
                data_to_send = '\x1e'
            elif key == Qt.Key.Key_Underscore:  # Ctrl+_ (US)
                data_to_send = '\x1f'
        
        # Alt 조합 처리 (ESC 시퀀스)
        elif modifiers & Qt.KeyboardModifier.AltModifier:
            if text and len(text) == 1:
                data_to_send = '\x1b' + text
        
        # 특수 키 처리 (방향키, 기능키 등)
        elif key == Qt.Key.Key_Up:
            data_to_send = '\x1b[A'
        elif key == Qt.Key.Key_Down:
            data_to_send = '\x1b[B'
        elif key == Qt.Key.Key_Right:
            data_to_send = '\x1b[C'
        elif key == Qt.Key.Key_Left:
            data_to_send = '\x1b[D'
        elif key == Qt.Key.Key_Home:
            data_to_send = '\x1b[H'
        elif key == Qt.Key.Key_End:
            data_to_send = '\x1b[F'
        elif key == Qt.Key.Key_PageUp:
            data_to_send = '\x1b[5~'
        elif key == Qt.Key.Key_PageDown:
            data_to_send = '\x1b[6~'
        elif key == Qt.Key.Key_Insert:
            data_to_send = '\x1b[2~'
        elif key == Qt.Key.Key_Delete:
            data_to_send = '\x1b[3~'
        
        # 기능키 처리
        elif key == Qt.Key.Key_F1:
            data_to_send = '\x1bOP'
        elif key == Qt.Key.Key_F2:
            data_to_send = '\x1bOQ'
        elif key == Qt.Key.Key_F3:
            data_to_send = '\x1bOR'
        elif key == Qt.Key.Key_F4:
            data_to_send = '\x1bOS'
        elif key >= Qt.Key.Key_F5 and key <= Qt.Key.Key_F12:
            f_num = key - Qt.Key.Key_F5 + 5
            if f_num <= 12:
                f_codes = {5: 15, 6: 17, 7: 18, 8: 19, 9: 20, 10: 21, 11: 23, 12: 24}
                data_to_send = f'\x1b[{f_codes[f_num]}~'
        
        # 기본 키 처리
        elif key == Qt.Key.Key_Escape:
            data_to_send = '\x1b'
        elif key == Qt.Key.Key_Tab:
            data_to_send = '\t'
        elif key == Qt.Key.Key_Backspace:
            data_to_send = '\x7f'
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            data_to_send = '\r'
        
        # 일반 문자 입력
        elif text:
            # 모든 입력 가능한 문자 허용 (유니코드 포함)
            data_to_send = text
        
        # 데이터 전송
        if data_to_send is not None:
            self.ssh_thread.send_data(data_to_send)
    
    def copy_selection(self):
        """선택된 텍스트 복사"""
        self.terminal_display.copy()
    
    def paste_from_clipboard(self):
        """클립보드에서 붙여넣기"""
        if self.ssh_thread and self.ssh_thread.channel:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                self.ssh_thread.send_data(text)
    
    def resizeEvent(self, event):
        """크기 변경 이벤트"""
        super().resizeEvent(event)
        
        # 연결된 상태에서만 크기 업데이트
        if (self.ssh_thread and self.ssh_thread.channel and 
            not self.ssh_thread.channel.closed and
            self.connection.status == ConnectionStatus.CONNECTED):
            # 터미널 크기 업데이트를 위한 타이머 시작 (디바운싱)
            self.resize_timer.start(1000)  # 1초 후 크기 업데이트 (더 안정적)
    
    @Slot()
    def _update_terminal_size(self):
        """터미널 크기 업데이트"""
        if not self.ssh_thread or not self.ssh_thread.channel:
            return
        
        try:
            # 폰트 메트릭을 이용해 문자 크기 계산
            font_metrics = QFontMetrics(self.terminal_display.font())
            
            # 정확한 문자 크기 계산 (모노스페이스 폰트용)
            char_width = font_metrics.horizontalAdvance('M')  # 'M'은 가장 넓은 문자
            char_height = font_metrics.height()
            
            # 터미널 위젯의 실제 표시 영역 크기
            viewport = self.terminal_display.viewport()
            
            # 스크롤바와 여백을 고려한 실제 사용 가능한 크기
            scrollbar_width = self.terminal_display.verticalScrollBar().width() if self.terminal_display.verticalScrollBar().isVisible() else 0
            scrollbar_height = self.terminal_display.horizontalScrollBar().height() if self.terminal_display.horizontalScrollBar().isVisible() else 0
            
            usable_width = viewport.width() - scrollbar_width - 20  # 좌우 여백 20px
            usable_height = viewport.height() - scrollbar_height - 20  # 상하 여백 20px
            
            # 문자 단위 크기 계산 (정수로 변환)
            cols = max(40, min(120, int(usable_width / char_width)))
            rows = max(10, min(50, int(usable_height / char_height)))
            
            self.logger.info(f"터미널 크기 계산:")
            self.logger.info(f"  • 뷰포트: {viewport.width()}x{viewport.height()}")
            self.logger.info(f"  • 스크롤바: {scrollbar_width}x{scrollbar_height}")
            self.logger.info(f"  • 사용가능: {usable_width}x{usable_height}")
            self.logger.info(f"  • 문자크기: {char_width}x{char_height}")
            self.logger.info(f"  • 최종크기: {cols}x{rows}")
            
            # SSH 채널 크기 조정
            self.ssh_thread.resize_terminal(cols, rows)
            
        except Exception as e:
            self.logger.error(f"터미널 크기 업데이트 오류: {e}")
            # 오류 시 기본 크기 사용
            self.ssh_thread.resize_terminal(80, 24)
    
    def get_connection_status(self) -> ConnectionStatus:
        """연결 상태 반환"""
        return self.connection.status
    
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """이벤트 필터 (완전한 키 입력 가로채기)"""
        if watched == self.terminal_display:
            event_type = event.type()
            if event_type in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease, 
                            QEvent.Type.ShortcutOverride, QEvent.Type.InputMethod,
                            QEvent.Type.InputMethodQuery):
                if event_type == QEvent.Type.KeyPress:
                    # 키 입력만 SSH로 전송하고 QTextEdit는 완전히 무시
                    self._handle_key_press(event)
                # 모든 키 관련 이벤트를 여기서 완전히 소비
                return True
        return super().eventFilter(watched, event)
