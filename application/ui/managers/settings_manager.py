"""설정 관리 모듈"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QMessageBox


class SettingsManager:
    """설정 관리 클래스"""

    def __init__(self, parent):
        self.parent = parent

    def load_current_settings(self):
        """현재 설정값 로드"""
        # LLM 프로필 목록 로드
        self.parent.llm_tab_manager.load_profiles()

        # 현재 프로필의 설정 로드
        self.parent.llm_tab_manager.load_current_profile_settings()

        # UI 설정 로드
        ui_config = self.parent.config_manager.get_ui_config()

        # 폰트 설정
        font = QFont(ui_config["font_family"])
        self.parent.font_family_combo.setCurrentFont(font)
        self.parent.font_size_slider.setValue(ui_config["font_size"])
        self.parent.font_size_label.setText(f"{ui_config['font_size']}px")

        # 채팅 버블 너비 설정
        self.parent.bubble_width_slider.setValue(ui_config["chat_bubble_max_width"])
        self.parent.bubble_width_label.setText(
            f"{ui_config['chat_bubble_max_width']}px"
        )

        # 미리보기 업데이트
        self.parent.ui_tab_manager.update_preview()

        # GitHub 설정 로드
        self.parent.github_tab_manager.load_repositories()
        self.parent.github_tab_manager.load_notification_settings()

    def reset_to_defaults(self):
        """기본값으로 복원"""
        current_tab = self.parent.tab_widget.currentIndex()

        if current_tab == 0:  # LLM 탭
            # 기본 프로필로 변경
            for i in range(self.parent.profile_combo.count()):
                if self.parent.profile_combo.itemData(i) == "default":
                    self.parent.profile_combo.setCurrentIndex(i)
                    break

            # 기본값들 설정
            self.parent.api_key_input.setText("your-api-key-here")
            self.parent.base_url_input.setText("http://localhost:11434/v1")
            self.parent.model_input.setCurrentText("llama3.2")
            self.parent.temperature_spin.setValue(0.7)
            self.parent.max_tokens_spin.setValue(100000)
            self.parent.top_k_spin.setValue(50)
            self.parent.instruction_file_input.setText(
                "instructions/default_agent_instructions.txt"
            )
        elif current_tab == 1:  # UI 탭
            font = QFont(
                "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
            )
            self.parent.font_family_combo.setCurrentFont(font)
            self.parent.font_size_slider.setValue(14)
            self.parent.bubble_width_slider.setValue(600)
            self.parent.ui_tab_manager.update_preview()
        elif current_tab == 3:  # GitHub 탭
            self.parent.github_tab_manager.repo_list.clear()

    def save_settings(self):
        """설정 저장"""
        try:
            # 현재 프로필 업데이트
            current_index = self.parent.profile_combo.currentIndex()
            if current_index >= 0:
                profile_id = self.parent.profile_combo.itemData(current_index)
                if profile_id:
                    # 프로필 업데이트
                    self.parent.llm_tab_manager.edit_profile()

            # UI 설정 저장
            font_family = self.parent.font_family_combo.currentFont().family()
            font_size = self.parent.font_size_slider.value()
            chat_bubble_max_width = self.parent.bubble_width_slider.value()
            window_theme = "light"  # 현재는 라이트 테마만 지원

            self.parent.config_manager.set_ui_config(
                font_family, font_size, chat_bubble_max_width, window_theme
            )

            # GitHub 알림 설정 저장
            self.parent.github_tab_manager.save_notification_settings()

            # 성공 메시지
            QMessageBox.information(
                self.parent,
                "저장 완료",
                "모든 설정이 성공적으로 저장되었습니다.\n변경사항은 다음 메시지부터 적용됩니다.",
            )

            # 설정 변경 시그널 발생
            self.parent.settings_changed.emit()

        except Exception as e:
            QMessageBox.critical(
                self.parent, "저장 실패", f"설정 저장 중 오류가 발생했습니다:\n{str(e)}"
            )
