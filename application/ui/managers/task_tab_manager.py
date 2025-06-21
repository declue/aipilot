"""작업 스케줄링 탭 관리자"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from application.tasks.models.task_config import TaskConfig
from application.util.logger import setup_logger

logger = setup_logger("task_tab_manager") or logging.getLogger(__name__)


class TaskDialog(QDialog):
    """작업 추가/편집 다이얼로그"""
    
    def __init__(self, parent=None, task: Optional[TaskConfig] = None):
        super().__init__(parent)
        self.task = task
        self.is_edit_mode = task is not None
        
        self.setWindowTitle("작업 편집" if self.is_edit_mode else "새 작업 추가")
        self.setModal(True)
        self.resize(500, 600)
        
        self.setup_ui()
        
        if self.is_edit_mode:
            self.load_task_data()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        
        # 기본 정보
        basic_group = QGroupBox("기본 정보")
        basic_layout = QFormLayout(basic_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("작업 이름")
        basic_layout.addRow("이름:", self.name_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("작업 설명")
        self.description_edit.setMaximumHeight(80)
        basic_layout.addRow("설명:", self.description_edit)
        
        self.enabled_check = QCheckBox("활성화")
        self.enabled_check.setChecked(True)
        basic_layout.addRow("상태:", self.enabled_check)
        
        layout.addWidget(basic_group)
        
        # 스케줄 설정
        schedule_group = QGroupBox("스케줄 설정")
        schedule_layout = QFormLayout(schedule_group)
        
        self.cron_edit = QLineEdit()
        self.cron_edit.setPlaceholderText("예: 0 10 * * * (매일 10시)")
        schedule_layout.addRow("Cron 표현식:", self.cron_edit)
        
        # Cron 도움말
        cron_help = QLabel("Cron 형식: 분 시 일 월 요일\n예시:\n• 0 10 * * * - 매일 10시\n• 0 9 * * 1-5 - 평일 9시\n• 30 14 * * 0 - 일요일 14시 30분")
        cron_help.setStyleSheet("color: #666; font-size: 11px;")
        schedule_layout.addRow("", cron_help)
        
        layout.addWidget(schedule_group)
        
        # 작업 설정
        action_group = QGroupBox("작업 설정")
        action_layout = QFormLayout(action_group)
        
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems(["llm_request", "api_call", "notification"])
        self.action_type_combo.currentTextChanged.connect(self.on_action_type_changed)
        action_layout.addRow("작업 타입:", self.action_type_combo)
        
        # 작업별 파라미터 위젯
        self.params_widget = QWidget()
        self.params_layout = QVBoxLayout(self.params_widget)
        action_layout.addRow("파라미터:", self.params_widget)
        
        layout.addWidget(action_group)
        
        # 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 초기 파라미터 위젯 설정
        self.on_action_type_changed("llm_request")
    
    def on_action_type_changed(self, action_type: str):
        """작업 타입 변경 시 파라미터 위젯 업데이트"""
        # 기존 위젯 제거
        for i in reversed(range(self.params_layout.count())):
            child = self.params_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        if action_type == "llm_request":
            self.setup_llm_params()
        elif action_type == "api_call":
            self.setup_api_params()
        elif action_type == "notification":
            self.setup_notification_params()
    
    def setup_llm_params(self):
        """LLM 요청 파라미터 설정"""
        layout = QFormLayout()
        
        self.llm_prompt_edit = QTextEdit()
        self.llm_prompt_edit.setPlaceholderText("LLM에게 보낼 질문이나 프롬프트")
        self.llm_prompt_edit.setMaximumHeight(100)
        layout.addRow("프롬프트:", self.llm_prompt_edit)
        
        self.llm_url_edit = QLineEdit("http://127.0.0.1:8000/llm/request")
        layout.addRow("API URL:", self.llm_url_edit)
        
        self.llm_stream_check = QCheckBox("스트리밍")
        layout.addRow("옵션:", self.llm_stream_check)
        
        widget = QWidget()
        widget.setLayout(layout)
        self.params_layout.addWidget(widget)
    
    def setup_api_params(self):
        """API 호출 파라미터 설정"""
        layout = QFormLayout()
        
        self.api_url_edit = QLineEdit()
        self.api_url_edit.setPlaceholderText("http://example.com/api")
        layout.addRow("URL:", self.api_url_edit)
        
        self.api_method_combo = QComboBox()
        self.api_method_combo.addItems(["GET", "POST"])
        layout.addRow("메서드:", self.api_method_combo)
        
        self.api_headers_edit = QTextEdit()
        self.api_headers_edit.setPlaceholderText('{"Content-Type": "application/json"}')
        self.api_headers_edit.setMaximumHeight(60)
        layout.addRow("헤더:", self.api_headers_edit)
        
        self.api_payload_edit = QTextEdit()
        self.api_payload_edit.setPlaceholderText('{"key": "value"}')
        self.api_payload_edit.setMaximumHeight(80)
        layout.addRow("페이로드:", self.api_payload_edit)
        
        widget = QWidget()
        widget.setLayout(layout)
        self.params_layout.addWidget(widget)
    
    def setup_notification_params(self):
        """알림 파라미터 설정"""
        layout = QFormLayout()
        
        self.noti_title_edit = QLineEdit()
        self.noti_title_edit.setPlaceholderText("알림 제목")
        layout.addRow("제목:", self.noti_title_edit)
        
        self.noti_message_edit = QTextEdit()
        self.noti_message_edit.setPlaceholderText("알림 메시지")
        self.noti_message_edit.setMaximumHeight(80)
        layout.addRow("메시지:", self.noti_message_edit)
        
        self.noti_type_combo = QComboBox()
        self.noti_type_combo.addItems(["info", "warning", "error"])
        layout.addRow("타입:", self.noti_type_combo)
        
        self.noti_url_edit = QLineEdit("http://127.0.0.1:8000/notifications/info")
        layout.addRow("API URL:", self.noti_url_edit)
        
        widget = QWidget()
        widget.setLayout(layout)
        self.params_layout.addWidget(widget)
    
    def load_task_data(self):
        """기존 작업 데이터 로드"""
        if not self.task:
            return
        
        self.name_edit.setText(self.task.name)
        self.description_edit.setPlainText(self.task.description)
        self.enabled_check.setChecked(self.task.enabled)
        self.cron_edit.setText(self.task.cron_expression)
        
        # 작업 타입 설정
        index = self.action_type_combo.findText(self.task.action_type)
        if index >= 0:
            self.action_type_combo.setCurrentIndex(index)
        
        # 파라미터 로드
        params = self.task.action_params
        action_type = self.task.action_type
        
        if action_type == "llm_request":
            if hasattr(self, 'llm_prompt_edit'):
                self.llm_prompt_edit.setPlainText(params.get("prompt", ""))
                self.llm_url_edit.setText(params.get("api_url", "http://127.0.0.1:8000/llm/request"))
                self.llm_stream_check.setChecked(params.get("stream", False))
        elif action_type == "api_call":
            if hasattr(self, 'api_url_edit'):
                self.api_url_edit.setText(params.get("url", ""))
                method_index = self.api_method_combo.findText(params.get("method", "GET"))
                if method_index >= 0:
                    self.api_method_combo.setCurrentIndex(method_index)
                self.api_headers_edit.setPlainText(str(params.get("headers", {})))
                self.api_payload_edit.setPlainText(str(params.get("payload", {})))
        elif action_type == "notification":
            if hasattr(self, 'noti_title_edit'):
                self.noti_title_edit.setText(params.get("title", ""))
                self.noti_message_edit.setPlainText(params.get("message", ""))
                type_index = self.noti_type_combo.findText(params.get("type", "info"))
                if type_index >= 0:
                    self.noti_type_combo.setCurrentIndex(type_index)
                self.noti_url_edit.setText(params.get("api_url", "http://127.0.0.1:8000/notifications/info"))
    
    def get_task_config(self) -> TaskConfig:
        """폼 데이터로부터 TaskConfig 생성"""
        task_id = self.task.id if self.task else str(uuid.uuid4())
        
        # 기본 정보
        name = self.name_edit.text().strip()
        description = self.description_edit.toPlainText().strip()
        enabled = self.enabled_check.isChecked()
        cron_expression = self.cron_edit.text().strip()
        action_type = self.action_type_combo.currentText()
        
        # 파라미터 수집
        action_params = {}
        
        if action_type == "llm_request":
            action_params = {
                "prompt": self.llm_prompt_edit.toPlainText().strip(),
                "api_url": self.llm_url_edit.text().strip(),
                "stream": self.llm_stream_check.isChecked()
            }
        elif action_type == "api_call":
            try:
                import json
                headers = json.loads(self.api_headers_edit.toPlainText().strip() or "{}")
                payload = json.loads(self.api_payload_edit.toPlainText().strip() or "{}")
            except json.JSONDecodeError:
                headers = {}
                payload = {}
            
            action_params = {
                "url": self.api_url_edit.text().strip(),
                "method": self.api_method_combo.currentText(),
                "headers": headers,
                "payload": payload
            }
        elif action_type == "notification":
            action_params = {
                "title": self.noti_title_edit.text().strip(),
                "message": self.noti_message_edit.toPlainText().strip(),
                "type": self.noti_type_combo.currentText(),
                "api_url": self.noti_url_edit.text().strip()
            }
        
        # TaskConfig 생성
        if self.is_edit_mode:
            task_config = TaskConfig(
                id=task_id,
                name=name,
                description=description,
                cron_expression=cron_expression,
                action_type=action_type,
                action_params=action_params,
                enabled=enabled,
                created_at=self.task.created_at if self.task else None,
                last_run=self.task.last_run if self.task else None,
                run_count=self.task.run_count if self.task else 0
            )
        else:
            task_config = TaskConfig(
                id=task_id,
                name=name,
                description=description,
                cron_expression=cron_expression,
                action_type=action_type,
                action_params=action_params,
                enabled=enabled
            )
        
        return task_config
    
    def validate_form(self) -> bool:
        """폼 유효성 검사"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "오류", "작업 이름을 입력해주세요.")
            return False
        
        if not self.cron_edit.text().strip():
            QMessageBox.warning(self, "오류", "Cron 표현식을 입력해주세요.")
            return False
        
        action_type = self.action_type_combo.currentText()
        
        if action_type == "llm_request":
            if not self.llm_prompt_edit.toPlainText().strip():
                QMessageBox.warning(self, "오류", "LLM 프롬프트를 입력해주세요.")
                return False
        elif action_type == "api_call":
            if not self.api_url_edit.text().strip():
                QMessageBox.warning(self, "오류", "API URL을 입력해주세요.")
                return False
        elif action_type == "notification":
            if not self.noti_message_edit.toPlainText().strip():
                QMessageBox.warning(self, "오류", "알림 메시지를 입력해주세요.")
                return False
        
        return True
    
    def accept(self):
        """확인 버튼 클릭"""
        if self.validate_form():
            super().accept()


class TaskTabManager:
    """작업 스케줄링 탭 관리자"""
    
    def __init__(self, settings_window):
        self.settings_window = settings_window
        self.task_thread = None  # TaskThread 참조
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_task_list)
        self.refresh_timer.start(5000)  # 5초마다 새로고침
    
    def create_task_tab(self) -> QWidget:
        """작업 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 상단 컨트롤
        self.create_controls(layout)
        
        # 분할 패널
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 작업 목록 (좌측)
        self.create_task_list(splitter)
        
        # 상세 정보 (우측)
        self.create_task_details(splitter)
        
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)
        
        return tab
    
    def create_controls(self, layout):
        """상단 컨트롤 생성"""
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        
        # 스케줄러 상태
        self.scheduler_status_label = QLabel("스케줄러: 중지됨")
        self.scheduler_status_label.setStyleSheet("font-weight: bold; color: #dc3545;")
        controls_layout.addWidget(self.scheduler_status_label)
        
        controls_layout.addStretch()
        
        # 버튼들
        self.start_button = QPushButton("📅 스케줄러 시작")
        self.start_button.clicked.connect(self.start_scheduler)
        controls_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏹️ 스케줄러 중지")
        self.stop_button.clicked.connect(self.stop_scheduler)
        self.stop_button.setEnabled(False)
        controls_layout.addWidget(self.stop_button)
        
        self.add_button = QPushButton("➕ 작업 추가")
        self.add_button.clicked.connect(self.add_task)
        controls_layout.addWidget(self.add_button)
        
        self.edit_button = QPushButton("✏️ 편집")
        self.edit_button.clicked.connect(self.edit_task)
        self.edit_button.setEnabled(False)
        controls_layout.addWidget(self.edit_button)
        
        self.delete_button = QPushButton("🗑️ 삭제")
        self.delete_button.clicked.connect(self.delete_task)
        self.delete_button.setEnabled(False)
        controls_layout.addWidget(self.delete_button)
        
        layout.addWidget(controls_frame)
    
    def create_task_list(self, parent):
        """작업 목록 테이블 생성"""
        list_frame = QFrame()
        list_layout = QVBoxLayout(list_frame)
        
        list_label = QLabel("📋 작업 목록")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        list_layout.addWidget(list_label)
        
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(6)
        self.task_table.setHorizontalHeaderLabels([
            "이름", "상태", "스케줄", "마지막 실행", "실행 횟수", "다음 실행"
        ])
        
        # 테이블 설정
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.itemSelectionChanged.connect(self.on_task_selected)
        self.task_table.itemDoubleClicked.connect(self.edit_task)
        
        list_layout.addWidget(self.task_table)
        parent.addWidget(list_frame)
    
    def create_task_details(self, parent):
        """작업 상세 정보 패널 생성"""
        details_frame = QFrame()
        details_layout = QVBoxLayout(details_frame)
        
        details_label = QLabel("📄 작업 상세 정보")
        details_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        details_layout.addWidget(details_label)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        details_layout.addWidget(self.details_text)
        
        # 실행 중인 작업들
        running_label = QLabel("⚡ 실행 중인 작업")
        running_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        details_layout.addWidget(running_label)
        
        self.running_table = QTableWidget()
        self.running_table.setColumnCount(3)
        self.running_table.setHorizontalHeaderLabels(["작업명", "다음 실행", "트리거"])
        
        running_header = self.running_table.horizontalHeader()
        running_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        running_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        running_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        details_layout.addWidget(self.running_table)
        
        parent.addWidget(details_frame)
    
    def set_task_thread(self, task_thread):
        """TaskThread 참조 설정"""
        self.task_thread = task_thread
        
        if task_thread:
            # 시그널 연결
            task_thread.scheduler_started.connect(self.on_scheduler_started)
            task_thread.scheduler_stopped.connect(self.on_scheduler_stopped)
            task_thread.task_executed.connect(self.on_task_executed)
            task_thread.task_error.connect(self.on_task_error)
        
        # 초기 데이터 로드
        self.refresh_task_list()
    
    def start_scheduler(self):
        """스케줄러 시작"""
        if not self.task_thread:
            # TaskThread가 없으면 새로 생성
            from application.tasks.task_thread import TaskThread
            self.task_thread = TaskThread()
            self.set_task_thread(self.task_thread)
            self.task_thread.start()
        else:
            # 이미 있으면 활성화
            self.task_thread.set_scheduler_enabled(True)
        
        logger.info("스케줄러 시작 요청")
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        if self.task_thread:
            self.task_thread.set_scheduler_enabled(False)
        
        logger.info("스케줄러 중지 요청")
    
    def on_scheduler_started(self):
        """스케줄러 시작됨"""
        self.scheduler_status_label.setText("스케줄러: 실행 중")
        self.scheduler_status_label.setStyleSheet("font-weight: bold; color: #28a745;")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.refresh_task_list()
        logger.info("스케줄러가 시작되었습니다")
    
    def on_scheduler_stopped(self):
        """스케줄러 중지됨"""
        self.scheduler_status_label.setText("스케줄러: 중지됨")
        self.scheduler_status_label.setStyleSheet("font-weight: bold; color: #dc3545;")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.refresh_task_list()
        logger.info("스케줄러가 중지되었습니다")
    
    def on_task_executed(self, task_id: str, event):
        """작업 실행 완료"""
        logger.info(f"작업 실행 완료: {task_id}")
        self.refresh_task_list()
    
    def on_task_error(self, task_id: str, event):
        """작업 실행 오류"""
        logger.error(f"작업 실행 오류: {task_id}")
        self.refresh_task_list()
    
    def add_task(self):
        """작업 추가"""
        dialog = TaskDialog(self.settings_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            task_config = dialog.get_task_config()
            if self.task_thread:
                success = self.task_thread.add_task(task_config)
                if success:
                    self.refresh_task_list()
                    QMessageBox.information(self.settings_window, "성공", "작업이 추가되었습니다.")
                else:
                    QMessageBox.warning(self.settings_window, "오류", "작업 추가에 실패했습니다.")
    
    def edit_task(self):
        """작업 편집"""
        selected_items = self.task_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        task_id = self.task_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if self.task_thread:
            task = self.task_thread.get_task(task_id)
            if task:
                dialog = TaskDialog(self.settings_window, task)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    updated_task = dialog.get_task_config()
                    success = self.task_thread.update_task(updated_task)
                    if success:
                        self.refresh_task_list()
                        QMessageBox.information(self.settings_window, "성공", "작업이 수정되었습니다.")
                    else:
                        QMessageBox.warning(self.settings_window, "오류", "작업 수정에 실패했습니다.")
    
    def delete_task(self):
        """작업 삭제"""
        selected_items = self.task_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        task_name = self.task_table.item(row, 0).text()
        task_id = self.task_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self.settings_window,
            "작업 삭제",
            f"'{task_name}' 작업을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.task_thread:
                success = self.task_thread.remove_task(task_id)
                if success:
                    self.refresh_task_list()
                    QMessageBox.information(self.settings_window, "성공", "작업이 삭제되었습니다.")
                else:
                    QMessageBox.warning(self.settings_window, "오류", "작업 삭제에 실패했습니다.")
    
    def on_task_selected(self):
        """작업 선택 시"""
        selected_items = self.task_table.selectedItems()
        has_selection = len(selected_items) > 0
        
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        
        if has_selection:
            row = selected_items[0].row()
            task_id = self.task_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.show_task_details(task_id)
    
    def show_task_details(self, task_id: str):
        """작업 상세 정보 표시"""
        if not self.task_thread:
            return
        
        task = self.task_thread.get_task(task_id)
        if not task:
            return
        
        details = f"""작업 ID: {task.id}
이름: {task.name}
설명: {task.description}
상태: {'활성화' if task.enabled else '비활성화'}
Cron 표현식: {task.cron_expression}
작업 타입: {task.action_type}
생성일: {task.created_at}
마지막 실행: {task.last_run or '없음'}
실행 횟수: {task.run_count}

작업 파라미터:
{self._format_params(task.action_params)}"""
        
        self.details_text.setPlainText(details)
    
    def _format_params(self, params: dict) -> str:
        """파라미터 포맷팅"""
        lines = []
        for key, value in params.items():
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)
    
    def refresh_task_list(self):
        """작업 목록 새로고침"""
        if not self.task_thread:
            return
        
        tasks = self.task_thread.get_tasks()
        running_jobs = self.task_thread.get_running_jobs()
        
        # 작업 목록 테이블 업데이트
        self.task_table.setRowCount(len(tasks))
        
        for row, (task_id, task) in enumerate(tasks.items()):
            # 이름
            name_item = QTableWidgetItem(task.name)
            name_item.setData(Qt.ItemDataRole.UserRole, task_id)
            self.task_table.setItem(row, 0, name_item)
            
            # 상태
            status = "✅ 활성화" if task.enabled else "❌ 비활성화"
            self.task_table.setItem(row, 1, QTableWidgetItem(status))
            
            # 스케줄
            self.task_table.setItem(row, 2, QTableWidgetItem(task.cron_expression))
            
            # 마지막 실행
            last_run = task.last_run
            if last_run:
                try:
                    dt = datetime.fromisoformat(last_run)
                    last_run_str = dt.strftime("%m-%d %H:%M")
                except:
                    last_run_str = "오류"
            else:
                last_run_str = "없음"
            self.task_table.setItem(row, 3, QTableWidgetItem(last_run_str))
            
            # 실행 횟수
            self.task_table.setItem(row, 4, QTableWidgetItem(str(task.run_count)))
            
            # 다음 실행 (실행 중인 작업에서 찾기)
            next_run = "없음"
            for job in running_jobs:
                if job["id"] == task_id and job["next_run"]:
                    try:
                        dt = datetime.fromisoformat(job["next_run"])
                        next_run = dt.strftime("%m-%d %H:%M")
                    except:
                        next_run = "오류"
                    break
            self.task_table.setItem(row, 5, QTableWidgetItem(next_run))
        
        # 실행 중인 작업 테이블 업데이트
        self.running_table.setRowCount(len(running_jobs))
        
        for row, job in enumerate(running_jobs):
            self.running_table.setItem(row, 0, QTableWidgetItem(job["name"] or job["id"]))
            
            next_run = job["next_run"]
            if next_run:
                try:
                    dt = datetime.fromisoformat(next_run)
                    next_run_str = dt.strftime("%m-%d %H:%M:%S")
                except:
                    next_run_str = "오류"
            else:
                next_run_str = "없음"
            self.running_table.setItem(row, 1, QTableWidgetItem(next_run_str))
            
            self.running_table.setItem(row, 2, QTableWidgetItem(str(job["trigger"])))
    
    def cleanup(self):
        """정리 작업"""
        if self.refresh_timer:
            self.refresh_timer.stop()
        
        if self.task_thread:
            self.task_thread.stop_scheduler()
            self.task_thread.quit()
            self.task_thread.wait()

    def update_theme(self):
        """테마 업데이트"""
        try:
            if hasattr(self.settings_window, 'theme_manager'):
                colors = self.settings_window.theme_manager.get_theme_colors()
                
                # 테이블 위젯들 테마 업데이트
                self._update_table_themes(colors)
                self._update_text_edit_themes(colors)
                
        except Exception as e:
            print(f"작업 탭 테마 업데이트 실패: {e}")

    def _update_table_themes(self, colors):
        """테이블 위젯 테마 업데이트"""
        table_style = f"""
            QTableWidget {{
                background-color: {colors['background']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                gridline-color: {colors['border_light']};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {colors['border_light']};
            }}
            QTableWidget::item:selected {{
                background-color: {colors['primary']}30;
                color: {colors['primary']};
            }}
            QHeaderView::section {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                padding: 8px;
                font-weight: 600;
            }}
        """
        
        if hasattr(self, 'task_table'):
            self.task_table.setStyleSheet(table_style)
        if hasattr(self, 'running_table'):
            self.running_table.setStyleSheet(table_style)

    def _update_text_edit_themes(self, colors):
        """텍스트 편집 위젯 테마 업데이트"""
        if hasattr(self, 'details_text'):
            self.details_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {colors['surface']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                    border-radius: 6px;
                    padding: 8px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 12px;
                }}
            """) 