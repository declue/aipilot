"""
연결 관리자 위젯
"""
import json
import logging
from typing import Dict, Optional

from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QCheckBox,
    QFileDialog,
)

from dspilot_core.config.config_manager import ConfigManager
from dspilot_shell.models.ssh_connection import SSHConnection, AuthMethod, ConnectionStatus


class NewConnectionDialog(QDialog):
    """새 연결 대화상자"""
    
    def __init__(self, parent=None, connection: Optional[SSHConnection] = None):
        super().__init__(parent)
        
        self.connection = connection
        self.is_editing = connection is not None
        
        self.setWindowTitle('연결 편집' if self.is_editing else '새 연결')
        self.setModal(True)
        self.setMinimumSize(500, 600)
        
        self._setup_ui()
        
        if self.is_editing and self.connection:
            self._load_connection_data()
    
    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 기본 설정 탭
        self._setup_basic_tab()
        
        # 인증 설정 탭
        self._setup_auth_tab()
        
        # 고급 설정 탭
        self._setup_advanced_tab()
        
        # 버튼 박스
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def _setup_basic_tab(self):
        """기본 설정 탭"""
        basic_widget = QWidget()
        layout = QFormLayout(basic_widget)
        
        # 연결 이름
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText('연결 이름 (선택사항)')
        layout.addRow('연결 이름:', self.name_edit)
        
        # 호스트
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText('IP 주소 또는 호스트명')
        layout.addRow('호스트:', self.host_edit)
        
        # 포트
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        layout.addRow('포트:', self.port_spin)
        
        # 사용자명
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText('SSH 사용자명')
        layout.addRow('사용자명:', self.username_edit)
        
        self.tab_widget.addTab(basic_widget, '기본 설정')
    
    def _setup_auth_tab(self):
        """인증 설정 탭"""
        auth_widget = QWidget()
        layout = QVBoxLayout(auth_widget)
        
        # 인증 방법 그룹
        auth_group = QGroupBox('인증 방법')
        auth_layout = QFormLayout(auth_group)
        
        self.auth_method_combo = QComboBox()
        self.auth_method_combo.addItems(['비밀번호', '키 파일', '키 에이전트'])
        self.auth_method_combo.currentTextChanged.connect(self._on_auth_method_changed)
        auth_layout.addRow('인증 방법:', self.auth_method_combo)
        
        layout.addWidget(auth_group)
        
        # 비밀번호 그룹
        self.password_group = QGroupBox('비밀번호 인증')
        password_layout = QFormLayout(self.password_group)
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText('SSH 비밀번호')
        password_layout.addRow('비밀번호:', self.password_edit)
        
        layout.addWidget(self.password_group)
        
        # 키 파일 그룹
        self.key_file_group = QGroupBox('키 파일 인증')
        key_file_layout = QFormLayout(self.key_file_group)
        
        key_file_row = QHBoxLayout()
        self.key_file_edit = QLineEdit()
        self.key_file_edit.setPlaceholderText('키 파일 경로')
        self.key_file_browse_btn = QPushButton('찾아보기')
        self.key_file_browse_btn.clicked.connect(self._browse_key_file)
        key_file_row.addWidget(self.key_file_edit)
        key_file_row.addWidget(self.key_file_browse_btn)
        
        key_file_widget = QWidget()
        key_file_widget.setLayout(key_file_row)
        key_file_layout.addRow('키 파일:', key_file_widget)
        
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_edit.setPlaceholderText('키 파일 암호 (선택사항)')
        key_file_layout.addRow('암호구:', self.passphrase_edit)
        
        layout.addWidget(self.key_file_group)
        
        # 초기 상태 설정
        self._on_auth_method_changed('비밀번호')
        
        self.tab_widget.addTab(auth_widget, '인증 설정')
    
    def _setup_advanced_tab(self):
        """고급 설정 탭"""
        advanced_widget = QWidget()
        layout = QVBoxLayout(advanced_widget)
        
        # 연결 옵션 그룹
        connection_group = QGroupBox('연결 옵션')
        connection_layout = QFormLayout(connection_group)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(' 초')
        connection_layout.addRow('연결 타임아웃:', self.timeout_spin)
        
        self.keep_alive_check = QCheckBox('Keep-Alive 활성화')
        self.keep_alive_check.setChecked(True)
        connection_layout.addRow('', self.keep_alive_check)
        
        self.compression_check = QCheckBox('압축 활성화')
        connection_layout.addRow('', self.compression_check)
        
        layout.addWidget(connection_group)
        
        # 터미널 설정 그룹
        terminal_group = QGroupBox('터미널 설정')
        terminal_layout = QFormLayout(terminal_group)
        
        self.terminal_type_combo = QComboBox()
        self.terminal_type_combo.addItems(['xterm-256color', 'xterm', 'vt100', 'vt220'])
        terminal_layout.addRow('터미널 타입:', self.terminal_type_combo)
        
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(['utf-8', 'euc-kr', 'cp949', 'iso-8859-1'])
        terminal_layout.addRow('인코딩:', self.encoding_combo)
        
        layout.addWidget(terminal_group)
        
        # 프록시 설정 그룹
        proxy_group = QGroupBox('프록시 설정 (선택사항)')
        proxy_layout = QFormLayout(proxy_group)
        
        self.proxy_host_edit = QLineEdit()
        self.proxy_host_edit.setPlaceholderText('프록시 호스트')
        proxy_layout.addRow('프록시 호스트:', self.proxy_host_edit)
        
        self.proxy_port_spin = QSpinBox()
        self.proxy_port_spin.setRange(0, 65535)
        proxy_layout.addRow('프록시 포트:', self.proxy_port_spin)
        
        self.proxy_username_edit = QLineEdit()
        self.proxy_username_edit.setPlaceholderText('프록시 사용자명')
        proxy_layout.addRow('프록시 사용자명:', self.proxy_username_edit)
        
        self.proxy_password_edit = QLineEdit()
        self.proxy_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.proxy_password_edit.setPlaceholderText('프록시 비밀번호')
        proxy_layout.addRow('프록시 비밀번호:', self.proxy_password_edit)
        
        layout.addWidget(proxy_group)
        
        self.tab_widget.addTab(advanced_widget, '고급 설정')
    
    @Slot(str)
    def _on_auth_method_changed(self, method: str):
        """인증 방법 변경"""
        if method == '비밀번호':
            self.password_group.setVisible(True)
            self.key_file_group.setVisible(False)
        elif method == '키 파일':
            self.password_group.setVisible(False)
            self.key_file_group.setVisible(True)
        else:  # 키 에이전트
            self.password_group.setVisible(False)
            self.key_file_group.setVisible(False)
    
    @Slot()
    def _browse_key_file(self):
        """키 파일 찾아보기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '키 파일 선택',
            '',
            'Key Files (*.pem *.key *.pub);;All Files (*)'
        )
        if file_path:
            self.key_file_edit.setText(file_path)
    
    def _load_connection_data(self):
        """연결 데이터 로드"""
        if not self.connection:
            return
        
        # 기본 설정
        self.name_edit.setText(self.connection.name)
        self.host_edit.setText(self.connection.host)
        self.port_spin.setValue(self.connection.port)
        self.username_edit.setText(self.connection.username)
        
        # 인증 설정
        auth_method_map = {
            AuthMethod.PASSWORD: '비밀번호',
            AuthMethod.KEY_FILE: '키 파일',
            AuthMethod.KEY_AGENT: '키 에이전트'
        }
        self.auth_method_combo.setCurrentText(auth_method_map[self.connection.auth_method])
        
        self.password_edit.setText(self.connection.password)
        self.key_file_edit.setText(self.connection.key_file_path)
        self.passphrase_edit.setText(self.connection.passphrase)
        
        # 고급 설정
        self.timeout_spin.setValue(self.connection.timeout)
        self.keep_alive_check.setChecked(self.connection.keep_alive)
        self.compression_check.setChecked(self.connection.compression)
        self.terminal_type_combo.setCurrentText(self.connection.terminal_type)
        self.encoding_combo.setCurrentText(self.connection.encoding)
        
        self.proxy_host_edit.setText(self.connection.proxy_host)
        self.proxy_port_spin.setValue(self.connection.proxy_port)
        self.proxy_username_edit.setText(self.connection.proxy_username)
        self.proxy_password_edit.setText(self.connection.proxy_password)
    
    @Slot()
    def _validate_and_accept(self):
        """유효성 검사 후 승인"""
        # 기본 필드 검증
        if not self.host_edit.text().strip():
            QMessageBox.warning(self, '입력 오류', '호스트를 입력하세요.')
            return
        
        if not self.username_edit.text().strip():
            QMessageBox.warning(self, '입력 오류', '사용자명을 입력하세요.')
            return
        
        # 인증 방법별 검증
        auth_method = self.auth_method_combo.currentText()
        if auth_method == '비밀번호' and not self.password_edit.text():
            QMessageBox.warning(self, '입력 오류', '비밀번호를 입력하세요.')
            return
        
        if auth_method == '키 파일' and not self.key_file_edit.text().strip():
            QMessageBox.warning(self, '입력 오류', '키 파일을 선택하세요.')
            return
        
        self.accept()
    
    def get_connection(self) -> SSHConnection:
        """연결 정보 반환"""
        # 인증 방법 매핑
        auth_method_map = {
            '비밀번호': AuthMethod.PASSWORD,
            '키 파일': AuthMethod.KEY_FILE,
            '키 에이전트': AuthMethod.KEY_AGENT
        }
        
        if self.is_editing and self.connection:
            # 기존 연결 수정
            connection = self.connection
        else:
            # 새 연결 생성
            connection = SSHConnection(
                name=self.name_edit.text().strip(),
                host=self.host_edit.text().strip(),
                username=self.username_edit.text().strip()
            )
        
        # 기본 설정 업데이트
        connection.name = self.name_edit.text().strip() or f"{self.username_edit.text()}@{self.host_edit.text()}"
        connection.host = self.host_edit.text().strip()
        connection.port = self.port_spin.value()
        connection.username = self.username_edit.text().strip()
        
        # 인증 설정 업데이트
        connection.auth_method = auth_method_map[self.auth_method_combo.currentText()]
        connection.password = self.password_edit.text()
        connection.key_file_path = self.key_file_edit.text().strip()
        connection.passphrase = self.passphrase_edit.text()
        
        # 고급 설정 업데이트
        connection.timeout = self.timeout_spin.value()
        connection.keep_alive = self.keep_alive_check.isChecked()
        connection.compression = self.compression_check.isChecked()
        connection.terminal_type = self.terminal_type_combo.currentText()
        connection.encoding = self.encoding_combo.currentText()
        
        connection.proxy_host = self.proxy_host_edit.text().strip()
        connection.proxy_port = self.proxy_port_spin.value()
        connection.proxy_username = self.proxy_username_edit.text().strip()
        connection.proxy_password = self.proxy_password_edit.text()
        
        return connection


class ConnectionManagerWidget(QWidget):
    """연결 관리자 위젯"""
    
    # 시그널 정의
    connection_requested = Signal(SSHConnection)
    connection_deleted = Signal(str)  # connection_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 설정 관리자
        self.config_manager = ConfigManager()
        
        # 연결 목록
        self.connections: Dict[str, SSHConnection] = {}
        
        # 로깅
        self.logger = logging.getLogger(__name__)
        
        # UI 설정
        self._setup_ui()
        
        # 연결 목록 로드
        self._load_connections()
    
    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        
        # 제목
        title_label = QLabel('SSH 연결 관리자')
        title_label.setStyleSheet('font-weight: bold; font-size: 14px; padding: 5px;')
        layout.addWidget(title_label)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        self.new_btn = QPushButton('새 연결')
        self.new_btn.clicked.connect(self.show_new_connection_dialog)
        button_layout.addWidget(self.new_btn)
        
        self.edit_btn = QPushButton('편집')
        self.edit_btn.clicked.connect(self._edit_connection)
        self.edit_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton('삭제')
        self.delete_btn.clicked.connect(self._delete_connection)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)
        
        layout.addLayout(button_layout)
        
        # 연결 목록
        self.connection_model = QStandardItemModel()
        self.connection_list = QListView()
        self.connection_list.setModel(self.connection_model)
        self.connection_list.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.connection_list.doubleClicked.connect(self._connect_to_selected)
        
        layout.addWidget(self.connection_list)
        
        # 연결 버튼
        self.connect_btn = QPushButton('연결')
        self.connect_btn.clicked.connect(self._connect_to_selected)
        self.connect_btn.setEnabled(False)
        layout.addWidget(self.connect_btn)
    
    def _load_connections(self):
        """저장된 연결 목록 로드"""
        try:
            # JSON 문자열로 저장된 연결 목록을 가져옴
            connections_json = self.config_manager.get_config_value('ssh', 'connections', '[]')
            connections_data = json.loads(connections_json) if connections_json else []
            
            for conn_data in connections_data:
                connection = SSHConnection.from_dict(conn_data)
                self.connections[connection.connection_id] = connection
                self._add_connection_to_model(connection)
            
            self.logger.info(f"연결 목록 로드 완료: {len(self.connections)}개")
            
        except Exception as e:
            self.logger.error(f"연결 목록 로드 실패: {e}")
    
    def _save_connections(self):
        """연결 목록 저장"""
        try:
            connections_data = [conn.to_dict() for conn in self.connections.values()]
            connections_json = json.dumps(connections_data, ensure_ascii=False, indent=2)
            self.config_manager.set_config_value('ssh', 'connections', connections_json)
            self.config_manager.app_config_manager.save_config()
            
            self.logger.info(f"연결 목록 저장 완료: {len(self.connections)}개")
            
        except Exception as e:
            self.logger.error(f"연결 목록 저장 실패: {e}")
    
    def _add_connection_to_model(self, connection: SSHConnection):
        """모델에 연결 추가"""
        item = QStandardItem(connection.get_display_name())
        item.setData(connection.connection_id, Qt.ItemDataRole.UserRole)
        
        # 연결 상태에 따른 아이콘 설정
        if connection.status == ConnectionStatus.CONNECTED:
            item.setData('🟢', Qt.ItemDataRole.DecorationRole)
        elif connection.status == ConnectionStatus.CONNECTING:
            item.setData('🟡', Qt.ItemDataRole.DecorationRole)
        elif connection.status == ConnectionStatus.FAILED:
            item.setData('🔴', Qt.ItemDataRole.DecorationRole)
        else:
            item.setData('⚪', Qt.ItemDataRole.DecorationRole)
        
        self.connection_model.appendRow(item)
    
    def _get_selected_connection(self) -> Optional[SSHConnection]:
        """선택된 연결 반환"""
        selection = self.connection_list.selectionModel().selectedIndexes()
        if not selection:
            return None
        
        index = selection[0]
        connection_id = self.connection_model.itemFromIndex(index).data(Qt.ItemDataRole.UserRole)
        return self.connections.get(connection_id)
    
    @Slot()
    def _on_selection_changed(self):
        """선택 변경 처리"""
        has_selection = bool(self.connection_list.selectionModel().selectedIndexes())
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.connect_btn.setEnabled(has_selection)
    
    @Slot()
    def show_new_connection_dialog(self):
        """새 연결 대화상자 표시"""
        dialog = NewConnectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            connection = dialog.get_connection()
            
            # 연결 유효성 검사
            is_valid, error_msg = connection.validate()
            if not is_valid:
                QMessageBox.warning(self, '연결 정보 오류', error_msg)
                return
            
            # 연결 추가
            self.connections[connection.connection_id] = connection
            self._add_connection_to_model(connection)
            self._save_connections()
            
            self.logger.info(f"새 연결 추가: {connection.get_display_name()}")
    
    @Slot()
    def _edit_connection(self):
        """연결 편집"""
        connection = self._get_selected_connection()
        if not connection:
            return
        
        dialog = NewConnectionDialog(self, connection)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_connection = dialog.get_connection()
            
            # 연결 유효성 검사
            is_valid, error_msg = updated_connection.validate()
            if not is_valid:
                QMessageBox.warning(self, '연결 정보 오류', error_msg)
                return
            
            # 연결 업데이트
            self.connections[connection.connection_id] = updated_connection
            self._refresh_connection_list()
            self._save_connections()
            
            self.logger.info(f"연결 편집: {updated_connection.get_display_name()}")
    
    @Slot()
    def _delete_connection(self):
        """연결 삭제"""
        connection = self._get_selected_connection()
        if not connection:
            return
        
        reply = QMessageBox.question(
            self,
            '연결 삭제',
            f"'{connection.get_display_name()}' 연결을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 연결 삭제
            del self.connections[connection.connection_id]
            self._refresh_connection_list()
            self._save_connections()
            
            # 삭제 시그널 발송
            self.connection_deleted.emit(connection.connection_id)
            
            self.logger.info(f"연결 삭제: {connection.get_display_name()}")
    
    @Slot()
    def _connect_to_selected(self):
        """선택된 연결로 연결"""
        connection = self._get_selected_connection()
        if connection:
            self.connection_requested.emit(connection)
    
    def _refresh_connection_list(self):
        """연결 목록 새로고침"""
        self.connection_model.clear()
        for connection in self.connections.values():
            self._add_connection_to_model(connection)
    
    @Slot(SSHConnection)
    def add_connection(self, connection: SSHConnection):
        """연결 추가 (외부에서 호출)"""
        if connection.connection_id not in self.connections:
            self.connections[connection.connection_id] = connection
            self._add_connection_to_model(connection)
            self._save_connections()
    
    @Slot(str)
    def remove_connection(self, connection_id: str):
        """연결 제거 (외부에서 호출)"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self._refresh_connection_list()
            self._save_connections()
    
    def update_connection_status(self, connection_id: str, status: ConnectionStatus):
        """연결 상태 업데이트"""
        if connection_id in self.connections:
            self.connections[connection_id].status = status
            self._refresh_connection_list()
