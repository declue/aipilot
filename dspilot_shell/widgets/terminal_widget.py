"""
SSH 터미널 위젯
"""
import logging
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
            
            # SSH 클라이언트 생성
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 연결 설정
            connect_kwargs = {
                'hostname': self.connection.host,
                'port': self.connection.port,
                'username': self.connection.username,
                'timeout': self.connection.timeout,
            }
            
            # 인증 설정
            if self.connection.auth_method.value == 'password':
                connect_kwargs['password'] = self.connection.password
            elif self.connection.auth_method.value == 'key_file':
                connect_kwargs['key_filename'] = self.connection.key_file_path
                if self.connection.passphrase:
                    connect_kwargs['passphrase'] = self.connection.passphrase
            
            # 연결 시도
            self.ssh_client.connect(**connect_kwargs)
            
            # 터미널 채널 생성
            self.channel = self.ssh_client.invoke_shell(
                term=self.connection.terminal_type,
                width=80,
                height=24
            )
            
            # 논블로킹 모드 설정
            self.channel.setblocking(0)
            
            self.running = True
            self.connection.status = ConnectionStatus.CONNECTED
            self.connection_status_changed.emit(ConnectionStatus.CONNECTED.value)
            
            self.logger.info(f"SSH 연결 성공: {self.connection.get_connection_string()}")
            
        except Exception as e:
            self.connection.status = ConnectionStatus.FAILED
            self.connection.last_error = str(e)
            self.connection_status_changed.emit(ConnectionStatus.FAILED.value)
            self.logger.error(f"SSH 연결 실패: {e}")
            raise
    
    def _read_loop(self):
        """데이터 읽기 루프"""
        while self.running and self.channel and not self.channel.closed:
            try:
                if self.channel.recv_ready():
                    data = self.channel.recv(1024)
                    if data:
                        text = data.decode(self.connection.encoding, errors='replace')
                        self.data_received.emit(text)
                
                # CPU 사용률을 줄이기 위한 짧은 대기
                time.sleep(0.01)
                
            except Exception as e:
                if self.running:  # 정상 종료가 아닌 경우만 에러로 처리
                    self.logger.error(f"데이터 읽기 오류: {e}")
                    self.error_occurred.emit(str(e))
                break
    
    def send_data(self, data: str):
        """데이터 전송"""
        if self.channel and not self.channel.closed:
            try:
                encoded_data = data.encode(self.connection.encoding)
                self.channel.send(encoded_data)
            except Exception as e:
                self.logger.error(f"데이터 전송 오류: {e}")
                self.error_occurred.emit(str(e))
    
    def resize_terminal(self, width: int, height: int):
        """터미널 크기 조정"""
        if self.channel and not self.channel.closed:
            try:
                self.channel.resize_pty(width, height)
            except Exception as e:
                self.logger.error(f"터미널 크기 조정 오류: {e}")
    
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
        self.connection.status = ConnectionStatus.DISCONNECTED
        self.connection_status_changed.emit(ConnectionStatus.DISCONNECTED.value)


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
        
        # 터미널 텍스트 에디터
        self.terminal_display = QTextEdit()
        self.terminal_display.setReadOnly(True)
        self.terminal_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        # 폰트 설정 (모노스페이스)
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Monaco", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        
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
            self._append_terminal_text(f"\n연결됨: {self.connection.get_connection_string()}\n", success=True)
        elif status_enum == ConnectionStatus.DISCONNECTED:
            self._append_terminal_text(f"\n연결 종료됨: {self.connection.get_connection_string()}\n", info=True)
        elif status_enum == ConnectionStatus.FAILED:
            self._append_terminal_text(f"\n연결 실패: {self.connection.last_error}\n", error=True)
    
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
        """키 입력 처리"""
        if not self.ssh_thread or not self.ssh_thread.channel:
            return
        
        # QKeyEvent로 캐스팅
        if not isinstance(event, QKeyEvent):
            return
        
        # 특수 키 처리
        key = event.key()
        text = event.text()
        
        # Ctrl 조합 처리
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_C:  # Ctrl+C
                self.ssh_thread.send_data('\x03')
                return
            elif key == Qt.Key.Key_D:  # Ctrl+D
                self.ssh_thread.send_data('\x04')
                return
            elif key == Qt.Key.Key_Z:  # Ctrl+Z
                self.ssh_thread.send_data('\x1a')
                return
        
        # 방향키 처리
        if key == Qt.Key.Key_Up:
            self.ssh_thread.send_data('\x1b[A')
        elif key == Qt.Key.Key_Down:
            self.ssh_thread.send_data('\x1b[B')
        elif key == Qt.Key.Key_Right:
            self.ssh_thread.send_data('\x1b[C')
        elif key == Qt.Key.Key_Left:
            self.ssh_thread.send_data('\x1b[D')
        elif key == Qt.Key.Key_PageUp:
            self.ssh_thread.send_data('\x1b[5~')
        elif key == Qt.Key.Key_PageDown:
            self.ssh_thread.send_data('\x1b[6~')
        elif key == Qt.Key.Key_Home:
            self.ssh_thread.send_data('\x1b[H')
        elif key == Qt.Key.Key_End:
            self.ssh_thread.send_data('\x1b[F')
        elif key == Qt.Key.Key_Escape:
            self.ssh_thread.send_data('\x1b')
        elif key == Qt.Key.Key_Tab:
            self.ssh_thread.send_data('\t')
        elif key == Qt.Key.Key_Backspace:
            self.ssh_thread.send_data('\x7f')
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.ssh_thread.send_data('\r')
        elif text:
            # 일반 텍스트 전송
            self.ssh_thread.send_data(text)
    
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
        
        # 터미널 크기 업데이트를 위한 타이머 시작
        self.resize_timer.start(500)  # 500ms 후 크기 업데이트
    
    @Slot()
    def _update_terminal_size(self):
        """터미널 크기 업데이트"""
        if not self.ssh_thread or not self.ssh_thread.channel:
            return
        
        # 폰트 메트릭을 이용해 문자 크기 계산
        font_metrics = QFontMetrics(self.terminal_display.font())
        char_width = font_metrics.averageCharWidth()
        char_height = font_metrics.height()
        
        # 터미널 위젯 크기
        widget_width = self.terminal_display.viewport().width()
        widget_height = self.terminal_display.viewport().height()
        
        # 문자 단위 크기 계산
        cols = max(1, widget_width // char_width)
        rows = max(1, widget_height // char_height)
        
        # SSH 채널 크기 조정
        self.ssh_thread.resize_terminal(cols, rows)
    
    def get_connection_status(self) -> ConnectionStatus:
        """연결 상태 반환"""
        return self.connection.status
    
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """이벤트 필터"""
        if watched == self.terminal_display and event.type() == QEvent.Type.KeyPress:
            self._handle_key_press(event)
            return True
        return super().eventFilter(watched, event)
