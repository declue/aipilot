"""
SSH 터미널 관리 프로그램 메인 윈도우
"""
import logging
from typing import Dict

from PySide6.QtCore import QTimer, Signal, Slot, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from dspilot_core.config.config_manager import ConfigManager
from dspilot_shell.widgets.connection_manager import ConnectionManagerWidget
from dspilot_shell.widgets.terminal_widget import TerminalWidget
from dspilot_shell.models.ssh_connection import SSHConnection


class MainWindow(QMainWindow):
    """SSH 터미널 관리 메인 윈도우"""
    
    # 시그널 정의
    connection_added = Signal(SSHConnection)
    connection_removed = Signal(str)  # connection_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 설정 관리자 초기화
        self.config_manager = ConfigManager()
        
        # 터미널 탭 관리
        self.terminal_tabs: Dict[str, TerminalWidget] = {}
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        
        # UI 초기화
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_dock_widgets()
        
        # 이벤트 연결
        self._connect_signals()
        
        # 타이머 설정
        self._setup_timers()
        
        # 윈도우 설정
        self._setup_window()
        
        # 독 위젯 메뉴 추가 (초기화 완료 후)
        self._add_dock_widget_to_menu()
    
    def _setup_ui(self):
        """UI 초기화"""
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        
        # 스플리터로 좌우 분할
        self.main_splitter = QSplitter()
        main_layout.addWidget(self.main_splitter)
        
        # 터미널 탭 위젯
        self.terminal_tab_widget = QTabWidget()
        self.terminal_tab_widget.setTabsClosable(True)
        self.terminal_tab_widget.setMovable(True)
        self.terminal_tab_widget.tabCloseRequested.connect(self._close_terminal_tab)
        
        # 스플리터에 추가
        self.main_splitter.addWidget(self.terminal_tab_widget)
        
        # 초기 스플리터 비율 설정
        self.main_splitter.setSizes([800, 300])
    
    def _setup_menu_bar(self):
        """메뉴바 설정"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu('파일(&F)')
        
        # 새 연결
        self.new_connection_action = QAction('새 연결(&N)', self)
        self.new_connection_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_connection_action.triggered.connect(self._new_connection)
        file_menu.addAction(self.new_connection_action)
        
        file_menu.addSeparator()
        
        # 종료
        self.exit_action = QAction('종료(&X)', self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)
        
        # 편집 메뉴
        edit_menu = menubar.addMenu('편집(&E)')
        
        # 복사
        self.copy_action = QAction('복사(&C)', self)
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_action.triggered.connect(self._copy_terminal_selection)
        edit_menu.addAction(self.copy_action)
        
        # 붙여넣기
        self.paste_action = QAction('붙여넣기(&P)', self)
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        self.paste_action.triggered.connect(self._paste_to_terminal)
        edit_menu.addAction(self.paste_action)
        
        # 보기 메뉴
        view_menu = menubar.addMenu('보기(&V)')
        
        # 전체화면
        self.fullscreen_action = QAction('전체화면(&F)', self)
        self.fullscreen_action.setShortcut(QKeySequence.StandardKey.FullScreen)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(self.fullscreen_action)
        
        # 도구 메뉴
        tools_menu = menubar.addMenu('도구(&T)')
        
        # 설정
        self.settings_action = QAction('설정(&S)', self)
        self.settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(self.settings_action)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu('도움말(&H)')
        
        # 정보
        self.about_action = QAction('정보(&A)', self)
        self.about_action.triggered.connect(self._show_about)
        help_menu.addAction(self.about_action)
    
    def _setup_toolbar(self):
        """툴바 설정"""
        toolbar = QToolBar('메인 툴바')
        self.addToolBar(toolbar)
        
        # 새 연결 버튼
        toolbar.addAction(self.new_connection_action)
        toolbar.addSeparator()
        
        # 복사/붙여넣기 버튼
        toolbar.addAction(self.copy_action)
        toolbar.addAction(self.paste_action)
        toolbar.addSeparator()
        
        # 설정 버튼
        toolbar.addAction(self.settings_action)
    
    def _setup_status_bar(self):
        """상태바 설정"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 상태 메시지
        self.status_bar.showMessage('준비')
    
    def _setup_dock_widgets(self):
        """독 위젯 설정"""
        # 연결 관리자 독 위젯
        self.connection_dock = QDockWidget('연결 관리자', self)
        self.connection_manager = ConnectionManagerWidget()
        self.connection_dock.setWidget(self.connection_manager)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.connection_dock)
        
        # 보기 메뉴에 독 위젯 토글 추가
        # 초기화에서는 메뉴 참조를 나중에 하도록 함
    
    def _connect_signals(self):
        """시그널 연결"""
        # 연결 관리자 시그널 연결
        self.connection_manager.connection_requested.connect(self._create_terminal_connection)
        self.connection_manager.connection_deleted.connect(self._close_connection)
        
        # 내부 시그널 연결
        self.connection_added.connect(self.connection_manager.add_connection)
        self.connection_removed.connect(self.connection_manager.remove_connection)
    
    def _setup_timers(self):
        """타이머 설정"""
        # 상태 업데이트 타이머
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # 1초마다 업데이트
    
    def _setup_window(self):
        """윈도우 설정"""
        self.setWindowTitle('DSPilot SSH Terminal Manager')
        self.setGeometry(100, 100, 1200, 800)
        
        # 아이콘 설정 (있다면)
        try:
            icon_path = self.config_manager.get_config_value('ui', 'icon_path')
            if icon_path:
                self.setWindowIcon(QIcon(icon_path))
        except:
            pass
    
    @Slot()
    def _new_connection(self):
        """새 연결 생성"""
        self.connection_manager.show_new_connection_dialog()
    
    @Slot(SSHConnection)
    def _create_terminal_connection(self, connection: SSHConnection):
        """터미널 연결 생성"""
        try:
            # 새 터미널 위젯 생성
            terminal_widget = TerminalWidget(connection)
            
            # 탭에 추가
            tab_index = self.terminal_tab_widget.addTab(
                terminal_widget, 
                f"{connection.name} ({connection.host})"
            )
            
            # 터미널 딕셔너리에 추가
            self.terminal_tabs[connection.connection_id] = terminal_widget
            
            # 새 탭으로 전환
            self.terminal_tab_widget.setCurrentIndex(tab_index)
            
            # 연결 시도
            terminal_widget.connect_ssh()
            
            self.status_bar.showMessage(f'연결 생성됨: {connection.name}')
            
        except Exception as e:
            self.logger.error(f"터미널 연결 생성 실패: {e}")
            QMessageBox.critical(self, '오류', f'연결 생성에 실패했습니다: {str(e)}')
    
    @Slot(int)
    def _close_terminal_tab(self, index: int):
        """터미널 탭 닫기"""
        if index < 0 or index >= self.terminal_tab_widget.count():
            return
        
        widget = self.terminal_tab_widget.widget(index)
        if isinstance(widget, TerminalWidget):
            # 연결 해제
            widget.disconnect_ssh()
            
            # 딕셔너리에서 제거
            connection_id = widget.connection.connection_id
            if connection_id in self.terminal_tabs:
                del self.terminal_tabs[connection_id]
            
            # 탭 제거
            self.terminal_tab_widget.removeTab(index)
            
            self.status_bar.showMessage(f'연결 종료됨: {widget.connection.name}')
    
    @Slot(str)
    def _close_connection(self, connection_id: str):
        """연결 종료"""
        if connection_id in self.terminal_tabs:
            terminal_widget = self.terminal_tabs[connection_id]
            
            # 탭 인덱스 찾기
            for i in range(self.terminal_tab_widget.count()):
                if self.terminal_tab_widget.widget(i) == terminal_widget:
                    self._close_terminal_tab(i)
                    break
    
    @Slot()
    def _copy_terminal_selection(self):
        """터미널 선택 텍스트 복사"""
        current_widget = self.terminal_tab_widget.currentWidget()
        if isinstance(current_widget, TerminalWidget):
            current_widget.copy_selection()
    
    @Slot()
    def _paste_to_terminal(self):
        """터미널에 붙여넣기"""
        current_widget = self.terminal_tab_widget.currentWidget()
        if isinstance(current_widget, TerminalWidget):
            current_widget.paste_from_clipboard()
    
    @Slot()
    def _toggle_fullscreen(self):
        """전체화면 토글"""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_action.setChecked(False)
        else:
            self.showFullScreen()
            self.fullscreen_action.setChecked(True)
    
    @Slot()
    def _show_settings(self):
        """설정 대화상자 표시"""
        # TODO: 설정 대화상자 구현
        QMessageBox.information(self, '설정', '설정 기능은 구현 예정입니다.')
    
    @Slot()
    def _show_about(self):
        """정보 대화상자 표시"""
        QMessageBox.about(
            self, 
            'DSPilot SSH Terminal Manager 정보',
            'DSPilot SSH Terminal Manager v1.0\n\n'
            'PySide6 기반 SSH 터미널 관리 도구\n'
            'DSPilot Core를 활용한 제품 수준 터미널'
        )
    
    @Slot()
    def _update_status(self):
        """상태 업데이트"""
        # 활성 연결 수 표시
        active_connections = len(self.terminal_tabs)
        if active_connections > 0:
            self.status_bar.showMessage(f'활성 연결: {active_connections}개')
        else:
            self.status_bar.showMessage('준비')
    
    def closeEvent(self, event):
        """윈도우 닫기 이벤트"""
        # 모든 터미널 연결 종료
        for connection_id in list(self.terminal_tabs.keys()):
            terminal_widget = self.terminal_tabs[connection_id]
            terminal_widget.disconnect_ssh()
        
        # 설정 저장
        try:
            self.config_manager.save_config()
        except Exception as e:
            self.logger.error(f"설정 저장 실패: {e}")
        
        event.accept()
    
    def _add_dock_widget_to_menu(self):
        """독 위젯을 보기 메뉴에 추가"""
        try:
            # 보기 메뉴 찾기
            menubar = self.menuBar()
            for action in menubar.actions():
                if '보기' in action.text():
                    menu = action.menu()
                    if menu and isinstance(menu, QMenu):
                        menu.addSeparator()
                        menu.addAction(self.connection_dock.toggleViewAction())
                    break
        except Exception as e:
            self.logger.error(f"독 위젯 메뉴 추가 실패: {e}")
