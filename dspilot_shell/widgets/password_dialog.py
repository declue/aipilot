"""
비밀번호 입력 대화상자
"""
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class PasswordDialog(QDialog):
    """비밀번호 입력 대화상자"""
    
    def __init__(self, connection_name: str, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle('비밀번호 입력')
        self.setModal(True)
        self.setFixedSize(350, 150)
        
        # 레이아웃
        layout = QVBoxLayout(self)
        
        # 설명 라벨
        info_label = QLabel(f"'{connection_name}' 연결을 위한 비밀번호를 입력하세요:")
        layout.addWidget(info_label)
        
        # 폼 레이아웃
        form_layout = QFormLayout()
        
        # 비밀번호 입력
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText('SSH 비밀번호')
        form_layout.addRow('비밀번호:', self.password_edit)
        
        layout.addLayout(form_layout)
        
        # 버튼 박스
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        # 포커스 설정
        self.password_edit.setFocus()
    
    def get_password(self) -> str:
        """입력된 비밀번호 반환"""
        return self.password_edit.text()
