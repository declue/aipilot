from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
)


class UISetupManager:
    """UI 구성 요소 설정 담당 클래스"""

    def __init__(self, main_window):
        self.main_window = main_window
        self.ui_config = main_window.ui_config

    def setup_header(self, layout):
        """헤더 설정 - 모델 선택 기능 추가"""
        header_frame = QFrame()
        header_frame.setStyleSheet(
            """
            QFrame {
                background-color: #FFFFFF;
                border: none;
                border-bottom: 1px solid #E5E7EB;
                padding: 0;
            }
        """
        )

        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 16, 24, 16)
        header_layout.setSpacing(16)

        # 타이틀
        title_label = QLabel("💬 DS Pilot")
        title_label.setStyleSheet(
            f"""
            QLabel {{
                color: #1F2937;
                font-size: 20px;
                font-weight: 700;
                font-family: '{self.ui_config['font_family']}';
            }}
        """
        )
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 모델 선택 컨테이너 (새 대화 버튼 좌측에 배치)
        model_container = QFrame()
        model_container.setFixedHeight(40)  # 버튼과 같은 높이
        model_container.setStyleSheet(
            """
            QFrame {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 20px;
                padding: 0;
            }
        """
        )
        model_layout = QHBoxLayout(model_container)
        model_layout.setContentsMargins(12, 0, 12, 0)  # 상하 패딩 제거, 좌우만 유지
        model_layout.setSpacing(8)

        # 모델 아이콘
        model_icon = QLabel("🤖")
        model_icon.setStyleSheet(
            """
            QLabel {
                color: #6B7280;
                font-size: 16px;
                font-weight: 500;
                background-color: transparent;
                border: none;
            }
        """
        )
        model_layout.addWidget(model_icon)

        # 모델 선택 드롭다운
        self.main_window.model_selector = QComboBox()
        self.main_window.model_selector.setMinimumWidth(180)
        self.main_window.model_selector.setFixedHeight(32)  # 컨테이너 내부에 맞는 높이
        self.main_window.model_selector.setStyleSheet(
            f"""
            QComboBox {{
                background-color: transparent;
                border: none;
                color: #374151;
                font-size: 14px;
                font-weight: 500;
                font-family: '{self.ui_config['font_family']}';
                padding: 0 8px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #FFFFFF;
                border: 2px solid #E5E7EB;
                border-radius: 8px;
                padding: 4px;
                selection-background-color: #EBF4FF;
                selection-color: #1E40AF;
                font-size: 14px;
                font-family: '{self.ui_config['font_family']}';
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: 4px;
                margin: 2px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #EBF4FF;
                color: #1E40AF;
            }}
        """
        )

        # 모델 선택 변경 시 이벤트 연결
        self.main_window.model_selector.currentTextChanged.connect(
            self.on_model_selection_changed
        )

        model_layout.addWidget(self.main_window.model_selector)
        header_layout.addWidget(model_container)

        # 새 대화 버튼
        new_chat_button = QPushButton("🆕 새 대화")
        new_chat_button.setFixedSize(100, 40)
        new_chat_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #10B981;
                color: white;
                border: 2px solid #10B981;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                font-family: '{self.ui_config['font_family']}';
            }}
            QPushButton:hover {{
                background-color: #059669;
                border-color: #059669;
            }}
            QPushButton:pressed {{
                background-color: #047857;
                border-color: #047857;
            }}
        """
        )
        new_chat_button.clicked.connect(self.main_window.start_new_conversation)
        header_layout.addWidget(new_chat_button)

        # 설정 버튼
        settings_button = QPushButton("⚙️ 설정")
        settings_button.setFixedSize(100, 40)
        settings_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #6B7280;
                color: white;
                border: 2px solid #6B7280;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                font-family: '{self.ui_config['font_family']}';
            }}
            QPushButton:hover {{
                background-color: #4B5563;
                border-color: #4B5563;
            }}
            QPushButton:pressed {{
                background-color: #374151;
                border-color: #374151;
            }}
        """
        )
        settings_button.clicked.connect(self.main_window.open_settings)
        header_layout.addWidget(settings_button)

        layout.addWidget(header_frame)

        # 모델 목록 로드
        self.load_model_profiles()

    def load_model_profiles(self):
        """프로필 목록을 모델 선택 드롭다운에 로드"""
        try:
            profiles = self.main_window.config_manager.get_llm_profiles()
            current_profile = self.main_window.config_manager.get_current_profile_name()

            self.main_window.model_selector.clear()

            for profile_id, profile_data in profiles.items():
                display_name = f"{profile_data['name']} ({profile_data['model']})"
                self.main_window.model_selector.addItem(display_name, profile_id)

            # 현재 프로필 선택
            for i in range(self.main_window.model_selector.count()):
                if self.main_window.model_selector.itemData(i) == current_profile:
                    self.main_window.model_selector.setCurrentIndex(i)
                    break

        except Exception as e:
            print(f"모델 프로필 로드 실패: {e}")

    def on_model_selection_changed(self):
        """모델 선택 변경 시 호출"""
        current_index = self.main_window.model_selector.currentIndex()
        if current_index >= 0:
            profile_id = self.main_window.model_selector.itemData(current_index)
            if profile_id:
                try:
                    # 현재 프로필 변경
                    self.main_window.config_manager.set_current_profile(profile_id)

                    # LLM Agent의 클라이언트 초기화 (새로운 설정으로 다시 생성)
                    if hasattr(self.main_window, "llm_agent"):
                        self.main_window.llm_agent._client = None  # 클라이언트 초기화

                    # 상태 메시지 추가
                    profiles = self.main_window.config_manager.get_llm_profiles()
                    selected_profile = profiles.get(profile_id, {})
                    model_name = selected_profile.get("model", "Unknown")
                    profile_name = selected_profile.get("name", "Unknown")

                    status_message = (
                        f"🔄 **모델 변경됨**: {profile_name} ({model_name})"
                    )
                    self.main_window.add_system_message(status_message)

                except Exception as e:
                    print(f"모델 변경 실패: {e}")

    def setup_chat_area(self, layout):
        """채팅 영역 설정 (스크롤 지원)"""
        # 채팅 영역 컨테이너
        chat_frame = QFrame()
        # 최대 너비 제한 없이 설정
        chat_frame.setStyleSheet(
            """
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                margin: 0px;
            }
        """
        )

        # 스크롤 영역 생성
        self.main_window.scroll_area = QScrollArea()
        self.main_window.scroll_area.setWidget(chat_frame)
        self.main_window.scroll_area.setWidgetResizable(True)
        self.main_window.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.main_window.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.main_window.scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
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

        # 채팅 컨테이너 및 레이아웃
        self.main_window.chat_container = chat_frame
        self.main_window.chat_layout = QVBoxLayout(self.main_window.chat_container)
        self.main_window.chat_layout.setContentsMargins(
            8, 20, 8, 20
        )  # 좌우 여백을 8px로 최소화
        self.main_window.chat_layout.setSpacing(16)
        self.main_window.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 빈 공간을 차지할 스페이서 추가
        self.main_window.chat_layout.addStretch()

        # 레이아웃에 스크롤 영역 추가
        layout.addWidget(self.main_window.scroll_area, 1)  # stretch factor를 1로 설정

    def setup_input_area(self, layout):
        """Material UI 스타일 입력 영역 (중단 버튼 추가)"""
        input_frame = QFrame()
        input_frame.setStyleSheet(
            """
            QFrame {
                background-color: #FFFFFF;
                border: none;
                border-top: 1px solid #E5E7EB;
                padding: 0;
            }
        """
        )

        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 20, 8, 28)  # 좌우 패딩을 8px로 최소화
        input_layout.setSpacing(16)

        # 입력 컨테이너
        input_container = QFrame()
        input_container.setStyleSheet(
            """
            QFrame {
                background-color: #F8FAFC;
                border: 2px solid #E2E8F0;
                border-radius: 28px;
                padding: 0;
            }
            QFrame:focus-within {
                border-color: #2563EB;
                background-color: #FFFFFF;
            }
        """
        )

        container_layout = QHBoxLayout(input_container)
        container_layout.setContentsMargins(24, 12, 12, 12)  # 더 큰 패딩
        container_layout.setSpacing(16)

        # 입력 텍스트
        self.main_window.input_text = QTextEdit()
        self.main_window.input_text.setMaximumHeight(150)  # 더 큰 최대 높이
        self.main_window.input_text.setMinimumHeight(48)  # 더 큰 최소 높이
        self.main_window.input_text.setPlaceholderText(
            "메시지를 입력하세요... (Shift+Enter로 줄바꿈)"
        )
        self.main_window.input_text.setAcceptRichText(False)  # HTML 형식 붙여넣기 방지
        self.main_window.input_text.setStyleSheet(
            f"""
            QTextEdit {{
                border: none;
                background-color: transparent;
                font-size: {self.ui_config['font_size']}px;
                font-family: '{self.ui_config['font_family']}';
                color: #1F2937;
                padding: 8px 0;
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                outline: none;
            }}
        """
        )

        # 엔터키 이벤트 처리
        self.main_window.input_text.keyPressEvent = (
            self.main_window.input_key_press_event
        )

        # 중단 버튼 (처음에는 숨김)
        self.main_window.stop_button = QPushButton("중단")
        self.main_window.stop_button.setFixedSize(88, 48)
        self.main_window.stop_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #EF4444;
                color: white;
                border: none;
                border-radius: 24px;
                font-weight: 700;
                font-size: {self.ui_config['font_size']}px;
                font-family: '{self.ui_config['font_family']}';
            }}
            QPushButton:hover {{
                background-color: #DC2626;
            }}
            QPushButton:pressed {{
                background-color: #B91C1C;
            }}
        """
        )
        self.main_window.stop_button.clicked.connect(self.main_window.stop_ai_response)
        self.main_window.stop_button.hide()  # 처음에는 숨김

        # 전송 버튼
        self.main_window.send_button = QPushButton("전송")
        self.main_window.send_button.setFixedSize(88, 48)  # 일관된 버튼 크기
        self.main_window.send_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: 24px;
                font-weight: 700;
                font-size: {self.ui_config['font_size']}px;
                font-family: '{self.ui_config['font_family']}';
            }}
            QPushButton:hover {{
                background-color: #1D4ED8;
            }}
            QPushButton:pressed {{
                background-color: #1E40AF;
            }}
            QPushButton:disabled {{
                background-color: #9CA3AF;
                color: #6B7280;
            }}
        """
        )
        self.main_window.send_button.clicked.connect(self.main_window.send_message)

        container_layout.addWidget(self.main_window.input_text, 1)
        container_layout.addWidget(self.main_window.stop_button)
        container_layout.addWidget(self.main_window.send_button)

        # 도움말 텍스트
        help_text = QLabel(
            "💡 Markdown 문법을 지원합니다 (예: **굵게**, *기울임*, `코드`, ```코드블록```)"
        )
        help_text.setStyleSheet(
            f"""
            QLabel {{
                color: #6B7280;
                font-size: {max(self.ui_config['font_size'] - 2, 10)}px;
                font-family: '{self.ui_config['font_family']}';
            }}
        """
        )

        input_layout.addWidget(input_container)
        input_layout.addWidget(help_text)

        layout.addWidget(input_frame)
