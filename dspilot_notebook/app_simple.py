"""
DSPilot Notebook - Windows 11 스타일 메모장 애플리케이션 (간소화 버전)

기능:
- Windows 11 메모장과 동일한 텍스트 편집 기능
- 파일 저장/로드
- 문서 트리 관리 (RAG 서버 준비)
- 다크/라이트 테마 지원
- 자동 저장 기능
"""

import json
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QMenu, QFileDialog, QMessageBox,
    QSplitter, QTreeWidget, QTreeWidgetItem, QStatusBar,
    QTabWidget, QDialog, QFormLayout, QComboBox, 
    QSpinBox, QCheckBox, QDialogButtonBox, QInputDialog
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction, QKeySequence, QFont
)

# dspilot_core 임포트
sys.path.insert(0, str(Path(__file__).parent.parent))
from dspilot_core.config.unified_config_manager import UnifiedConfigManager
from dspilot_core.util.logger import setup_logger


logger = setup_logger("notebook") or logging.getLogger("notebook")


class DocumentNode:
    """문서 트리 노드"""
    
    def __init__(self, name: str, path: str = "", is_folder: bool = False):
        self.name = name
        self.path = path
        self.is_folder = is_folder
        self.children: List[DocumentNode] = []
        self.parent: Optional[DocumentNode] = None
        self.metadata: Dict[str, Any] = {
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "tags": [],
            "content_type": "text/plain"
        }


class DocumentTreeManager:
    """문서 트리 관리자 - RAG 서버 준비"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        self.root = DocumentNode("Workspace", str(self.workspace_path), True)
        self.index_file = self.workspace_path / ".dspilot_index.json"
        self.load_index()
    
    def load_index(self):
        """인덱스 파일 로드"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._build_tree_from_data(data, self.root)
            except Exception as e:
                logger.error(f"인덱스 로드 실패: {e}")
    
    def save_index(self):
        """인덱스 파일 저장"""
        try:
            data = self._tree_to_data(self.root)
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"인덱스 저장 실패: {e}")
    
    def _tree_to_data(self, node: DocumentNode) -> Dict:
        """트리를 딕셔너리로 변환"""
        return {
            "name": node.name,
            "path": node.path,
            "is_folder": node.is_folder,
            "metadata": node.metadata,
            "children": [self._tree_to_data(child) for child in node.children]
        }
    
    def _build_tree_from_data(self, data: Dict, parent: DocumentNode):
        """딕셔너리에서 트리 구축"""
        for child_data in data.get("children", []):
            child = DocumentNode(
                child_data["name"],
                child_data["path"],
                child_data["is_folder"]
            )
            child.metadata = child_data.get("metadata", {})
            child.parent = parent
            parent.children.append(child)
            self._build_tree_from_data(child_data, child)
    
    def add_document(self, name: str, content: str = "", parent: Optional[DocumentNode] = None) -> Optional[DocumentNode]:
        """문서 추가"""
        if parent is None:
            parent = self.root
        
        # 파일 경로 생성
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        if not safe_name.endswith('.txt'):
            safe_name += '.txt'
        
        file_path = Path(parent.path) / safe_name
        
        # 파일 저장
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            logger.error(f"파일 저장 실패: {e}")
            return None
        
        # 노드 생성
        node = DocumentNode(name, str(file_path), False)
        node.parent = parent
        parent.children.append(node)
        
        self.save_index()
        return node
    
    def add_folder(self, name: str, parent: Optional[DocumentNode] = None) -> DocumentNode:
        """폴더 추가"""
        if parent is None:
            parent = self.root
        
        # 폴더 경로 생성
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        folder_path = Path(parent.path) / safe_name
        folder_path.mkdir(exist_ok=True)
        
        # 노드 생성
        node = DocumentNode(name, str(folder_path), True)
        node.parent = parent
        parent.children.append(node)
        
        self.save_index()
        return node


class SettingsDialog(QDialog):
    """설정 대화상자"""
    
    def __init__(self, config_manager: UnifiedConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("설정")
        self.setModal(True)
        self.resize(400, 300)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 폼 레이아웃
        form_layout = QFormLayout()
        
        # 폰트 설정
        self.font_family = QComboBox()
        self.font_family.addItems([
            "Consolas", "Courier New", "Monaco", "Menlo",
            "Source Code Pro", "Ubuntu Mono", "JetBrains Mono"
        ])
        form_layout.addRow("폰트 패밀리:", self.font_family)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 32)
        self.font_size.setValue(12)
        form_layout.addRow("폰트 크기:", self.font_size)
        
        # 테마 설정
        self.theme = QComboBox()
        self.theme.addItems(["Light", "Dark"])
        form_layout.addRow("테마:", self.theme)
        
        # 자동 저장
        self.auto_save = QCheckBox()
        form_layout.addRow("자동 저장:", self.auto_save)
        
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(1, 60)
        self.auto_save_interval.setValue(5)
        self.auto_save_interval.setSuffix(" 분")
        form_layout.addRow("자동 저장 간격:", self.auto_save_interval)
        
        layout.addLayout(form_layout)
        
        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_settings(self):
        """설정 로드"""
        try:
            # 설정 로드 시도
            ui_config = {}
            self.font_family.setCurrentText(ui_config.get("font_family", "Consolas"))
            self.font_size.setValue(int(ui_config.get("font_size", "12")))
            self.theme.setCurrentText(ui_config.get("theme", "Light"))
            self.auto_save.setChecked(ui_config.get("auto_save", "true") == "true")
            self.auto_save_interval.setValue(int(ui_config.get("auto_save_interval", "5")))
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
    
    def get_settings(self) -> Dict[str, Any]:
        """설정 반환"""
        return {
            "font_family": self.font_family.currentText(),
            "font_size": self.font_size.value(),
            "theme": self.theme.currentText(),
            "auto_save": self.auto_save.isChecked(),
            "auto_save_interval": self.auto_save_interval.value()
        }


class TextEditor(QTextEdit):
    """향상된 텍스트 에디터"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_editor()
    
    def setup_editor(self):
        """에디터 설정"""
        # 폰트 설정
        font = QFont("Consolas", 12)
        self.setFont(font)
        
        # 줄 감싸기
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        
        # 탭 너비
        self.setTabStopDistance(40)
    
    def apply_theme(self, theme: str):
        """테마 적용"""
        if theme == "Dark":
            self.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 1px solid #3c3c3c;
                    selection-background-color: #264f78;
                }
            """)
        else:
            self.setStyleSheet("""
                QTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    selection-background-color: #3390ff;
                }
            """)


class DocumentTab(QWidget):
    """문서 탭"""
    
    content_changed = Signal()
    
    def __init__(self, document_node: Optional[DocumentNode] = None, parent=None):
        super().__init__(parent)
        self.document_node = document_node
        self.is_modified = False
        self.setup_ui()
        if document_node and document_node.path:
            self.load_content()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 텍스트 에디터
        self.editor = TextEditor()
        self.editor.textChanged.connect(self.on_content_changed)
        layout.addWidget(self.editor)
    
    def load_content(self):
        """파일 내용 로드"""
        if self.document_node and self.document_node.path:
            try:
                with open(self.document_node.path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.editor.setPlainText(content)
                    self.is_modified = False
            except Exception as e:
                logger.error(f"파일 로드 실패: {e}")
                QMessageBox.warning(self, "오류", f"파일을 불러올 수 없습니다: {e}")
    
    def save_content(self) -> bool:
        """내용 저장"""
        if not self.document_node or not self.document_node.path:
            return False
        
        try:
            with open(self.document_node.path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.is_modified = False
            if self.document_node:
                self.document_node.metadata["modified"] = datetime.now().isoformat()
            return True
        except Exception as e:
            logger.error(f"파일 저장 실패: {e}")
            QMessageBox.warning(self, "오류", f"파일을 저장할 수 없습니다: {e}")
            return False
    
    def on_content_changed(self):
        """내용 변경 시"""
        self.is_modified = True
        self.content_changed.emit()
    
    def apply_theme(self, theme: str):
        """테마 적용"""
        self.editor.apply_theme(theme)


class NotebookApplication(QMainWindow):
    """메인 애플리케이션 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        # 설정 관리자 초기화
        try:
            self.config_manager = UnifiedConfigManager()
        except Exception as e:
            logger.error(f"설정 관리자 초기화 실패: {e}")
            self.config_manager = None
        
        # 문서 트리 관리자 초기화
        workspace_path = os.path.expanduser("~/Documents/DSPilot_Notebook")
        self.doc_manager = DocumentTreeManager(workspace_path)
        
        # 자동 저장 타이머
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        
        self.setup_ui()
        self.setup_menus()
        self.setup_statusbar()
        self.load_settings()
        
        # 초기 문서
        self.new_document()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("DSPilot Notebook")
        self.setGeometry(100, 100, 1200, 800)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 스플리터
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # 문서 트리
        self.setup_document_tree()
        splitter.addWidget(self.tree_widget)
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        splitter.addWidget(self.tab_widget)
        
        # 스플리터 비율 설정
        splitter.setSizes([250, 950])
    
    def setup_document_tree(self):
        """문서 트리 설정"""
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("문서")
        self.tree_widget.itemDoubleClicked.connect(self.open_document_from_tree)
        
        # 컨텍스트 메뉴
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_tree_context_menu)
        
        self.refresh_document_tree()
    
    def refresh_document_tree(self):
        """문서 트리 새로고침"""
        self.tree_widget.clear()
        root_item = QTreeWidgetItem(self.tree_widget, [self.doc_manager.root.name])
        self._add_tree_items(self.doc_manager.root, root_item)
        self.tree_widget.expandAll()
    
    def _add_tree_items(self, node: DocumentNode, parent_item: QTreeWidgetItem):
        """트리 아이템 추가"""
        for child in node.children:
            item = QTreeWidgetItem(parent_item, [child.name])
            item.setData(0, Qt.ItemDataRole.UserRole, child)
            
            if child.is_folder:
                # 폴더 아이콘
                item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
                self._add_tree_items(child, item)
            else:
                # 파일 아이콘
                item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
    
    def show_tree_context_menu(self, position):
        """트리 컨텍스트 메뉴 표시"""
        item = self.tree_widget.itemAt(position)
        
        menu = QMenu(self)
        
        if item:
            node = item.data(0, Qt.ItemDataRole.UserRole)
            if node and node.is_folder:
                menu.addAction("새 문서", lambda: self.new_document_in_folder(node))
                menu.addAction("새 폴더", lambda: self.new_folder_in_folder(node))
                menu.addSeparator()
            menu.addAction("삭제", lambda: self.delete_node(item))
        else:
            menu.addAction("새 문서", lambda: self.new_document_in_folder(self.doc_manager.root))
            menu.addAction("새 폴더", lambda: self.new_folder_in_folder(self.doc_manager.root))
        
        if menu.actions():
            menu.exec(self.tree_widget.mapToGlobal(position))
    
    def setup_menus(self):
        """메뉴 설정"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일(&F)")
        
        new_action = QAction("새로 만들기(&N)", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_document)
        file_menu.addAction(new_action)
        
        open_action = QAction("열기(&O)", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_document)
        file_menu.addAction(open_action)
        
        save_action = QAction("저장(&S)", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_document)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("다른 이름으로 저장(&A)", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_document_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("끝내기(&X)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 편집 메뉴
        edit_menu = menubar.addMenu("편집(&E)")
        
        undo_action = QAction("실행 취소(&U)", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("다시 실행(&R)", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("잘라내기(&T)", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("복사(&C)", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("붙여넣기(&P)", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self.paste)
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        find_action = QAction("찾기(&F)", self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self.find_text)
        edit_menu.addAction(find_action)
        
        # 보기 메뉴
        view_menu = menubar.addMenu("보기(&V)")
        
        theme_menu = view_menu.addMenu("테마")
        
        light_theme_action = QAction("라이트 테마", self)
        light_theme_action.triggered.connect(lambda: self.apply_theme("Light"))
        theme_menu.addAction(light_theme_action)
        
        dark_theme_action = QAction("다크 테마", self)
        dark_theme_action.triggered.connect(lambda: self.apply_theme("Dark"))
        theme_menu.addAction(dark_theme_action)
        
        # 도구 메뉴
        tools_menu = menubar.addMenu("도구(&T)")
        
        settings_action = QAction("설정(&S)", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
    
    def setup_statusbar(self):
        """상태바 설정"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 문서 정보 라벨
        self.doc_info_label = QLabel("준비")
        self.status_bar.addWidget(self.doc_info_label)
        
        # 자동 저장 상태
        self.auto_save_label = QLabel()
        self.status_bar.addPermanentWidget(self.auto_save_label)
    
    def load_settings(self):
        """설정 로드"""
        try:
            # 기본 테마 적용
            self.apply_theme("Light")
            
            # 자동 저장 설정 (기본값)
            self.auto_save_timer.start(5 * 60 * 1000)  # 5분
            self.auto_save_label.setText("자동 저장: 5분")
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
    
    def apply_theme(self, theme: str):
        """테마 적용"""
        if theme == "Dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QMenuBar {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border-bottom: 1px solid #3c3c3c;
                }
                QMenuBar::item {
                    padding: 4px 8px;
                    background-color: transparent;
                }
                QMenuBar::item:selected {
                    background-color: #3c3c3c;
                }
                QMenu {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3c3c3c;
                }
                QMenu::item {
                    padding: 4px 20px;
                }
                QMenu::item:selected {
                    background-color: #3c3c3c;
                }
                QTabWidget::pane {
                    border: 1px solid #3c3c3c;
                    background-color: #1e1e1e;
                }
                QTabBar::tab {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    padding: 8px 16px;
                    border: 1px solid #3c3c3c;
                    border-bottom: none;
                }
                QTabBar::tab:selected {
                    background-color: #1e1e1e;
                }
                QTreeWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3c3c3c;
                }
                QTreeWidget::item:selected {
                    background-color: #264f78;
                }
                QStatusBar {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border-top: 1px solid #3c3c3c;
                }
            """)
        else:
            self.setStyleSheet("")
        
        # 모든 탭에 테마 적용
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, DocumentTab):
                tab.apply_theme(theme)
    
    def new_document(self):
        """새 문서"""
        tab = DocumentTab()
        index = self.tab_widget.addTab(tab, "새 문서")
        self.tab_widget.setCurrentIndex(index)
        tab.content_changed.connect(self.update_tab_title)
        return tab
    
    def new_document_in_folder(self, parent_node: DocumentNode):
        """폴더에 새 문서 생성"""
        name, ok = QInputDialog.getText(self, "새 문서", "문서 이름:")
        if ok and name:
            node = self.doc_manager.add_document(name, "", parent_node)
            if node:
                self.refresh_document_tree()
                self.open_document_node(node)
    
    def new_folder_in_folder(self, parent_node: DocumentNode):
        """폴더에 새 폴더 생성"""
        name, ok = QInputDialog.getText(self, "새 폴더", "폴더 이름:")
        if ok and name:
            node = self.doc_manager.add_folder(name, parent_node)
            if node:
                self.refresh_document_tree()
    
    def open_document(self):
        """문서 열기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "문서 열기", 
            str(self.doc_manager.workspace_path),
            "텍스트 파일 (*.txt);;모든 파일 (*.*)"
        )
        
        if file_path:
            # 기존에 열린 탭이 있는지 확인
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if (isinstance(tab, DocumentTab) and 
                    tab.document_node and 
                    tab.document_node.path == file_path):
                    self.tab_widget.setCurrentIndex(i)
                    return
            
            # 새 탭으로 열기
            node = DocumentNode(Path(file_path).name, file_path)
            tab = DocumentTab(node)
            index = self.tab_widget.addTab(tab, node.name)
            self.tab_widget.setCurrentIndex(index)
            tab.content_changed.connect(self.update_tab_title)
    
    def open_document_from_tree(self, item: QTreeWidgetItem):
        """트리에서 문서 열기"""
        node = item.data(0, Qt.ItemDataRole.UserRole)
        if node and not node.is_folder:
            self.open_document_node(node)
    
    def open_document_node(self, node: DocumentNode):
        """문서 노드 열기"""
        # 기존에 열린 탭이 있는지 확인
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if (isinstance(tab, DocumentTab) and 
                tab.document_node and 
                tab.document_node.path == node.path):
                self.tab_widget.setCurrentIndex(i)
                return
        
        # 새 탭으로 열기
        tab = DocumentTab(node)
        index = self.tab_widget.addTab(tab, node.name)
        self.tab_widget.setCurrentIndex(index)
        tab.content_changed.connect(self.update_tab_title)
    
    def save_document(self):
        """문서 저장"""
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, DocumentTab):
            if current_tab.document_node and current_tab.document_node.path:
                current_tab.save_content()
                self.update_tab_title()
            else:
                self.save_document_as()
    
    def save_document_as(self):
        """다른 이름으로 저장"""
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, DocumentTab):
            file_path, _ = QFileDialog.getSaveFileName(
                self, "다른 이름으로 저장",
                str(self.doc_manager.workspace_path),
                "텍스트 파일 (*.txt);;모든 파일 (*.*)"
            )
            
            if file_path:
                # 새 노드 생성
                node = DocumentNode(Path(file_path).name, file_path)
                current_tab.document_node = node
                
                # 저장
                if current_tab.save_content():
                    # 탭 제목 업데이트
                    index = self.tab_widget.currentIndex()
                    self.tab_widget.setTabText(index, node.name)
                    
                    # 문서 트리에 추가 (워크스페이스 내부인 경우)
                    if file_path.startswith(str(self.doc_manager.workspace_path)):
                        # TODO: 적절한 부모 찾기
                        self.doc_manager.root.children.append(node)
                        node.parent = self.doc_manager.root
                        self.doc_manager.save_index()
                        self.refresh_document_tree()
    
    def close_tab(self, index: int):
        """탭 닫기"""
        tab = self.tab_widget.widget(index)
        if isinstance(tab, DocumentTab) and tab.is_modified:
            reply = QMessageBox.question(
                self, "저장하지 않은 변경 사항",
                f"'{self.tab_widget.tabText(index)}'에 저장하지 않은 변경 사항이 있습니다.\n저장하시겠습니까?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.save_document()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        self.tab_widget.removeTab(index)
    
    def update_tab_title(self):
        """탭 제목 업데이트"""
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, DocumentTab):
            index = self.tab_widget.currentIndex()
            title = "새 문서"
            
            if current_tab.document_node:
                title = current_tab.document_node.name
            
            if current_tab.is_modified:
                title += " *"
            
            self.tab_widget.setTabText(index, title)
    
    def delete_node(self, item: QTreeWidgetItem):
        """노드 삭제"""
        node = item.data(0, Qt.ItemDataRole.UserRole)
        if not node:
            return
        
        reply = QMessageBox.question(
            self, "삭제 확인",
            f"'{node.name}'을(를) 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 파일/폴더 삭제
                path = Path(node.path)
                if path.exists():
                    if path.is_file():
                        path.unlink()
                    else:
                        import shutil
                        shutil.rmtree(path)
                
                # 트리에서 제거
                if node.parent:
                    node.parent.children.remove(node)
                
                self.doc_manager.save_index()
                self.refresh_document_tree()
                
                # 열린 탭이 있으면 닫기
                for i in range(self.tab_widget.count()):
                    tab = self.tab_widget.widget(i)
                    if (isinstance(tab, DocumentTab) and 
                        tab.document_node and 
                        tab.document_node.path == node.path):
                        self.tab_widget.removeTab(i)
                        break
                
            except Exception as e:
                QMessageBox.warning(self, "오류", f"삭제 실패: {e}")
    
    def auto_save(self):
        """자동 저장"""
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, DocumentTab) and current_tab.is_modified:
            if current_tab.document_node and current_tab.document_node.path:
                current_tab.save_content()
                self.status_bar.showMessage("자동 저장됨", 2000)
    
    def show_settings(self):
        """설정 표시"""
        if not self.config_manager:
            QMessageBox.warning(self, "오류", "설정 관리자를 사용할 수 없습니다.")
            return
        
        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.get_settings()
            
            # 설정 적용
            self.apply_theme(settings["theme"])
            
            # 자동 저장 설정
            if settings["auto_save"]:
                interval = settings["auto_save_interval"]
                self.auto_save_timer.start(interval * 60 * 1000)  # 분을 밀리초로
                self.auto_save_label.setText(f"자동 저장: {interval}분")
            else:
                self.auto_save_timer.stop()
                self.auto_save_label.setText("")
            
            QMessageBox.information(self, "설정", "설정이 적용되었습니다.")
    
    # 편집 기능들
    def undo(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, DocumentTab):
            current_tab.editor.undo()
    
    def redo(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, DocumentTab):
            current_tab.editor.redo()
    
    def cut(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, DocumentTab):
            current_tab.editor.cut()
    
    def copy(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, DocumentTab):
            current_tab.editor.copy()
    
    def paste(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, DocumentTab):
            current_tab.editor.paste()
    
    def find_text(self):
        # TODO: 찾기 대화상자 구현
        QMessageBox.information(self, "정보", "찾기 기능은 곧 구현됩니다.")
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        # 저장하지 않은 탭이 있는지 확인
        modified_tabs = []
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, DocumentTab) and tab.is_modified:
                modified_tabs.append((i, self.tab_widget.tabText(i)))
        
        if modified_tabs:
            reply = QMessageBox.question(
                self, "저장하지 않은 변경 사항",
                f"{len(modified_tabs)}개의 문서에 저장하지 않은 변경 사항이 있습니다.\n종료하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        event.accept()


from PySide6.QtWidgets import QLabel
