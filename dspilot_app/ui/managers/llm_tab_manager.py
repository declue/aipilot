import asyncio
from typing import Any, Dict

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from application.ui.common.style_manager import StyleManager
from dspilot_core.llm.agents.ask_agent import AskAgent


class LLMTabManager:
    """LLM 탭 관리 클래스"""

    def __init__(self, parent: Any) -> None:
        self.parent = parent

    def create_llm_tab(self) -> QWidget:
        """LLM 설정 탭 생성"""
        tab = QWidget()

        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #F3F4F6;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #D1D5DB;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #9CA3AF;
            }
        """
        )

        # 스크롤 내용 위젯
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 프로필 관리 그룹박스
        self.create_profile_group(layout)

        # LLM 설정 그룹박스
        self.create_connection_group(layout)

        # 모델 파라미터 그룹박스
        self.create_parameters_group(layout)

        layout.addStretch()

        scroll_area.setWidget(scroll_content)

        # 탭 레이아웃
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)

        return tab

    def create_profile_group(self, layout: QVBoxLayout) -> None:
        """프로필 관리 그룹 생성"""
        group_box = QGroupBox("프로필 관리")
        group_box.setStyleSheet(StyleManager.get_group_box_style())

        form_layout = QFormLayout(group_box)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(10)

        # 현재 프로필 선택
        profile_container = QWidget()
        profile_layout = QHBoxLayout(profile_container)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(8)

        self.parent.profile_combo = QComboBox()
        StyleManager.style_input(self.parent.profile_combo)
        self.parent.profile_combo.currentTextChanged.connect(self.on_profile_changed)

        # 프로필 관리 버튼들
        self.parent.add_profile_btn = QPushButton("➕")
        self.parent.add_profile_btn.setToolTip("새 프로필 추가")
        self.parent.add_profile_btn.clicked.connect(self.add_profile)
        self.parent.add_profile_btn.setMaximumWidth(35)

        self.parent.edit_profile_btn = QPushButton("✏️")
        self.parent.edit_profile_btn.setToolTip("현재 프로필 편집")
        self.parent.edit_profile_btn.clicked.connect(self.edit_profile)
        self.parent.edit_profile_btn.setMaximumWidth(35)

        self.parent.delete_profile_btn = QPushButton("🗑️")
        self.parent.delete_profile_btn.setToolTip("현재 프로필 삭제")
        self.parent.delete_profile_btn.clicked.connect(self.delete_profile)
        self.parent.delete_profile_btn.setMaximumWidth(35)

        for btn in [
            self.parent.add_profile_btn,
            self.parent.edit_profile_btn,
            self.parent.delete_profile_btn,
        ]:
            StyleManager.style_button(btn)

        profile_layout.addWidget(self.parent.profile_combo, 1)
        profile_layout.addWidget(self.parent.add_profile_btn)
        profile_layout.addWidget(self.parent.edit_profile_btn)
        profile_layout.addWidget(self.parent.delete_profile_btn)

        profile_label = QLabel("📋 프로필:")
        StyleManager.style_label(profile_label)
        form_layout.addRow(profile_label, profile_container)

        # 프로필 설명
        self.parent.profile_description = QTextEdit()
        self.parent.profile_description.setMaximumHeight(60)
        self.parent.profile_description.setReadOnly(True)
        StyleManager.style_input(self.parent.profile_description)

        desc_label = QLabel("📝 설명:")
        StyleManager.style_label(desc_label)
        form_layout.addRow(desc_label, self.parent.profile_description)

        layout.addWidget(group_box)

    def create_connection_group(self, layout: QVBoxLayout) -> None:
        """연결 설정 그룹 생성"""
        group_box = QGroupBox("API 연결 설정")
        group_box.setStyleSheet(StyleManager.get_group_box_style())

        form_layout = QFormLayout(group_box)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(10)

        # API Key 입력
        self.parent.api_key_input = QLineEdit()
        self.parent.api_key_input.setPlaceholderText(
            "API 키를 입력하세요 (Ollama는 아무값이나 입력)"
        )
        self.parent.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        StyleManager.style_input(self.parent.api_key_input)

        api_key_label = QLabel("🔑 API Key:")
        StyleManager.style_label(api_key_label)
        form_layout.addRow(api_key_label, self.parent.api_key_input)

        # 서버 URL 입력
        self.parent.base_url_input = QLineEdit()
        self.parent.base_url_input.setPlaceholderText("예: http://localhost:11434/v1 (Ollama)")
        StyleManager.style_input(self.parent.base_url_input)

        base_url_label = QLabel("🌐 서버 URL:")
        StyleManager.style_label(base_url_label)
        form_layout.addRow(base_url_label, self.parent.base_url_input)

        # 모델명 입력 (콤보박스로 변경)
        model_container = QWidget()
        model_layout = QHBoxLayout(model_container)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(8)

        self.parent.model_input = QComboBox()
        self.parent.model_input.setEditable(True)  # 직접 입력 가능
        self.parent.model_input.setPlaceholderText("예: llama3.2, gpt-3.5-turbo, codellama")
        StyleManager.style_input(self.parent.model_input)

        # 모델 새로고침 버튼
        self.parent.refresh_models_btn = QPushButton("🔄 새로고침")
        self.parent.refresh_models_btn.setToolTip("사용 가능한 모델 목록 새로고침")
        self.parent.refresh_models_btn.clicked.connect(self.refresh_models)
        StyleManager.style_button(self.parent.refresh_models_btn)

        model_layout.addWidget(self.parent.model_input, 1)  # 1: 확장 가능
        model_layout.addWidget(self.parent.refresh_models_btn, 0)  # 0: 고정 크기

        model_label = QLabel("🤖 모델명:")
        StyleManager.style_label(model_label)
        form_layout.addRow(model_label, model_container)

        layout.addWidget(group_box)

    def create_parameters_group(self, layout: QVBoxLayout) -> None:
        """모델 파라미터 그룹 생성"""
        group_box = QGroupBox("모델 파라미터")
        group_box.setStyleSheet(StyleManager.get_group_box_style())

        form_layout = QFormLayout(group_box)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(10)

        # Temperature 설정
        self.parent.temperature_spin = QDoubleSpinBox()
        self.parent.temperature_spin.setRange(0.0, 2.0)
        self.parent.temperature_spin.setSingleStep(0.1)
        self.parent.temperature_spin.setDecimals(1)
        self.parent.temperature_spin.setValue(0.7)
        self.parent.temperature_spin.setToolTip("낮을수록 일관성 높음, 높을수록 창의적")
        StyleManager.style_input(self.parent.temperature_spin)

        temp_label = QLabel("🌡️ Temperature:")
        StyleManager.style_label(temp_label)
        form_layout.addRow(temp_label, self.parent.temperature_spin)

        # Max Tokens 설정
        self.parent.max_tokens_spin = QSpinBox()
        self.parent.max_tokens_spin.setRange(1, 500000)
        self.parent.max_tokens_spin.setValue(100000)
        self.parent.max_tokens_spin.setToolTip("응답의 최대 토큰 수")
        StyleManager.style_input(self.parent.max_tokens_spin)

        tokens_label = QLabel("📏 Max Tokens:")
        StyleManager.style_label(tokens_label)
        form_layout.addRow(tokens_label, self.parent.max_tokens_spin)

        # Top K 설정
        self.parent.top_k_spin = QSpinBox()
        self.parent.top_k_spin.setRange(1, 100)
        self.parent.top_k_spin.setValue(50)
        self.parent.top_k_spin.setToolTip("다음 토큰 선택 시 고려할 후보 수")
        StyleManager.style_input(self.parent.top_k_spin)

        topk_label = QLabel("🔝 Top K:")
        StyleManager.style_label(topk_label)
        form_layout.addRow(topk_label, self.parent.top_k_spin)

        # Instruction 파일 설정
        instruction_container = QWidget()
        instruction_layout = QHBoxLayout(instruction_container)
        instruction_layout.setContentsMargins(0, 0, 0, 0)
        instruction_layout.setSpacing(8)

        self.parent.instruction_file_input = QLineEdit()
        self.parent.instruction_file_input.setPlaceholderText(
            "예: instructions/default_agent_instructions.txt"
        )
        self.parent.instruction_file_input.setToolTip("Agent가 사용할 instruction 파일 경로")
        StyleManager.style_input(self.parent.instruction_file_input)

        # 파일 선택 버튼
        self.parent.browse_instruction_btn = QPushButton("📁 찾기")
        self.parent.browse_instruction_btn.setToolTip("instruction 파일 선택")
        self.parent.browse_instruction_btn.clicked.connect(self.browse_instruction_file)
        StyleManager.style_button(self.parent.browse_instruction_btn)

        # 파일 편집 버튼
        self.parent.edit_instruction_btn = QPushButton("✏️ 편집")
        self.parent.edit_instruction_btn.setToolTip("instruction 파일 편집")
        self.parent.edit_instruction_btn.clicked.connect(self.edit_instruction_file)
        StyleManager.style_button(self.parent.edit_instruction_btn)

        instruction_layout.addWidget(self.parent.instruction_file_input, 1)
        instruction_layout.addWidget(self.parent.browse_instruction_btn, 0)
        instruction_layout.addWidget(self.parent.edit_instruction_btn, 0)

        instruction_label = QLabel("📝 Instruction 파일:")
        StyleManager.style_label(instruction_label)
        form_layout.addRow(instruction_label, instruction_container)

        layout.addWidget(group_box)

    def load_profiles(self) -> None:
        """프로필 목록 로드"""
        profiles = self.parent.config_manager.get_llm_profiles()
        current_profile = self.parent.config_manager.get_current_profile_name()

        self.parent.profile_combo.clear()
        for profile_id, profile_data in profiles.items():
            display_name = f"{profile_data['name']} ({profile_id})"
            self.parent.profile_combo.addItem(display_name, profile_id)

        # 현재 프로필 선택
        for i in range(self.parent.profile_combo.count()):
            if self.parent.profile_combo.itemData(i) == current_profile:
                self.parent.profile_combo.setCurrentIndex(i)
                break

    def on_profile_changed(self) -> None:
        """프로필 변경 시 호출"""
        current_index = self.parent.profile_combo.currentIndex()
        if current_index >= 0:
            profile_id = self.parent.profile_combo.itemData(current_index)
            if profile_id:
                try:
                    self.parent.config_manager.set_current_profile(profile_id)
                    self.load_current_profile_settings()
                except Exception as e:
                    QMessageBox.warning(
                        self.parent,
                        "프로필 변경 실패",
                        f"프로필 변경에 실패했습니다: {str(e)}",
                    )

    def load_current_profile_settings(self) -> None:
        """현재 프로필의 설정을 UI에 로드"""
        try:
            profiles = self.parent.config_manager.get_llm_profiles()
            current_profile_id = self.parent.config_manager.get_current_profile_name()
            current_profile = profiles.get(current_profile_id, {})

            if current_profile:
                self.parent.api_key_input.setText(current_profile.get("api_key", ""))
                self.parent.base_url_input.setText(current_profile.get("base_url", ""))
                self.parent.model_input.setCurrentText(current_profile.get("model", ""))
                self.parent.temperature_spin.setValue(current_profile.get("temperature", 0.7))
                self.parent.max_tokens_spin.setValue(current_profile.get("max_tokens", 100000))
                self.parent.top_k_spin.setValue(current_profile.get("top_k", 50))
                self.parent.instruction_file_input.setText(
                    current_profile.get(
                        "instruction_file",
                        "instructions/default_agent_instructions.txt",
                    )
                )
                self.parent.profile_description.setText(current_profile.get("description", ""))

        except Exception as e:
            QMessageBox.warning(
                self.parent,
                "설정 로드 실패",
                f"프로필 설정 로드에 실패했습니다: {str(e)}",
            )

    def add_profile(self) -> None:
        """새 프로필 추가"""
        profile_id, ok = QInputDialog.getText(
            self.parent, "새 프로필 추가", "프로필 ID를 입력하세요:"
        )
        if not ok or not profile_id.strip():
            return

        profile_id = profile_id.strip()

        try:
            profiles = self.parent.config_manager.get_llm_profiles()
            if profile_id in profiles:
                QMessageBox.warning(self.parent, "중복 프로필", "이미 존재하는 프로필 ID입니다.")
                return

            name, ok = QInputDialog.getText(self.parent, "프로필 이름", "프로필 이름을 입력하세요:")
            if not ok or not name.strip():
                return

            description, ok = QInputDialog.getText(
                self.parent, "프로필 설명", "프로필 설명을 입력하세요 (선택사항):"
            )
            if not ok:
                description = ""

            # 현재 UI의 설정값으로 새 프로필 생성
            new_profile = {
                "name": name.strip(),
                "api_key": self.parent.api_key_input.text(),
                "base_url": self.parent.base_url_input.text(),
                "model": self.parent.model_input.currentText(),
                "temperature": self.parent.temperature_spin.value(),
                "max_tokens": self.parent.max_tokens_spin.value(),
                "top_k": self.parent.top_k_spin.value(),
                "instruction_file": self.parent.instruction_file_input.text()
                or "instructions/default_agent_instructions.txt",
                "description": description.strip(),
            }

            self.parent.config_manager.create_llm_profile(profile_id, new_profile)
            self.load_profiles()

            # 새로 생성한 프로필로 변경
            for i in range(self.parent.profile_combo.count()):
                if self.parent.profile_combo.itemData(i) == profile_id:
                    self.parent.profile_combo.setCurrentIndex(i)
                    break

            QMessageBox.information(self.parent, "성공", f"프로필 '{name}'이 추가되었습니다.")

        except Exception as e:
            QMessageBox.critical(
                self.parent, "프로필 추가 실패", f"프로필 추가에 실패했습니다: {str(e)}"
            )

    def edit_profile(self) -> None:
        """현재 프로필 편집"""
        current_index = self.parent.profile_combo.currentIndex()
        if current_index < 0:
            return

        profile_id = self.parent.profile_combo.itemData(current_index)
        if not profile_id:
            return

        try:
            profiles = self.parent.config_manager.get_llm_profiles()
            current_profile = profiles.get(profile_id, {})

            # 현재 UI의 설정값으로 프로필 업데이트
            updated_profile = {
                "name": current_profile.get("name", ""),
                "api_key": self.parent.api_key_input.text(),
                "base_url": self.parent.base_url_input.text(),
                "model": self.parent.model_input.currentText(),
                "temperature": self.parent.temperature_spin.value(),
                "max_tokens": self.parent.max_tokens_spin.value(),
                "top_k": self.parent.top_k_spin.value(),
                "instruction_file": self.parent.instruction_file_input.text()
                or "instructions/default_agent_instructions.txt",
                "description": self.parent.profile_description.toPlainText(),
            }

            self.parent.config_manager.update_llm_profile(profile_id, updated_profile)
            QMessageBox.information(
                self.parent,
                "성공",
                f"프로필 '{current_profile.get('name', profile_id)}'이 업데이트되었습니다.",
            )

        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "프로필 업데이트 실패",
                f"프로필 업데이트에 실패했습니다: {str(e)}",
            )

    def delete_profile(self) -> None:
        """현재 프로필 삭제"""
        current_index = self.parent.profile_combo.currentIndex()
        if current_index < 0:
            return

        profile_id = self.parent.profile_combo.itemData(current_index)
        if not profile_id:
            return

        if profile_id == "default":
            QMessageBox.warning(self.parent, "삭제 불가", "기본 프로필은 삭제할 수 없습니다.")
            return

        try:
            profiles = self.parent.config_manager.get_llm_profiles()
            profile_name = profiles.get(profile_id, {}).get("name", profile_id)

            reply = QMessageBox.question(
                self.parent,
                "프로필 삭제",
                f"프로필 '{profile_name}'을 삭제하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.parent.config_manager.delete_llm_profile(profile_id)
                self.load_profiles()  # 프로필 목록 새로고침
                QMessageBox.information(
                    self.parent, "성공", f"프로필 '{profile_name}'이 삭제되었습니다."
                )

        except Exception as e:
            QMessageBox.critical(
                self.parent, "프로필 삭제 실패", f"프로필 삭제에 실패했습니다: {str(e)}"
            )

    def test_connection(self) -> None:
        """연결 테스트"""
        api_key = self.parent.api_key_input.text().strip()
        base_url = self.parent.base_url_input.text().strip()
        # 콤보박스의 현재 텍스트 가져오기 (선택된 항목 또는 직접 입력된 텍스트)
        model = self.parent.model_input.currentText().strip()

        if not api_key or not base_url or not model:
            QMessageBox.warning(self.parent, "입력 오류", "모든 필드를 입력해주세요.")
            return

        self.test_llm_connection(api_key, base_url, model)

    def test_llm_connection(self, api_key: str, base_url: str, model: str) -> None:
        """LLM 연결 테스트"""
        try:
            result = asyncio.run(AskAgent.test_connection(api_key, base_url, model))
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "연결 테스트 오류 ❌",
                f"연결 테스트 중 오류가 발생했습니다.\n\n오류: {str(e)}",
            )
            return

        if result["success"]:
            QMessageBox.information(
                self.parent,
                "연결 성공 ✅",
                f"LLM 서버에 성공적으로 연결되었습니다!\n\n"
                f"모델: {result['model']}\n"
                f"응답: {result['response']}",
            )
        else:
            QMessageBox.critical(
                self.parent,
                "연결 실패 ❌",
                f"LLM 서버 연결에 실패했습니다.\n\n"
                f"오류: {result['message']}\n\n"
                f"• 서버 URL이 올바른지 확인하세요\n"
                f"• 모델명이 정확한지 확인하세요\n"
                f"• 서버가 실행 중인지 확인하세요",
            )

    def refresh_models(self) -> None:
        """사용 가능한 모델 목록 새로고침"""
        api_key = self.parent.api_key_input.text().strip()
        base_url = self.parent.base_url_input.text().strip()

        if not api_key or not base_url:
            QMessageBox.warning(
                self.parent,
                "입력 오류",
                "모델 목록을 가져오려면 API Key와 서버 URL을 먼저 입력해주세요.",
            )
            return

        # 현재 선택된 모델 저장
        current_model = self.parent.model_input.currentText().strip()

        # 모델 목록 가져오기
        try:
            result = asyncio.run(AskAgent.get_available_models(api_key, base_url))
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "모델 목록 가져오기 오류 ❌",
                f"모델 목록을 가져오는 중 오류가 발생했습니다.\n\n오류: {str(e)}",
            )
            return

        if result["success"]:
            # 콤보박스 클리어하고 새 모델들 추가
            self.parent.model_input.clear()

            models = result["models"]
            if models:
                self.parent.model_input.addItems(models)

                # 이전에 선택된 모델이 목록에 있으면 다시 선택
                if current_model:
                    index = self.parent.model_input.findText(current_model)
                    if index >= 0:
                        self.parent.model_input.setCurrentIndex(index)
                    else:
                        # 목록에 없으면 직접 입력된 텍스트로 설정
                        self.parent.model_input.setCurrentText(current_model)

                QMessageBox.information(
                    self.parent,
                    "모델 목록 새로고침 성공 ✅",
                    f"{result['message']}\n\n"
                    f"사용 가능한 모델:\n"
                    + "\n".join(f"• {model}" for model in models[:10])
                    + (f"\n• ... 외 {len(models)-10}개" if len(models) > 10 else ""),
                )
            else:
                QMessageBox.warning(
                    self.parent,
                    "모델 없음 ⚠️",
                    "서버에서 사용 가능한 모델을 찾을 수 없습니다.\n" "서버 설정을 확인해주세요.",
                )
        else:
            QMessageBox.critical(
                self.parent,
                "모델 목록 가져오기 실패 ❌",
                f"모델 목록을 가져오는데 실패했습니다.\n\n"
                f"오류: {result['message']}\n\n"
                f"• API Key와 서버 URL이 올바른지 확인하세요\n"
                f"• 서버가 실행 중이고 /v1/models 엔드포인트를 지원하는지 확인하세요",
            )

    def browse_instruction_file(self) -> None:
        """instruction 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "instruction 파일 선택",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            self.parent.instruction_file_input.setText(file_path)

    def edit_instruction_file(self) -> None:
        """instruction 파일 편집"""
        file_path = self.parent.instruction_file_input.text().strip()
        if not file_path:
            QMessageBox.warning(
                self.parent,
                "파일 경로 없음",
                "먼저 instruction 파일 경로를 입력하세요.",
            )
            return

        try:
            import os

            # 파일이 없으면 기본 내용으로 생성
            if not os.path.exists(file_path):
                # 디렉토리가 없으면 생성
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # 기본 instruction 내용 생성
                default_content = self.parent.config_manager._get_default_instruction_content()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(default_content)

            # 파일 내용 읽기
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 편집 대화상자 생성

            dialog = QDialog(self.parent)
            dialog.setWindowTitle(f"Instruction 파일 편집 - {os.path.basename(file_path)}")
            dialog.setMinimumSize(800, 600)

            layout = QVBoxLayout(dialog)

            # 텍스트 편집기
            text_edit = QTextEdit()
            text_edit.setPlainText(content)
            text_edit.setStyleSheet(
                """
                QTextEdit {
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 12px;
                    line-height: 1.5;
                    border: 1px solid #d1d5db;
                    border-radius: 6px;
                    padding: 10px;
                }
            """
            )
            layout.addWidget(text_edit)

            # 버튼 레이아웃
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            # 취소 버튼
            cancel_btn = QPushButton("취소")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)

            # 저장 버튼
            save_btn = QPushButton("저장")
            save_btn.setDefault(True)
            save_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(save_btn)

            layout.addLayout(button_layout)

            # 대화상자 실행
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_content = text_edit.toPlainText()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                QMessageBox.information(
                    self.parent,
                    "성공",
                    f"instruction 파일이 성공적으로 저장되었습니다.\n\n파일: {file_path}",
                )

        except Exception as e:
            QMessageBox.critical(
                self.parent, "파일 편집 실패", f"파일 편집에 실패했습니다: {str(e)}"
            )

    def update_theme(self) -> None:
        """테마 업데이트"""
        try:
            if hasattr(self.parent, "theme_manager"):
                # 스타일 매니저에 테마 매니저 설정
                StyleManager.set_theme_manager(self.parent.theme_manager)

                colors = self.parent.theme_manager.get_theme_colors()

                # 스크롤 영역 테마 업데이트
                self._update_scroll_area_theme(colors)

        except Exception as e:
            print(f"LLM 탭 테마 업데이트 실패: {e}")

    def _update_scroll_area_theme(self, colors: Dict[str, Any]) -> None:
        """스크롤 영역 테마 업데이트"""
        # 스크롤 영역 스타일 업데이트 (실제 구현에서는 위젯 참조 필요)
