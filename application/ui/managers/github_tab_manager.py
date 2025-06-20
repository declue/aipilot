"""GitHub 설정 탭 관리자"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from application.config.config_manager import ConfigManager

if TYPE_CHECKING:
    from application.ui.main_window import MainWindow


class GitHubTabManager:
    """GitHub 설정 탭 관리자"""

    repo_list: QListWidget
    config_manager: ConfigManager
    parent: MainWindow

    def __init__(self, parent: MainWindow):
        self.parent = parent
        self.config_manager: ConfigManager = parent.config_manager
        # UI 위젯 속성들
        self.github_notifications_enabled: QCheckBox
        self.summary_enabled: QCheckBox
        self.summary_threshold: QSpinBox
        self.rate_limit_enabled: QCheckBox
        self.rate_limit_count: QSpinBox
        self.rate_limit_interval: QSpinBox
        self.event_widgets: Dict[str, QWidget]
        self.event_configs: Dict[str, Dict[str, Any]]

    def create_github_tab(self):
        """GitHub 설정 탭 생성"""
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
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(16, 16, 16, 16)
        scroll_layout.setSpacing(16)

        # Repository/Organization 그룹
        self.setup_repository_group(scroll_layout)

        # 알림 설정 그룹
        self.setup_notification_group(scroll_layout)

        # 여백 추가
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)

        # 탭 레이아웃
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)

        return tab

    def setup_repository_group(self, layout):
        """Repository/Organization 설정 그룹"""
        group = QGroupBox("📁 Repository/Organization 설정")
        group.setStyleSheet(
            """
            QGroupBox {
                font-weight: 600;
                font-size: 12px;
                color: #374151;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: #1F2937;
                background-color: #FFFFFF;
            }
        """
        )
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(16, 16, 16, 16)
        group_layout.setSpacing(12)

        # 설명 라벨
        desc_label = QLabel(
            "메시지를 수신할 GitHub Repository 또는 Organization을 설정하세요."
        )
        desc_label.setStyleSheet(
            """
            QLabel {
                color: #6B7280;
                font-size: 11px;
                font-weight: 400;
                margin-bottom: 8px;
            }
        """
        )
        group_layout.addWidget(desc_label)

        # Repository/Organization 리스트
        self.repo_list = QListWidget()
        self.repo_list.setStyleSheet(
            """
            QListWidget {
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                background-color: #FFFFFF;
                font-size: 11px;
                min-height: 150px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #F3F4F6;
                color: #374151;
            }
            QListWidget::item:selected {
                background-color: #EBF4FF;
                color: #1D4ED8;
            }
            QListWidget::item:hover {
                background-color: #F9FAFB;
            }
        """
        )
        group_layout.addWidget(self.repo_list)

        # 버튼 영역
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # 추가 버튼
        add_button = QPushButton("➕ 추가")
        add_button.setStyleSheet(self.get_button_style("#10B981"))
        add_button.clicked.connect(self.add_repository)

        # 제거 버튼
        remove_button = QPushButton("➖ 제거")
        remove_button.setStyleSheet(self.get_button_style("#EF4444"))
        remove_button.clicked.connect(self.remove_repository)

        # 편집 버튼
        edit_button = QPushButton("✏️ 편집")
        edit_button.setStyleSheet(self.get_button_style("#F59E0B"))
        edit_button.clicked.connect(self.edit_repository)

        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addWidget(edit_button)
        button_layout.addStretch()

        group_layout.addLayout(button_layout)
        layout.addWidget(group)

    def get_button_style(self, color):
        """버튼 스타일 반환"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                padding: 8px 16px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {color}CC;
            }}
            QPushButton:pressed {{
                background-color: {color}AA;
            }}
        """

    def add_repository(self):
        """Repository/Organization 추가"""
        text, ok = QInputDialog.getText(
            self.parent,
            "Repository/Organization 추가",
            "Repository 또는 Organization 이름을 입력하세요:\n(예: owner/repo 또는 organization)",
            QLineEdit.EchoMode.Normal,
            "",
        )
        if ok and text.strip():
            # 중복 확인
            for i in range(self.repo_list.count()):
                if self.repo_list.item(i).text() == text.strip():
                    QMessageBox.warning(
                        self.parent,
                        "중복 항목",
                        "이미 존재하는 Repository/Organization입니다.",
                    )
                    return

            # 리스트에 추가
            item = QListWidgetItem(text.strip())
            self.repo_list.addItem(item)

            # 설정 저장
            self.save_repositories()

    def remove_repository(self):
        """Repository/Organization 제거"""
        current_item = self.repo_list.currentItem()
        if current_item:
            reply = QMessageBox.question(
                self.parent,
                "제거 확인",
                f"'{current_item.text()}'를 제거하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                row = self.repo_list.row(current_item)
                self.repo_list.takeItem(row)
                self.save_repositories()
        else:
            QMessageBox.information(
                self.parent, "선택 없음", "제거할 Repository/Organization을 선택하세요."
            )

    def edit_repository(self):
        """Repository/Organization 편집"""
        current_item = self.repo_list.currentItem()
        if current_item:
            text, ok = QInputDialog.getText(
                self.parent,
                "Repository/Organization 편집",
                "Repository 또는 Organization 이름을 수정하세요:",
                QLineEdit.EchoMode.Normal,
                current_item.text(),
            )
            if ok and text.strip():
                # 중복 확인 (자기 자신 제외)
                for i in range(self.repo_list.count()):
                    item = self.repo_list.item(i)
                    if item != current_item and item.text() == text.strip():
                        QMessageBox.warning(
                            self.parent,
                            "중복 항목",
                            "이미 존재하는 Repository/Organization입니다.",
                        )
                        return

                # 수정
                current_item.setText(text.strip())
                self.save_repositories()
        else:
            QMessageBox.information(
                self.parent, "선택 없음", "편집할 Repository/Organization을 선택하세요."
            )

    def save_repositories(self):
        """Repository 목록 저장"""
        repositories = []
        for i in range(self.repo_list.count()):
            repositories.append(self.repo_list.item(i).text())

        # 설정에 저장
        self.config_manager.set_github_repositories(repositories)

    def load_repositories(self):
        """Repository 목록 로드"""
        self.config_manager.load_config()
        repositories = self.config_manager.get_github_repositories()
        self.repo_list.clear()
        for repo in repositories:
            item = QListWidgetItem(repo)
            self.repo_list.addItem(item)

    def setup_notification_group(self, layout):
        """GitHub 알림 설정 그룹"""
        group = QGroupBox("🔔 GitHub 알림 설정")
        group.setStyleSheet(
            """
            QGroupBox {
                font-weight: 600;
                font-size: 12px;
                color: #374151;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: #1F2937;
                background-color: #FFFFFF;
            }
        """
        )
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(16, 16, 16, 16)
        group_layout.setSpacing(12)

        # 전역 설정
        self.setup_global_notification_settings(group_layout)

        # 이벤트별 설정
        self.setup_event_notification_settings(group_layout)

        layout.addWidget(group)

    def setup_global_notification_settings(self, layout):
        """전역 알림 설정"""
        global_frame = QFrame()
        global_frame.setStyleSheet(
            """
            QFrame {
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                background-color: #F9FAFB;
                padding: 8px;
            }
        """
        )
        global_layout = QVBoxLayout(global_frame)
        global_layout.setContentsMargins(12, 12, 12, 12)
        global_layout.setSpacing(8)

        # 전역 활성화
        self.github_notifications_enabled = QCheckBox("GitHub 알림 활성화")
        self.github_notifications_enabled.setChecked(True)
        self.github_notifications_enabled.setStyleSheet(
            """
            QCheckBox {
                font-weight: 600;
                font-size: 12px;
                color: #1F2937;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #D1D5DB;
                border-radius: 3px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #10B981;
                border-radius: 3px;
                background-color: #10B981;
            }
        """
        )
        global_layout.addWidget(self.github_notifications_enabled)

        # 요약 설정
        summary_layout = QHBoxLayout()
        self.summary_enabled = QCheckBox("다중 이벤트 요약")
        self.summary_enabled.setChecked(True)
        self.summary_threshold = QSpinBox()
        self.summary_threshold.setRange(2, 20)
        self.summary_threshold.setValue(3)
        self.summary_threshold.setSuffix("개 이상")

        summary_layout.addWidget(self.summary_enabled)
        summary_layout.addWidget(QLabel("임계값:"))
        summary_layout.addWidget(self.summary_threshold)
        summary_layout.addStretch()
        global_layout.addLayout(summary_layout)

        # 속도 제한 설정
        rate_limit_layout = QHBoxLayout()
        self.rate_limit_enabled = QCheckBox("속도 제한")
        self.rate_limit_enabled.setChecked(True)
        self.rate_limit_count = QSpinBox()
        self.rate_limit_count.setRange(5, 100)
        self.rate_limit_count.setValue(20)
        self.rate_limit_count.setSuffix("개")
        self.rate_limit_interval = QSpinBox()
        self.rate_limit_interval.setRange(60, 3600)
        self.rate_limit_interval.setValue(300)
        self.rate_limit_interval.setSuffix("초")

        rate_limit_layout.addWidget(self.rate_limit_enabled)
        rate_limit_layout.addWidget(QLabel("최대"))
        rate_limit_layout.addWidget(self.rate_limit_count)
        rate_limit_layout.addWidget(QLabel("개/"))
        rate_limit_layout.addWidget(self.rate_limit_interval)
        rate_limit_layout.addStretch()
        global_layout.addLayout(rate_limit_layout)

        layout.addWidget(global_frame)

    def setup_event_notification_settings(self, layout):
        """이벤트별 알림 설정"""
        # 이벤트 타입 정의
        self.event_configs = {
            "push": {
                "name": "🚀 Push 이벤트",
                "description": "브랜치에 커밋이 푸시될 때",
                "actions": None,
                "custom_fields": {
                    "min_commits": ("최소 커밋 수", 1, 1, 100),
                    "max_commits": ("최대 커밋 수", 50, 1, 1000),
                    "exclude_branches": ("제외 브랜치", ""),
                    "include_branches": ("포함 브랜치", ""),
                },
            },
            "pull_request": {
                "name": "📝 Pull Request",
                "description": "PR 생성, 업데이트, 머지 등",
                "actions": {
                    "opened": "새 PR 생성",
                    "closed": "PR 닫힘",
                    "reopened": "PR 재개",
                    "edited": "PR 편집",
                    "assigned": "담당자 할당",
                    "review_requested": "리뷰 요청",
                    "synchronize": "PR 업데이트",
                    "ready_for_review": "리뷰 준비",
                },
                "default_actions": [
                    "opened",
                    "closed",
                    "review_requested",
                    "ready_for_review",
                ],
            },
            "issues": {
                "name": "🐛 Issues",
                "description": "이슈 생성, 종료, 할당 등",
                "actions": {
                    "opened": "새 이슈 생성",
                    "closed": "이슈 닫힘",
                    "reopened": "이슈 재개",
                    "assigned": "담당자 할당",
                    "transferred": "이슈 이전",
                },
                "default_actions": ["opened", "closed", "assigned", "transferred"],
            },
            "release": {
                "name": "🎉 Release",
                "description": "릴리즈 생성, 배포 등",
                "actions": {
                    "published": "릴리즈 배포",
                    "created": "릴리즈 생성",
                    "deleted": "릴리즈 삭제",
                    "prereleased": "프리릴리즈",
                    "released": "정식 릴리즈",
                },
                "default_actions": ["published", "prereleased", "released"],
                "custom_fields": {
                    "include_prerelease": ("프리릴리즈 포함", True),
                    "include_draft": ("드래프트 포함", False),
                },
            },
            "workflow": {
                "name": "⚙️ GitHub Actions",
                "description": "워크플로우 실행 상태",
                "actions": {
                    "success": "성공",
                    "failure": "실패",
                    "cancelled": "취소됨",
                    "in_progress": "진행중",
                    "timed_out": "시간초과",
                },
                "default_actions": ["success", "failure", "cancelled", "timed_out"],
            },
            "repository": {
                "name": "📁 Repository",
                "description": "스타, 포크, 브랜치 생성 등",
                "actions": {
                    "star": "스타 추가",
                    "fork": "포크 생성",
                    "create": "브랜치/태그 생성",
                    "delete": "브랜치/태그 삭제",
                },
                "default_actions": ["star", "fork", "create", "delete"],
            },
        }

        # 이벤트별 설정 UI 생성
        self.event_widgets = {}
        for event_type, config in self.event_configs.items():
            event_widget = self.create_event_config_widget(event_type, config)
            self.event_widgets[event_type] = event_widget
            layout.addWidget(event_widget)

    def create_event_config_widget(
        self, event_type: str, config: Dict[str, Any]
    ) -> QWidget:
        """이벤트 설정 위젯 생성"""
        # 메인 프레임
        main_frame = QFrame()
        main_frame.setStyleSheet(
            """
            QFrame {
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                background-color: #FFFFFF;
                margin: 4px;
            }
        """
        )
        main_layout = QVBoxLayout(main_frame)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # 헤더
        header_layout = QHBoxLayout()

        # 활성화 체크박스
        enabled_cb = QCheckBox(config["name"])
        enabled_cb.setChecked(True)
        enabled_cb.setStyleSheet(
            """
            QCheckBox {
                font-weight: 600;
                font-size: 12px;
                color: #1F2937;
            }
        """
        )

        header_layout.addWidget(enabled_cb)
        header_layout.addStretch()

        # 시스템 알림/채팅 버블 체크박스
        system_notification_cb = QCheckBox("시스템 알림")
        system_notification_cb.setChecked(True)
        chat_bubble_cb = QCheckBox("채팅 버블")
        chat_bubble_cb.setChecked(True)

        header_layout.addWidget(system_notification_cb)
        header_layout.addWidget(chat_bubble_cb)

        main_layout.addLayout(header_layout)

        # 설명
        desc_label = QLabel(config["description"])
        desc_label.setStyleSheet(
            """
            QLabel {
                color: #6B7280;
                font-size: 10px;
                margin-bottom: 8px;
            }
        """
        )
        main_layout.addWidget(desc_label)

        # 액션 설정 (있는 경우)
        action_widgets = {}
        if config.get("actions"):
            actions_frame = QFrame()
            actions_frame.setStyleSheet(
                """
                QFrame {
                    border: 1px solid #F3F4F6;
                    border-radius: 4px;
                    background-color: #F9FAFB;
                    padding: 8px;
                }
            """
            )
            actions_layout = QGridLayout(actions_frame)
            actions_layout.setContentsMargins(8, 8, 8, 8)
            actions_layout.setSpacing(4)

            actions_label = QLabel("세부 액션:")
            actions_label.setStyleSheet(
                "font-weight: 600; font-size: 10px; color: #374151;"
            )
            actions_layout.addWidget(actions_label, 0, 0, 1, -1)

            row, col = 1, 0
            default_actions = config.get("default_actions", [])

            for action_key, action_name in config["actions"].items():
                action_cb = QCheckBox(action_name)
                action_cb.setChecked(action_key in default_actions)
                action_cb.setStyleSheet("font-size: 10px;")

                actions_layout.addWidget(action_cb, row, col)
                action_widgets[action_key] = action_cb

                col += 1
                if col > 2:  # 3열로 배치
                    col = 0
                    row += 1

            main_layout.addWidget(actions_frame)

        # 커스텀 필드 (있는 경우)
        custom_widgets = {}
        if config.get("custom_fields"):
            custom_frame = QFrame()
            custom_frame.setStyleSheet(
                """
                QFrame {
                    border: 1px solid #F3F4F6;
                    border-radius: 4px;
                    background-color: #F9FAFB;
                    padding: 8px;
                }
            """
            )
            custom_layout = QFormLayout(custom_frame)
            custom_layout.setContentsMargins(8, 8, 8, 8)
            custom_layout.setSpacing(4)

            for field_key, field_config in config["custom_fields"].items():
                field_name = field_config[0]
                default_value = field_config[1]

                if isinstance(default_value, bool):
                    # 체크박스
                    widget = QCheckBox()
                    widget.setChecked(default_value)
                elif isinstance(default_value, int):
                    # 숫자 입력
                    widget = QSpinBox()  # type: ignore
                    widget.setRange(field_config[2], field_config[3])  # type: ignore
                    widget.setValue(default_value)  # type: ignore
                else:
                    # 텍스트 입력
                    widget = QLineEdit()  # type: ignore
                    widget.setText(str(default_value))  # type: ignore
                    widget.setPlaceholderText("쉼표로 구분 (예: main,master)")  # type: ignore

                widget.setStyleSheet("font-size: 10px;")
                custom_widgets[field_key] = widget
                custom_layout.addRow(field_name + ":", widget)

            main_layout.addWidget(custom_frame)

        # 위젯들을 저장
        widget_data = {
            "enabled": enabled_cb,
            "system_notification": system_notification_cb,
            "chat_bubble": chat_bubble_cb,
            "actions": action_widgets,
            "custom": custom_widgets,
        }

        main_frame.setProperty("widget_data", widget_data)
        return main_frame

    def save_notification_settings(self):
        """알림 설정 저장"""
        settings = {
            "enabled": self.github_notifications_enabled.isChecked(),
            "summary_enabled": self.summary_enabled.isChecked(),
            "summary_threshold": self.summary_threshold.value(),
            "rate_limit_enabled": self.rate_limit_enabled.isChecked(),
            "rate_limit_count": self.rate_limit_count.value(),
            "rate_limit_interval": self.rate_limit_interval.value(),
            "events": {},
        }

        for event_type, widget in self.event_widgets.items():
            widget_data = widget.property("widget_data")
            if widget_data:
                event_settings = {
                    "enabled": widget_data["enabled"].isChecked(),
                    "show_system_notification": widget_data[
                        "system_notification"
                    ].isChecked(),
                    "show_chat_bubble": widget_data["chat_bubble"].isChecked(),
                }

                # 액션 설정
                if widget_data["actions"]:
                    event_settings["actions"] = {
                        action: cb.isChecked()
                        for action, cb in widget_data["actions"].items()
                    }

                # 커스텀 필드
                if widget_data["custom"]:
                    for field_key, widget in widget_data["custom"].items():
                        if isinstance(widget, QCheckBox):
                            event_settings[field_key] = widget.isChecked()
                        elif isinstance(widget, QSpinBox):
                            event_settings[field_key] = widget.value()
                        elif isinstance(widget, QLineEdit):
                            text = widget.text().strip()
                            if field_key.endswith("_branches"):
                                event_settings[field_key] = (
                                    [b.strip() for b in text.split(",") if b.strip()]
                                    if text
                                    else []
                                )
                            else:
                                event_settings[field_key] = text

                settings["events"][event_type] = event_settings

        # JSON으로 저장
        settings_json = json.dumps(settings, ensure_ascii=False, indent=2)
        self.config_manager.set_config_value(
            "GITHUB", "notification_settings", settings_json
        )
        self.config_manager.save_config()

    def load_notification_settings(self):
        """알림 설정 로드"""
        settings_json = self.config_manager.get_config_value(
            "GITHUB", "notification_settings", "{}"
        )
        try:
            settings = json.loads(settings_json) if settings_json else {}
        except json.JSONDecodeError:
            settings = {}

        # 전역 설정 로드
        if hasattr(self, "github_notifications_enabled"):
            self.github_notifications_enabled.setChecked(settings.get("enabled", True))
            self.summary_enabled.setChecked(settings.get("summary_enabled", True))
            self.summary_threshold.setValue(settings.get("summary_threshold", 3))
            self.rate_limit_enabled.setChecked(settings.get("rate_limit_enabled", True))
            self.rate_limit_count.setValue(settings.get("rate_limit_count", 20))
            self.rate_limit_interval.setValue(settings.get("rate_limit_interval", 300))

            # 이벤트별 설정 로드
            events_settings = settings.get("events", {})
            for event_type, widget in self.event_widgets.items():
                widget_data = widget.property("widget_data")
                if widget_data and event_type in events_settings:
                    event_settings = events_settings[event_type]

                    widget_data["enabled"].setChecked(
                        event_settings.get("enabled", True)
                    )
                    widget_data["system_notification"].setChecked(
                        event_settings.get("show_system_notification", True)
                    )
                    widget_data["chat_bubble"].setChecked(
                        event_settings.get("show_chat_bubble", True)
                    )

                    # 액션 설정 로드
                    if widget_data["actions"] and "actions" in event_settings:
                        for action, cb in widget_data["actions"].items():
                            cb.setChecked(event_settings["actions"].get(action, False))

                    # 커스텀 필드 로드
                    if widget_data["custom"]:
                        for field_key, widget in widget_data["custom"].items():
                            if field_key in event_settings:
                                value = event_settings[field_key]
                                if isinstance(widget, QCheckBox):
                                    widget.setChecked(bool(value))
                                elif isinstance(widget, QSpinBox):
                                    widget.setValue(int(value))
                                elif isinstance(widget, QLineEdit):
                                    if field_key.endswith("_branches") and isinstance(
                                        value, list
                                    ):
                                        widget.setText(", ".join(value))
                                    else:
                                        widget.setText(str(value))

    def get_notification_filter_config(self) -> Dict[str, Any]:
        """현재 알림 필터 설정을 반환 (다른 모듈에서 사용)"""
        settings_json = self.config_manager.get_config_value(
            "GITHUB", "notification_settings", "{}"
        )
        try:
            return json.loads(settings_json) if settings_json else {}
        except json.JSONDecodeError:
            return {}
