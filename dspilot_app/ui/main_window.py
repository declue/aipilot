import asyncio
import logging
import os
from typing import Any, Optional

from PySide6.QtCore import QSize, Qt, QThreadPool, QTimer
from PySide6.QtGui import QIcon, QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dspilot_app.services.execution_manager import ExecutionManager
from dspilot_app.services.models.execution_plan import ExecutionPlan, ExecutionStep
from dspilot_app.services.planning_service import PlanningService
from dspilot_app.ui.common.style_manager import StyleManager
from dspilot_app.ui.common.theme_manager import ThemeManager, ThemeMode
from dspilot_app.ui.domain.conversation_manager import ConversationManager
from dspilot_app.ui.domain.message_manager import MessageManager
from dspilot_app.ui.domain.streaming_manager import StreamingManager
from dspilot_app.ui.managers.ui_setup_manager import UISetupManager
from dspilot_app.ui.runnables.llm_agent_worker import LLMAgentWorker
from dspilot_app.ui.settings_window import SettingsWindow
from dspilot_app.ui.widgets.new_message_notification import NewMessageNotification
from dspilot_core.config.config_manager import ConfigManager
from dspilot_core.llm.agents.agent_factory import AgentFactory
from dspilot_core.llm.mcp.mcp_manager import MCPManager
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager
from dspilot_core.tasks.task_manager import TaskManager

# from dspilot_core.tasks.task_thread import TaskThread
from dspilot_core.util.logger import setup_logger

logger: logging.Logger = setup_logger("main_window") or logging.getLogger("main_window")


class MainWindow(QMainWindow):
    """ChatGPT 스타일 메인 창"""

    def __init__(
        self,
        mcp_manager: MCPManager,
        mcp_tool_manager: MCPToolManager,
        planning_service: PlanningService,
        execution_manager: ExecutionManager,
        app_instance: Optional[Any] = None,
    ):
        super().__init__()
        self.config_manager = ConfigManager()
        self.mcp_manager = mcp_manager
        self.mcp_tool_manager = mcp_tool_manager
        self.planning_service = planning_service
        self.execution_manager = execution_manager
        self._app = app_instance  # App 인스턴스 참조 저장
        self.ui_config = self.config_manager.get_ui_config()
        self.tray_app = None  # TrayApp 참조
        self.settings_window: SettingsWindow | None = None
        self.task_thread: Any = None  # TaskThread 참조
        self.message_manager = MessageManager(self)
        self.conversation_manager = ConversationManager()
        self.streaming_manager = StreamingManager(self)
        self.ui_setup_manager = UISetupManager(self)
        self.task_manager: Optional[TaskManager] = None
        self.webhook_status_checker: Optional[QTimer] = None
        self._last_scroll_value = 0
        self._scroll_at_bottom = True

        # 테마 관리자 초기화
        self.theme_manager = ThemeManager(self.config_manager)
        StyleManager.set_theme_manager(self.theme_manager)

        # 테마 변경 시그널 연결
        self.theme_manager.theme_changed.connect(self.on_theme_changed)

        # 스크롤 관련 속성
        self.auto_scroll_enabled = True  # 자동 스크롤 활성화 여부
        self.new_message_notification: Optional[NewMessageNotification] = (
            None  # 새 메시지 알림 위젯
        )

        # UI 컴포넌트들 (UISetupManager에서 설정됨)
        self.input_text: Any = None
        self.send_button: Any = None
        self.stop_button: Any = None
        self.status_label: Any = None
        self.model_selector: Any = None
        self.model_label: Any = None
        self.scroll_area: Any = None
        self.chat_layout: Any = None
        self.theme_toggle_button: Any = None
        self.webhook_status_label: Any = None

        # 창 설정
        self.setWindowTitle("💬 DS Pilot")
        # 최소 크기만 설정하고 크기 조절 가능하게 함
        self.setMinimumSize(800, 600)
        self.resize(1400, 800)  # 초기 크기

        # 윈도우 아이콘 설정
        self.set_window_icon()

        # 윈도우 스타일 설정 (명시적 폰트 크기 사용)
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: #FFFFFF;
                font-family: '{self.ui_config['font_family']}';
                font-size: {self.ui_config['font_size']}px;
            }}

            QMainWindow * {{
                font-family: '{self.ui_config['font_family']}';
                font-size: 12px;  /* 명시적으로 12px 고정 */
            }}
        """
        )

        self.setup_ui()

        # 매니저 인스턴스 생성 (UI 설정 후)
        self.llm_agent = AgentFactory.create_agent(
            config_manager=self.config_manager, mcp_tool_manager=self.mcp_tool_manager
        )

        # 환영 메시지 추가
        self.add_ai_message(
            """안녕하세요! 👋

저는 AI 어시스턴트입니다. 무엇을 도와드릴까요?

**기능:**
- 📝 **질문 답변**: 궁금한 것을 물어보세요
- 💬 **자연스러운 대화**: 일상 대화도 가능합니다
- 🔍 **정보 검색**: 다양한 주제에 대해 알려드립니다
- 🛠️ **도구 활용**: 필요시 외부 도구를 사용해 더 정확한 정보를 제공합니다

*Markdown 문법도 지원하니 자유롭게 대화해보세요!* ✨

⚙️ **설정**: 우측 상단의 설정 버튼으로 LLM API와 MCP 도구를 설정하세요."""
        )

        # 윈도우가 완전히 표시된 후 최신 메시지(환영 메시지)로 스크롤
        QTimer.singleShot(100, self.force_scroll_to_bottom)

        # 초기 테마 적용
        self.apply_current_theme()

        # 테마 토글 버튼 업데이트
        if hasattr(self, "theme_toggle_button"):
            self.update_theme_toggle_button()

        # TaskThread 초기화 및 시작
        # self.init_task_scheduler()

        # Webhook 상태 체크 타이머 설정
        self.init_webhook_status_checker()

        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect signals to slots"""
        self.execution_manager.execution_started.connect(self.on_execution_started)
        self.execution_manager.step_started.connect(self.on_step_started)
        self.execution_manager.step_finished.connect(self.on_step_finished)
        self.execution_manager.step_error.connect(self.on_step_error)
        self.execution_manager.plan_finished.connect(self.on_plan_finished)
        self.execution_manager.final_response_chunk.connect(self.on_final_response_chunk)
        self.execution_manager.final_response_ready.connect(self.on_final_response_ready)

    def on_execution_started(self, plan: ExecutionPlan) -> None:
        """Handles the start of a plan execution."""
        self.add_system_message(f"🚀 **실행 계획 시작:** {plan.description}")

    def on_step_started(self, step: ExecutionStep) -> None:
        """Handles the start of a step."""
        self.add_system_message(f"**[{step.step}단계]** {step.tool_name} 실행: {step.description}")

    def on_step_finished(self, step: ExecutionStep, result: Any) -> None:
        """Handles the completion of a step."""
        result_str = str(result)
        if len(result_str) > 200:
            result_str = result_str[:200] + "..."
        self.add_system_message(f"✅ **[{step.step}단계]** 완료. 결과: `{result_str}`")

    def on_step_error(self, step: ExecutionStep, error: str) -> None:
        """Handles an error in a step."""
        self.add_system_message(f"❌ **[{step.step}단계]** 오류: {error}")

    def on_plan_finished(self, results: dict) -> None:
        """Handles the completion of a plan."""
        self.add_system_message("🏁 **실행 계획 완료.** 최종 응답을 생성합니다.")

    def on_final_response_chunk(self, chunk: str) -> None:
        """Handles a chunk of the final streaming response."""
        self.streaming_manager.add_streaming_chunk(chunk)

    def on_final_response_ready(self, full_response: str, used_tools: list) -> None:
        """Handles the full final response."""
        self.streaming_manager.finish_streaming(full_response)
        if self.streaming_manager.state.current_streaming_bubble:
            self.streaming_manager.state.current_streaming_bubble.set_used_tools(used_tools)
        self.stop_ai_response()  # Clean up worker and buttons

    def set_window_icon(self) -> None:
        """윈도우 아이콘 설정"""
        try:
            # logo.png 파일을 윈도우 아이콘으로 설정
            logo_path = "logo.png"
            if os.path.exists(logo_path):
                window_icon = QIcon(logo_path)
                if not window_icon.isNull():
                    # 다양한 크기의 아이콘 추가 (Windows 작업 표시줄 대응)
                    window_icon.addFile(logo_path, QSize(16, 16))
                    window_icon.addFile(logo_path, QSize(24, 24))
                    window_icon.addFile(logo_path, QSize(32, 32))
                    window_icon.addFile(logo_path, QSize(48, 48))
                    window_icon.addFile(logo_path, QSize(64, 64))
                    window_icon.addFile(logo_path, QSize(96, 96))
                    window_icon.addFile(logo_path, QSize(128, 128))
                    window_icon.addFile(logo_path, QSize(256, 256))

                    self.setWindowIcon(window_icon)

                    # Windows에서 작업 표시줄 아이콘 강제 업데이트
                    if hasattr(self, "winId"):
                        try:
                            import sys

                            if sys.platform == "win32":
                                # 윈도우 핸들을 통한 아이콘 업데이트 시도
                                self.update()
                                self.repaint()
                        except Exception:
                            pass  # 실패해도 계속 진행

                    logger.debug("윈도우 아이콘을 logo.png로 설정 완료 (다중 크기)")
                else:
                    logger.warning("logo.png 파일을 아이콘으로 로드할 수 없습니다")
            else:
                logger.warning("logo.png 파일을 찾을 수 없습니다")
        except Exception as e:
            logger.error("윈도우 아이콘 설정 실패: %s", e)

    def setup_ui(self) -> None:
        """UI 설정"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # UI 매니저 생성 및 설정
        ui_setup_manager = UISetupManager(self)
        self._ui_setup_manager = ui_setup_manager  # 참조 저장

        # 헤더
        ui_setup_manager.setup_header(layout)

        # 채팅 영역
        ui_setup_manager.setup_chat_area(layout)

        # 새 메시지 알림 위젯 설정
        self.setup_new_message_notification()

        # 입력 영역
        ui_setup_manager.setup_input_area(layout)

        # 모델 프로필 변경 시그널 연결
        if hasattr(self, "model_selector") and self.model_selector is not None:
            self.model_selector.currentIndexChanged.connect(self.on_profile_changed)

        # OpenAI 워커 풀
        self.thread_pool = QThreadPool()

    def on_profile_changed(self, index: int) -> None:
        """모델 프로필 변경 시 호출되는 슬롯"""
        if not hasattr(self, "model_selector") or self.model_selector is None or index < 0:
            logger.debug("model_selector가 초기화되지 않았거나 인덱스가 유효하지 않습니다.")
            return

        try:
            profile_id = self.model_selector.itemData(index)
            if profile_id:
                logger.info(f"UI에서 프로필 변경 감지: '{profile_id}'")

                # 1. ConfigManager에서 현재 프로필 변경 (올바른 메서드 사용)
                self.config_manager.set_current_profile(profile_id)

                # 2. 프로필 변경 확인을 위한 로그
                new_config = self.config_manager.get_llm_config()
                api_key = new_config.get("api_key", "")
                api_key_preview = (
                    api_key[:10] + "..." if api_key and len(api_key) > 10 else "설정되지 않음"
                )
                logger.info(
                    f"새 프로필 설정 확인: 모델={new_config.get('model')}, API 키={api_key_preview}, base_url={new_config.get('base_url')}"
                )

                # 3. LLM Agent 및 MCPToolManager 클라이언트 재초기화
                if hasattr(self, "llm_agent"):
                    self.llm_agent.reinitialize_client()
                    logger.info("LLM Agent 클라이언트 재초기화 완료")

                # MCPToolManager는 reinitialize_client 메서드가 없으므로 주석 처리
                # if hasattr(self, "mcp_tool_manager"):
                #     self.mcp_tool_manager.reinitialize_client()
                #     logger.info("MCP Tool Manager 클라이언트 재초기화 완료")

                # 4. UI의 모델 라벨 업데이트
                self.update_model_label()

                # 5. 모델 변경 알림만 표시 (대화 맥락은 유지)
                if hasattr(self, "message_manager") and self.message_manager is not None:
                    current_text = (
                        self.model_selector.currentText() if self.model_selector else "알 수 없음"
                    )
                    QTimer.singleShot(
                        100,
                        lambda: self.add_system_message(
                            f"✅ **시스템**: 언어 모델이 **{current_text}** (으)로 변경되었습니다. 기존 대화를 이어가실 수 있습니다."
                        ),
                    )

        except Exception as e:
            logger.error(f"프로필 변경 처리 중 오류 발생: {e}")
            import traceback

            logger.error(f"프로필 변경 오류 상세: {traceback.format_exc()}")
            # 사용자에게 오류 알림 (add_system_message가 초기화되었을 때만)
            if hasattr(self, "message_manager") and self.message_manager is not None:
                self.add_system_message(
                    f"❌ **오류**: 프로필 변경 중 문제가 발생했습니다: {str(e)}"
                )

    def on_settings_changed(self) -> None:
        """설정이 변경되었을 때 호출"""
        logger.debug("UI 설정이 변경되었습니다")
        self.ui_config = self.config_manager.get_ui_config()
        # UI 요소들 업데이트
        self.update_ui_styles()
        # 모델 선택 드롭다운 업데이트
        self.refresh_model_selector()

    def update_ui_styles(self) -> None:
        """UI 스타일 업데이트"""
        # 메인 윈도우 스타일 업데이트
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: #FFFFFF;
                color: #1F2937;
                font-family: '{self.ui_config['font_family']}';
                font-size: {self.ui_config['font_size']}px;
            }}

            QMainWindow * {{
                font-family: '{self.ui_config['font_family']}';
            }}
        """
        )

        # UI 요소들을 다시 설정하여 새로운 폰트 설정 적용
        self.refresh_ui_elements()

    def refresh_ui_elements(self) -> None:
        """UI 요소들의 스타일을 새로운 설정으로 업데이트"""
        # 모델 라벨 업데이트
        if hasattr(self, "model_label") and self.model_label is not None:
            self.model_label.setStyleSheet(
                f"""
                QLabel {{
                    color: #6B7280;
                    background-color: #F9FAFB;
                    font-size: 12px;
                    font-weight: 500;
                    border: 1px solid #E5E7EB;
                    border-radius: 12px;
                    padding: 4px 12px;
                    margin-left: 16px;
                    font-family: '{self.ui_config['font_family']}';
                }}
            """
            )  # 상태 라벨 업데이트
        if hasattr(self, "status_label") and self.status_label is not None:
            self.status_label.setStyleSheet(
                f"""
                QLabel {{
                    color: #059669;
                    background-color: transparent;
                    border: none;
                    padding: 8px 16px;
                    font-size: {max(self.ui_config['font_size'] - 2, 10)}px;
                    font-family: '{self.ui_config['font_family']}';
                }}
            """
            )

        # 입력창 업데이트
        if hasattr(self, "input_text") and self.input_text is not None:
            self.input_text.setStyleSheet(
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

        # 전송 버튼 업데이트
        if hasattr(self, "send_button") and self.send_button is not None:
            self.send_button.setStyleSheet(
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

        # 중단 버튼 업데이트
        if hasattr(self, "stop_button") and self.stop_button is not None:
            self.stop_button.setStyleSheet(
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

        # 헤더 버튼들 업데이트
        header_buttons = self.findChildren(QPushButton)
        for button in header_buttons:
            if button.text() == "🆕 새 대화":
                button.setStyleSheet(
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
            elif button.text() == "⚙️ 설정":
                button.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: #F8FAFC;
                        color: #475569;
                        border: 2px solid #E2E8F0;
                        border-radius: 20px;
                        font-size: 14px;
                        font-weight: 600;
                        font-family: '{self.ui_config['font_family']}';
                    }}
                    QPushButton:hover {{
                        background-color: #F1F5F9;
                        border-color: #CBD5E1;
                    }}
                    QPushButton:pressed {{
                        background-color: #E2E8F0;
                        border-color: #94A3B8;
                    }}
                """
                )

        # 도움말 텍스트 업데이트
        help_labels = self.findChildren(QLabel)
        for label in help_labels:
            if "💡 Markdown" in label.text():
                label.setStyleSheet(
                    f"""
                    QLabel {{
                        color: #6B7280;
                        font-size: {max(self.ui_config['font_size'] - 2, 10)}px;
                        font-family: '{self.ui_config['font_family']}';
                    }}
                """
                )

        # 기존 채팅 메시지들의 스타일도 업데이트하기 위해 메시지 매니저에 알림
        if hasattr(self, "message_manager") and self.message_manager is not None:
            self.message_manager.update_all_message_styles()

    def update_model_label(self) -> None:
        """모델명 라벨 업데이트"""
        if not hasattr(self, "model_label") or self.model_label is None:
            logger.debug("model_label이 아직 초기화되지 않았습니다. 건너뜁니다.")
            return

        try:
            llm_config = self.config_manager.get_llm_config()
            model = llm_config.get("model", "설정 필요")
            self.model_label.setText(f"📋 {model}")
            logger.debug(f"모델명 업데이트: {model}")
        except Exception as e:
            self.model_label.setText("📋 설정 필요")
            logger.warning(f"모델명 업데이트 실패: {e}")

    def eventFilter(self, obj: Any, event: Any) -> bool:
        """이벤트 필터 - 입력창 키 이벤트 처리"""
        if obj == self.input_text and hasattr(event, "type"):
            from PySide6.QtCore import QEvent

            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Return:
                    if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                        # Shift+Enter: 줄바꿈
                        return False  # 기본 동작 수행
                    else:
                        # Enter: 메시지 전송
                        self.send_message()
                        return True  # 이벤트 처리됨
        return super().eventFilter(obj, event)

    def input_key_press_event(self, event: QKeyEvent) -> None:
        """입력창 키 이벤트 처리 (deprecated - eventFilter 사용)"""
        # 이 메서드는 더 이상 사용되지 않지만 호환성을 위해 유지
        if event.key() == Qt.Key.Key_Return:
            if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                # Shift+Enter: 줄바꿈
                QTextEdit.keyPressEvent(self.input_text, event)
            else:
                # Enter: 메시지 전송
                self.send_message()
        else:
            QTextEdit.keyPressEvent(self.input_text, event)

    def send_message(self) -> None:
        """메시지 전송"""
        message = self.input_text.toPlainText().strip()
        if not message:
            return

        # 입력창 비우기
        self.input_text.clear()

        # 사용자 메시지 표시
        self.add_user_message(message)

        # 대화 히스토리에 사용자 메시지 추가 (ConversationManager)
        self.conversation_manager.add_user_message(message)

        # LLM Agent의 대화 히스토리에도 추가
        if hasattr(self, "llm_agent"):
            self.llm_agent.add_user_message(message)

        # AI 응답 요청
        self.request_ai_response(message)

    def add_user_message(self, message: str) -> None:
        """사용자 메시지 추가"""
        self.message_manager.add_user_message(message)

    def add_ai_message(self, message: str, used_tools: Optional[list] = None) -> None:
        """AI 메시지 추가"""
        self.message_manager.add_ai_message(message, used_tools)

    def setup_new_message_notification(self) -> None:
        """새 메시지 알림 위젯 설정"""
        if hasattr(self, "scroll_area") and self.scroll_area:
            # 스크롤 영역 위에 새 메시지 알림 위젯 생성
            self.new_message_notification = NewMessageNotification(self.scroll_area)
            self.new_message_notification.scroll_to_bottom_requested.connect(
                self.force_scroll_to_bottom
            )

            # 스크롤 이벤트 감지를 위한 연결
            if hasattr(self.scroll_area, "verticalScrollBar"):
                scrollbar = self.scroll_area.verticalScrollBar()
                if scrollbar:
                    scrollbar.valueChanged.connect(self._on_scroll_changed)
                    scrollbar.rangeChanged.connect(self._on_scroll_range_changed)

    def _on_scroll_changed(self, value: int) -> None:
        """스크롤 위치 변경 감지"""
        if hasattr(self, "scroll_area") and self.scroll_area:
            scrollbar = self.scroll_area.verticalScrollBar()
            if scrollbar:
                # 사용자가 수동으로 스크롤한 경우 자동 스크롤 비활성화
                if abs(value - scrollbar.maximum()) > 50:  # 50px 이상 차이가 나면
                    self.auto_scroll_enabled = False
                    logger.debug("사용자 스크롤로 인해 자동 스크롤 비활성화")
                else:
                    # 거의 맨 아래에 있으면 자동 스크롤 활성화
                    self.auto_scroll_enabled = True
                    if self.new_message_notification:
                        self.new_message_notification.hide()

    def _on_scroll_range_changed(self, _min_val: int, _max_val: int) -> None:
        """스크롤 범위 변경 감지 (새 메시지 추가 시)"""
        if not self.auto_scroll_enabled and self.new_message_notification:
            # 자동 스크롤이 비활성화된 상태에서 새 메시지가 추가되면 알림 표시
            self.new_message_notification.position_on_parent()
            self.new_message_notification.show_notification()
            logger.debug("새 메시지 알림 표시")

    def scroll_to_bottom(self) -> None:
        """스크롤을 맨 아래로 이동 (자동 스크롤 활성화 시에만)"""
        if self.auto_scroll_enabled and hasattr(self, "scroll_area") and self.scroll_area:
            # 약간의 지연을 두고 스크롤 (레이아웃 업데이트 후)
            QTimer.singleShot(50, self._do_scroll_to_bottom)

    def force_scroll_to_bottom(self) -> None:
        """강제로 스크롤을 맨 아래로 이동 (알림 클릭 시)"""
        self.auto_scroll_enabled = True  # 자동 스크롤 다시 활성화
        if hasattr(self, "scroll_area") and self.scroll_area:
            QTimer.singleShot(50, self._do_scroll_to_bottom)

    def _do_scroll_to_bottom(self) -> None:
        """실제 스크롤 동작 실행"""
        if hasattr(self, "scroll_area") and self.scroll_area:
            # 수직 스크롤바를 맨 아래로 이동
            vertical_scrollbar = self.scroll_area.verticalScrollBar()
            if vertical_scrollbar:
                vertical_scrollbar.setValue(vertical_scrollbar.maximum())

    def adjust_window_size(self) -> None:
        """창 크기 조정 - 스크롤 방식에서는 사용하지 않음"""
        # 스크롤 방식을 사용하므로 창 크기를 고정적으로 유지

    def stop_ai_response(self) -> None:
        """AI 응답 중지 및 관련 UI 상태 초기화"""
        if self.streaming_manager.is_streaming():
            self.streaming_manager.stop_streaming()

        if self.llm_agent:
            self.llm_agent.cancel()

        self.input_text.setDisabled(False)
        self.send_button.setDisabled(False)
        self.stop_button.hide()
        self.send_button.show()
        logger.debug("AI 응답 중지 및 UI 활성화")
        self.input_text.setFocus()

    def request_ai_response(self, message: str) -> None:
        """사용자 메시지에 대한 AI 응답 요청 (메인 로직)"""
        if not self.llm_agent:
            self.add_system_message("LLM 에이전트가 초기화되지 않았습니다.")
            return

        self.input_text.setDisabled(True)
        self.send_button.setDisabled(True)
        self.stop_button.show()
        self.send_button.hide()

        async def run_request():
            try:
                # 1. Analyze the request and create a plan
                plan = await self.planning_service.analyze_request_and_plan(message)

                if plan and plan.steps:
                    # 2. If a plan exists, execute it
                    await self.execution_manager.execute_plan(plan, message)
                    # The final response is handled by signals from ExecutionManager
                else:
                    # 3. If no plan, proceed with a direct chat response
                    logger.info("실행 계획이 없습니다. 일반 채팅 응답을 진행합니다.")
                    worker = LLMAgentWorker(
                        user_message=message,
                        llm_agent=self.llm_agent,
                    )
                    worker.signals.streaming_started.connect(self.on_streaming_started)
                    worker.signals.streaming_chunk.connect(self.on_streaming_chunk)
                    worker.signals.streaming_finished.connect(self.on_streaming_finished)
                    worker.signals.error.connect(self.handle_ai_error)
                    self.streaming_manager.state.current_worker = worker
                    QThreadPool.globalInstance().start(worker)

            except Exception as e:
                logger.error(f"AI 응답 요청 중 오류 발생: {e}", exc_info=True)
                self.handle_ai_error(f"오류 발생: {e}")

        asyncio.run(run_request())

    def on_streaming_started(self) -> None:
        """스트리밍 시작 시 호출"""
        self.streaming_manager.start_streaming()
        logger.debug("스트리밍 UI 시작")
        if hasattr(self, "status_label") and self.status_label is not None:
            self.status_label.setText("답변 중...")

    def on_streaming_chunk(self, chunk: str) -> None:
        """스트리밍 청크 수신 시 호출"""
        logger.debug(f"📦 스트리밍 청크 수신: {chunk[:50]}...")
        self.streaming_manager.add_streaming_chunk(chunk)

    def on_streaming_finished(self) -> None:
        """스트리밍 완료 시 호출"""
        if not self.streaming_manager.is_streaming():  # 이미 중단된 경우 무시
            return

        # StreamingManager의 스트리밍 완료 처리 호출
        self.streaming_manager.on_streaming_finished()  # UI 상태 복원
        if hasattr(self, "status_label") and self.status_label is not None:
            self.status_label.setText("준비됨")
            self.status_label.setStyleSheet(
                f"""
                QLabel {{
                    color: #059669;
                    background-color: transparent;
                    border: none;
                    padding: 8px 16px;
                    font-size: {max(self.ui_config['font_size'] - 2, 10)}px;
                    font-family: '{self.ui_config['font_family']}';
                }}
            """
            )

        if hasattr(self, "send_button"):
            self.send_button.setEnabled(True)
            self.send_button.show()

        # 버튼 상태 복원
        if hasattr(self, "stop_button"):
            self.stop_button.hide()

        # 현재 AI 버블의 Raw 버튼 표시 (스트리밍 완료됨을 알림)
        if hasattr(self, "message_manager"):
            self.message_manager.show_current_ai_raw_button()

        # 창 크기 조정 (스트리밍 완료 후 강제 스크롤)
        self.force_scroll_to_bottom()

    def handle_ai_error(self, error_msg: str) -> None:
        """AI 응답 중 에러 발생 시 처리"""
        logger.error("AI 응답 에러: %s", error_msg)
        self.add_system_message(f"죄송합니다. 응답 생성 중 오류가 발생했습니다.\n\n오류: {error_msg}")
        self.stop_ai_response()

    def adjust_browser_height(self, browser: Any) -> None:
        """브라우저 높이 자동 조정"""
        document = browser.document()
        document_height = document.size().height()
        browser.setFixedHeight(int(document_height) + 10)

    def closeEvent(self, event: Any) -> None:  # pylint: disable=invalid-name
        """창 닫기 이벤트"""
        # 창 닫기 시 트레이로 숨김
        if hasattr(self, "tray_app") and self.tray_app:
            logger.debug("창 닫기 -> 트레이로 숨김")
            event.ignore()
            self.hide()
        else:
            # 완전 종료 시 TaskThread 정리
            # if hasattr(self, "task_thread") and self.task_thread:
            #     logger.info("작업 스케줄러 스레드 종료 중...")
            #     self.task_thread.stop_scheduler()
            #     self.task_thread.quit()
            #     self.task_thread.wait(3000)  # 3초 대기
            #     logger.info("작업 스케줄러 스레드 종료 완료")
            event.accept()

    def showEvent(self, event: Any) -> None:  # pylint: disable=invalid-name
        """창 표시 이벤트 - 윈도우가 표시될 때마다 최신 알림으로 스크롤"""
        super().showEvent(event)
        # 윈도우가 완전히 표시된 후 최신 알림으로 스크롤
        QTimer.singleShot(250, self.force_scroll_to_bottom)
        # 트레이 깜박임 중지
        if hasattr(self, "tray_app") and self.tray_app:
            self.tray_app.on_window_activated()
        logger.debug("윈도우 표시됨 - 최신 알림으로 스크롤")

    def focusInEvent(self, event: Any) -> None:  # pylint: disable=invalid-name
        """포커스 입력 이벤트 - 윈도우가 포커스를 받았을 때"""
        super().focusInEvent(event)
        # 트레이 깜박임 중지
        if hasattr(self, "tray_app") and self.tray_app:
            self.tray_app.on_window_activated()
        logger.debug("윈도우 포커스 받음 - 트레이 깜박임 중지")

    def activateEvent(self, event: Any) -> None:  # pylint: disable=invalid-name
        """윈도우 활성화 이벤트"""
        # super().activateEvent(event)  # QMainWindow에 activateEvent가 없음
        # 트레이 깜박임 중지
        if hasattr(self, "tray_app") and self.tray_app:
            self.tray_app.on_window_activated()
        logger.debug("윈도우 활성화됨 - 트레이 깜박임 중지")

    def changeEvent(self, event: Any) -> None:  # pylint: disable=invalid-name
        """윈도우 상태 변경 이벤트 - 최소화/복원 등"""
        super().changeEvent(event)

        if event.type() == event.Type.WindowStateChange:
            # 윈도우 상태 변경 시 로그 출력
            is_minimized = self.isMinimized()
            is_maximized = self.isMaximized()
            is_active = self.isActiveWindow()
            is_visible = self.isVisible()

            logger.debug(
                f"윈도우 상태 변경: minimized={is_minimized}, maximized={is_maximized}, active={is_active}, visible={is_visible}"
            )
            print(
                f"[DEBUG] 윈도우 상태 변경: minimized={is_minimized}, maximized={is_maximized}, active={is_active}, visible={is_visible}"
            )

            # 윈도우가 복원되거나 활성화되면 트레이 깜박임 중지
            if not is_minimized and is_active and hasattr(self, "tray_app") and self.tray_app:
                self.tray_app.on_window_activated()
                logger.debug("윈도우 복원/활성화 - 트레이 깜박임 중지")

        elif event.type() == event.Type.ActivationChange:
            # 활성화 상태 변경
            is_active = self.isActiveWindow()
            # logger.debug(f"윈도우 활성화 상태 변경: active={is_active}")
            # print(f"[DEBUG] 윈도우 활성화 상태 변경: active={is_active}")

            # 활성화되면 트레이 깜박임 중지
            if is_active and hasattr(self, "tray_app") and self.tray_app:
                self.tray_app.on_window_activated()
                logger.debug("윈도우 활성화로 인한 트레이 깜박임 중지")

    def init_task_scheduler(self) -> None:
        """작업 스케줄러 초기화"""
        # try:
        #
        #     self.task_thread = TaskThread()
        #     self.task_thread.start()
        #     logger.info("작업 스케줄러 스레드 시작됨")
        # except Exception as e:
        #     logger.error(f"작업 스케줄러 초기화 실패: {e}")
        pass  # Temporarily disabled

    def init_webhook_status_checker(self) -> None:
        """Webhook 서버 상태 체크 타이머 초기화"""
        try:
            # 주기적으로 webhook 상태를 체크하는 타이머 설정
            self.webhook_status_timer = QTimer()
            self.webhook_status_timer.timeout.connect(self.check_webhook_status)
            self.webhook_status_timer.start(30000)  # 30초마다 체크

            # 초기 상태 체크
            QTimer.singleShot(2000, self.check_webhook_status)  # 2초 후 첫 체크

            logger.info("Webhook 상태 체크 타이머 초기화 완료")
        except Exception as e:
            logger.error(f"Webhook 상태 체크 타이머 초기화 실패: {e}")

    def check_webhook_status(self) -> None:
        """Webhook 서버 연결 상태 체크"""
        try:
            logger.info("=== Webhook 상태 체크 시작 ===")
            logger.info(f"self._app 존재 여부: {hasattr(self, '_app')}")
            logger.info(
                f"self._app이 None이 아님: {hasattr(self, '_app') and self._app is not None}"
            )

            # App 인스턴스에서 webhook_client 가져오기
            if hasattr(self, "_app") and self._app and hasattr(self._app, "webhook_client"):
                webhook_client = self._app.webhook_client
                logger.info(f"App 인스턴스에서 webhook_client 확인: {webhook_client is not None}")

                if webhook_client:
                    client_id = getattr(webhook_client, "client_id", "None")
                    logger.info(f"✅ Webhook client 발견! client_id={client_id}")
                    self.update_webhook_status_connected(webhook_client)
                else:
                    logger.info("❌ Webhook client가 None이므로 비활성화 상태로 설정")
                    self.update_webhook_status_disabled()
            else:
                logger.info(f"❌ App 인스턴스 체크 실패:")
                logger.info(f"  - hasattr(self, '_app'): {hasattr(self, '_app')}")
                logger.info(f"  - self._app: {getattr(self, '_app', 'NOT_SET')}")
                logger.info(
                    f"  - hasattr(self._app, 'webhook_client'): {hasattr(getattr(self, '_app', None), 'webhook_client') if hasattr(self, '_app') else 'N/A'}"
                )

                # App 인스턴스가 없는 경우 설정에서 직접 확인
                webhook_enabled_str = self.config_manager.get_config_value(
                    "WEBHOOK", "enabled", "false"
                )
                webhook_enabled = (
                    webhook_enabled_str.lower() == "true" if webhook_enabled_str else False
                )
                logger.info(f"설정에서 Webhook 활성화 상태: {webhook_enabled}")

                if webhook_enabled:
                    logger.info("⚠️ Webhook이 활성화되어 있지만 연결되지 않음")
                    self.update_webhook_status_disconnected()
                else:
                    logger.info("⚫ Webhook이 비활성화됨")
                    self.update_webhook_status_disabled()

            logger.info("=== Webhook 상태 체크 완료 ===")
        except Exception as e:
            logger.error(f"❌ Webhook 상태 체크 실패: {e}")
            import traceback

            logger.error(f"상세 오류: {traceback.format_exc()}")
            self.update_webhook_status_error()

    def update_webhook_status_connected(self, webhook_client: Any) -> None:
        """Webhook 연결됨 상태로 UI 업데이트"""
        if not hasattr(self, "webhook_status_label") or not self.webhook_status_label:
            logger.debug("webhook_status_label이 없어서 상태 업데이트 건너뜀")
            return

        try:
            logger.debug(
                f"Webhook 연결 상태 업데이트 시도: client_id={getattr(webhook_client, 'client_id', 'None')}"
            )

            # 클라이언트 ID가 있으면 연결된 것으로 간주
            if hasattr(webhook_client, "client_id") and webhook_client.client_id:
                logger.info(
                    f"Webhook 연결됨 - UI를 초록색으로 업데이트: client_id={webhook_client.client_id}"
                )
                self.webhook_status_label.setText("🟢")
                self.webhook_status_label.setStyleSheet(
                    """
                    QLabel {
                        color: #10B981;
                        background-color: #ECFDF5;
                        border: 1px solid #10B981;
                        border-radius: 16px;
                        font-size: 14px;
                        padding: 4px;
                    }
                    """
                )
                webhook_server_url = getattr(webhook_client, "webhook_server_url", "알 수 없음")
                self.webhook_status_label.setToolTip(
                    f"Webhook 서버 연결됨\n"
                    f"클라이언트 ID: {webhook_client.client_id}\n"
                    f"서버: {webhook_server_url}"
                )
            else:
                logger.debug("client_id가 없어서 연결 안됨 상태로 설정")
                self.update_webhook_status_disconnected()
        except Exception as e:
            logger.error(f"Webhook 연결 상태 업데이트 실패: {e}")
            import traceback

            logger.error(f"상세 오류: {traceback.format_exc()}")
            self.update_webhook_status_error()

    def update_webhook_status_disconnected(self) -> None:
        """Webhook 연결 안됨 상태로 UI 업데이트"""
        if not hasattr(self, "webhook_status_label") or not self.webhook_status_label:
            return

        self.webhook_status_label.setText("🔴")
        self.webhook_status_label.setStyleSheet(
            """
            QLabel {
                color: #EF4444;
                background-color: #FEF2F2;
                border: 1px solid #EF4444;
                border-radius: 16px;
                font-size: 14px;
                padding: 4px;
            }
            """
        )
        webhook_url = self.config_manager.get_config_value("WEBHOOK", "server_url", "설정되지 않음")
        self.webhook_status_label.setToolTip(
            f"Webhook 서버 연결 안됨\n" f"서버: {webhook_url}\n" f"서버가 실행 중인지 확인하세요"
        )

    def update_webhook_status_disabled(self) -> None:
        """Webhook 비활성화 상태로 UI 업데이트"""
        if not hasattr(self, "webhook_status_label") or not self.webhook_status_label:
            return

        self.webhook_status_label.setText("⚫")
        self.webhook_status_label.setStyleSheet(
            """
            QLabel {
                color: #6B7280;
                background-color: #F9FAFB;
                border: 1px solid #D1D5DB;
                border-radius: 16px;
                font-size: 14px;
                padding: 4px;
            }
            """
        )
        self.webhook_status_label.setToolTip(
            "Webhook 기능 비활성화됨\n" "설정에서 Webhook을 활성화할 수 있습니다"
        )

    def update_webhook_status_error(self) -> None:
        """Webhook 오류 상태로 UI 업데이트"""
        if not hasattr(self, "webhook_status_label") or not self.webhook_status_label:
            return

        self.webhook_status_label.setText("⚠️")
        self.webhook_status_label.setStyleSheet(
            """
            QLabel {
                color: #F59E0B;
                background-color: #FFFBEB;
                border: 1px solid #F59E0B;
                border-radius: 16px;
                font-size: 14px;
                padding: 4px;
            }
            """
        )
        self.webhook_status_label.setToolTip(
            "Webhook 상태 확인 중 오류 발생\n" "연결 상태를 확인할 수 없습니다"
        )

    def set_app_reference(self, app_instance: Any) -> None:
        """App 인스턴스 참조 설정 (런타임에 설정용)"""
        logger.debug(f"App 인스턴스 참조 설정: {app_instance is not None}")
        self._app = app_instance
        # App 참조가 설정되면 즉시 webhook 상태 체크
        if app_instance:
            logger.debug("App 참조 설정 후 즉시 webhook 상태 체크 실행")
            QTimer.singleShot(1000, self.check_webhook_status)  # 1초 후 체크

    def force_webhook_status_refresh(self) -> None:
        """Webhook 상태를 강제로 새로고침"""
        logger.info("Webhook 상태 강제 새로고침 요청됨")
        self.check_webhook_status()

    def open_settings(self) -> None:
        """설정창 열기"""
        if not hasattr(self, "settings_window") or self.settings_window is None:
            # MCP 관리자와 TaskThread를 설정창에 전달
            self.settings_window = SettingsWindow(
                self.config_manager, self, self.mcp_manager, self.mcp_tool_manager
            )
            self.settings_window.settings_changed.connect(self.on_settings_changed)

            # TaskThread를 TaskTabManager에 전달
            # if self.task_thread and hasattr(self.settings_window, "task_tab_manager"):
            #     self.settings_window.task_tab_manager.set_task_thread(self.task_thread)

            # 현재 테마를 설정창에 적용
            if hasattr(self.settings_window, "update_theme"):
                self.settings_window.update_theme()

        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def start_new_conversation(self) -> None:
        """새로운 대화 시작"""
        # message_manager가 초기화되지 않았으면 리턴
        if not hasattr(self, "message_manager") or self.message_manager is None:
            return

        # 대화 히스토리 초기화
        self.conversation_manager.clear_history()

        # LLM Agent 대화 히스토리도 초기화
        if hasattr(self, "llm_agent"):
            self.llm_agent.clear_conversation()

        # 채팅 영역 비우기
        self.message_manager.clear_chat_area()

        # 환영 메시지 다시 추가
        self.add_ai_message(
            """새로운 대화를 시작합니다! 👋

안녕하세요! 저는 AI 어시스턴트입니다. 무엇을 도와드릴까요?

**이전 대화 맥락이 초기화되었습니다.** 새로운 주제로 대화해보세요!

⚙️ **설정**: 우측 상단의 설정 버튼으로 LLM API와 MCP 도구를 설정하세요."""
        )

        # 환영 메시지 추가 후 스크롤
        QTimer.singleShot(100, self.force_scroll_to_bottom)

        logger.debug("새로운 대화 시작됨")

    def add_api_message_to_chat(self, message_type: str, content: str) -> None:
        """API로 받은 메시지를 대화창에 추가"""
        logger.debug("API 메시지 추가: %s - %s", message_type, content)

        # 메시지 타입에 따라 다른 스타일로 표시
        if message_type == "html_notification":
            # HTML 알림은 HTML로 렌더링
            self.message_manager.add_html_message(content)
        elif message_type == "notification":
            # GitHub 관련 메시지인지 확인
            if self._is_github_message(content):
                # GitHub 메시지는 GitHub 아이콘으로 표시
                self.message_manager.add_github_message(content)
            else:
                # 일반 알림 메시지는 시스템 메시지로 표시
                formatted_content = f"📬 **알림 메시지**\n\n{content}"
                self.add_system_message(formatted_content)
        elif message_type == "system":
            # 시스템 메시지는 시스템 메시지로 표시
            self.add_system_message(content)
        elif message_type == "api_message":
            # API 메시지는 사용자 메시지로 표시
            self.add_user_message(content)
        else:
            # 기본적으로 시스템 메시지로 표시
            self.add_system_message(f"**{message_type}**\n\n{content}")

        # 메시지 추가 후 스크롤 (자동 스크롤 활성화 시에만)
        self.scroll_to_bottom()

    def _is_github_message(self, content: str) -> bool:
        """메시지가 GitHub 관련인지 확인"""
        github_keywords = [
            "GitHub",
            "github",
            "push",
            "pull request",
            "issue",
            "commit",
            "repository",
            "repo",
            "branch",
            "merge",
            "star",
            "fork",
            "release",
            "워크플로우",
            "workflow",
            "GitHub Actions",
            "체크",
            "check",
        ]

        # 메시지 내용에 GitHub 관련 키워드가 포함되어 있는지 확인
        content_lower = content.lower()
        is_github = any(keyword.lower() in content_lower for keyword in github_keywords)

        if is_github:
            logger.info(f"GitHub 메시지 감지됨: {content[:100]}...")
        else:
            logger.debug(f"일반 메시지로 분류됨: {content[:50]}...")

        return is_github

    def add_system_message(self, message: str) -> None:
        """시스템 메시지 추가 (API 알림 등)"""
        if hasattr(self, "message_manager") and self.message_manager is not None:
            self.message_manager.add_system_message(message)

    def add_user_message_from_api(self, content: str) -> None:
        """API로부터 사용자 메시지 추가"""
        logger.debug("API 사용자 메시지 추가: %s...", content[:50])
        self.add_user_message(content)

    def trigger_llm_response_from_api(self, prompt: str) -> None:
        """API로부터 LLM 응답 요청"""
        logger.debug("API LLM 응답 요청: %s...", prompt[:50])

        # 먼저 사용자 메시지로 추가
        self.add_user_message(prompt)

        # 대화 히스토리에 사용자 메시지 추가 (중요!)
        self.conversation_manager.add_user_message(prompt)

        # 그 다음 AI 응답 요청
        self.request_ai_response(prompt)

    def refresh_model_selector(self) -> None:
        """모델 선택 드롭다운 새로고침"""
        if not hasattr(self, "model_selector") or self.model_selector is None:
            logger.debug("model_selector가 아직 초기화되지 않았습니다. 건너뜁니다.")
            return

        try:
            profiles = self.config_manager.get_llm_profiles()
            current_profile = self.config_manager.get_current_profile_name()

            # 드롭다운 업데이트
            self.model_selector.clear()

            for profile_id, profile_data in profiles.items():
                display_name = f"{profile_data['name']} ({profile_data['model']})"
                self.model_selector.addItem(display_name, profile_id)

            # 현재 프로필 다시 선택
            for i in range(self.model_selector.count()):
                if self.model_selector.itemData(i) == current_profile:
                    self.model_selector.setCurrentIndex(i)
                    break
        except Exception as e:
            logger.error(f"모델 선택 드롭다운 새로고침 실패: {e}")

    def toggle_theme(self) -> None:
        """테마를 토글합니다."""
        try:
            new_theme = self.theme_manager.toggle_theme()
            logger.info(f"테마 변경됨: {new_theme.value}")
        except Exception as e:
            logger.error(f"테마 토글 실패: {e}")

    def on_theme_changed(self, theme: ThemeMode) -> None:
        """테마 변경 시 호출되는 슬롯"""
        try:
            logger.info(f"테마 변경 신호 수신: {theme.value}")
            self.apply_current_theme()
            self.update_theme_toggle_button()
        except Exception as e:
            logger.error(f"테마 변경 처리 실패: {e}")

    def apply_current_theme(self) -> None:
        """현재 테마를 UI에 적용합니다."""
        try:
            # 테마 색상 가져오기
            colors = self.theme_manager.get_theme_colors()

            # 메인 윈도우 전체 스타일 적용
            main_window_style = f"""
            QMainWindow {{
                background-color: {colors['background']};
                color: {colors['text']};
                font-family: '{self.ui_config['font_family']}';
                font-size: {self.ui_config['font_size']}px;
            }}
            
            QWidget {{
                background-color: {colors['background']};
                color: {colors['text']};
                font-family: '{self.ui_config['font_family']}';
            }}
            
            QFrame {{
                background-color: {colors['background']};
                color: {colors['text']};
            }}
            
            QLabel {{
                color: {colors['text']};
                background-color: transparent;
            }}
            
            QTextEdit {{
                background-color: {colors['input_background']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
            }}
            
            QScrollArea {{
                background-color: {colors['background']};
                border: none;
            }}
            
            QScrollBar:vertical {{
                background-color: {colors['surface']};
                width: 12px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {colors['scrollbar']};
                border-radius: 6px;
                min-height: 20px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {colors['scrollbar_hover']};
            }}
            """

            self.setStyleSheet(main_window_style)

            # UI 컴포넌트 개별 업데이트
            self.update_header_theme()
            self.update_input_area_theme()

            # 컨테이너 테마 업데이트
            self.update_container_themes()

            # 기존 채팅 메시지들에도 테마 적용
            self.update_existing_messages_theme()

            # 설정창이 열려있으면 테마 업데이트
            self.update_settings_window_theme()

            # Webhook 상태 업데이트 (현재 상태 유지하면서 테마만 변경)
            self.check_webhook_status()

            logger.info(f"테마 적용 완료: {self.theme_manager.get_current_theme().value}")
        except Exception as e:
            logger.error(f"테마 적용 실패: {e}")

    def update_header_theme(self) -> None:
        """헤더 컴포넌트의 테마를 업데이트합니다."""
        try:
            colors = self.theme_manager.get_theme_colors()

            # 헤더 프레임 찾기
            header_frame = self.findChild(QFrame, "header_frame")
            if header_frame:
                header_frame.setStyleSheet(
                    f"""
                    QFrame {{
                        background-color: {colors['header_background']};
                        border: none;
                        border-bottom: 1px solid {colors['border']};
                        padding: 0;
                    }}
                """
                )

            # 모든 QPushButton 찾아서 업데이트
            buttons = self.findChildren(QPushButton)
            for button in buttons:
                button_text = button.text()

                if "새 대화" in button_text:
                    # 새 대화 버튼
                    button.setStyleSheet(
                        f"""
                        QPushButton {{
                            background-color: {colors['success']};
                            color: white;
                            border: 2px solid {colors['success']};
                            border-radius: 20px;
                            font-size: 14px;
                            font-weight: 600;
                            font-family: '{self.ui_config['font_family']}';
                        }}
                        QPushButton:hover {{
                            background-color: {colors['success_hover']};
                            border-color: {colors['success_hover']};
                        }}
                        QPushButton:pressed {{
                            background-color: {colors['success_pressed']};
                            border-color: {colors['success_pressed']};
                        }}
                    """
                    )
                elif "설정" in button_text:
                    # 설정 버튼
                    button.setStyleSheet(
                        f"""
                        QPushButton {{
                            background-color: {colors['button_background']};
                            color: {colors['text']};
                            border: 2px solid {colors['button_border']};
                            border-radius: 20px;
                            font-size: 14px;
                            font-weight: 600;
                            font-family: '{self.ui_config['font_family']}';
                        }}
                        QPushButton:hover {{
                            background-color: {colors['button_hover']};
                            border-color: {colors['border']};
                        }}
                        QPushButton:pressed {{
                            background-color: {colors['button_pressed']};
                            border-color: {colors['border']};
                        }}
                    """
                    )

            # 모든 QLabel 업데이트
            labels = self.findChildren(QLabel)
            for label in labels:
                if "DS Pilot" in label.text():
                    # 타이틀 라벨
                    label.setStyleSheet(
                        f"""
                        QLabel {{
                            color: {colors['text']};
                            font-size: 20px;
                            font-weight: 700;
                            font-family: '{self.ui_config['font_family']}';
                            background-color: transparent;
                        }}
                    """
                    )
                else:
                    # 일반 라벨
                    label.setStyleSheet(
                        f"""
                        QLabel {{
                            color: {colors['text']};
                            background-color: transparent;
                        }}
                    """
                    )

            # 모델 선택 ComboBox 업데이트
            if hasattr(self, "model_selector") and self.model_selector:
                self.model_selector.setStyleSheet(
                    f"""
                    QComboBox {{
                        background-color: {colors['input_background']};
                        border: none;
                        color: {colors['text']};
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
                        background-color: {colors['background']};
                        border: 2px solid {colors['border']};
                        border-radius: 8px;
                        padding: 4px;
                        selection-background-color: {colors['primary']};
                        selection-color: white;
                        font-size: 14px;
                        font-family: '{self.ui_config['font_family']}';
                    }}
                    QComboBox QAbstractItemView::item {{
                        padding: 8px 12px;
                        border-radius: 4px;
                        margin: 2px;
                        color: {colors['text']};
                    }}
                    QComboBox QAbstractItemView::item:selected {{
                        background-color: {colors['primary']};
                        color: white;
                    }}
                """
                )

        except Exception as e:
            logger.error(f"헤더 테마 업데이트 실패: {e}")

    def update_input_area_theme(self) -> None:
        """입력 영역의 테마를 업데이트합니다."""
        try:
            colors = self.theme_manager.get_theme_colors()

            # 입력 텍스트 영역 업데이트
            if hasattr(self, "input_text") and self.input_text is not None:
                self.input_text.setStyleSheet(
                    f"""
                    QTextEdit {{
                        background-color: {colors['input_background']};
                        color: {colors['text']};
                        border: 1px solid {colors['border']};
                        border-radius: 24px;
                        padding: 8px 16px;
                        font-size: {self.ui_config['font_size']}px;
                        font-family: '{self.ui_config['font_family']}';
                    }}
                    QTextEdit:focus {{
                        border-color: {colors['primary']};
                    }}
                """
                )

            # 전송 버튼 업데이트
            if hasattr(self, "send_button") and self.send_button is not None:
                self.send_button.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {colors['primary']};
                        color: white;
                        border: none;
                        border-radius: 24px;
                        font-weight: 700;
                        font-size: {self.ui_config['font_size']}px;
                        font-family: '{self.ui_config['font_family']}';
                    }}
                    QPushButton:hover {{
                        background-color: {colors['primary_hover']};
                    }}
                    QPushButton:pressed {{
                        background-color: {colors['primary_pressed']};
                    }}
                    QPushButton:disabled {{
                        background-color: {colors['text_secondary']};
                        color: {colors['text']};
                    }}
                """
                )

            # 중단 버튼 업데이트
            if hasattr(self, "stop_button") and self.stop_button is not None:
                self.stop_button.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {colors['danger']};
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

        except Exception as e:
            logger.error(f"입력 영역 테마 업데이트 실패: {e}")

    def update_theme_toggle_button(self) -> None:
        """테마 토글 버튼 업데이트"""
        try:
            if hasattr(self, "theme_toggle_button") and self.theme_toggle_button:
                colors = self.theme_manager.get_theme_colors()
                current_theme = self.theme_manager.get_current_theme()

                # 테마에 따른 아이콘 선택
                icon = "🌙" if current_theme == ThemeMode.LIGHT else "☀️"
                self.theme_toggle_button.setText(icon)

                # 테마별 스타일 적용
                style = f"""
                    QPushButton {{
                        background-color: {colors['button_background']};
                        color: {colors['text']};
                        border: 2px solid {colors['button_border']};
                        border-radius: 20px;
                        padding: 8px 16px;
                        font-weight: 600;
                        font-size: 16px;
                        font-family: '{self.ui_config['font_family']}';
                    }}
                    QPushButton:hover {{
                        background-color: {colors['button_hover']};
                        border-color: {colors['border']};
                    }}
                    QPushButton:pressed {{
                        background-color: {colors['button_pressed']};
                        border-color: {colors['border']};
                    }}
                """
                self.theme_toggle_button.setStyleSheet(style)

                # 툴팁 업데이트
                tooltip = (
                    "라이트 모드로 전환" if current_theme == ThemeMode.DARK else "다크 모드로 전환"
                )
                self.theme_toggle_button.setToolTip(tooltip)

                logger.debug(f"테마 토글 버튼 업데이트 완료: {icon}")

        except Exception as e:
            logger.error(f"테마 토글 버튼 업데이트 실패: {e}")

    def update_existing_messages_theme(self) -> None:
        """기존 채팅 메시지들에 새 테마를 적용합니다."""
        try:
            if not hasattr(self, "message_manager") or not self.message_manager:
                return

            # MessageManager를 통해 모든 채팅 버블의 테마 업데이트
            if hasattr(self.message_manager, "update_all_message_styles"):
                # UI 설정도 테마에 맞게 업데이트
                self.ui_config = self.config_manager.get_ui_config()
                self.message_manager.ui_config = self.ui_config
                self.message_manager.update_all_message_styles()
                logger.debug("기존 메시지들에 테마 적용 완료")

            # 채팅 영역 강제 업데이트
            if hasattr(self, "chat_layout") and self.chat_layout:
                for i in range(self.chat_layout.count()):
                    item = self.chat_layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        # 위젯이 테마 업데이트를 지원하는 경우
                        if hasattr(widget, "apply_theme"):
                            try:
                                widget.apply_theme(self.theme_manager)
                            except Exception as e:
                                logger.debug(f"위젯 테마 적용 실패: {e}")

                        # 위젯 강제 업데이트
                        widget.update()
                        if hasattr(widget, "repaint"):
                            widget.repaint()

        except Exception as e:
            logger.error(f"기존 메시지 테마 업데이트 실패: {e}")

    def update_container_themes(self) -> None:
        """UI 컨테이너들의 테마를 업데이트합니다."""
        try:
            # UI 설정 매니저를 찾아서 컨테이너 테마 업데이트
            if hasattr(self, "_ui_setup_manager"):
                self._ui_setup_manager.update_container_themes()
            else:
                # UI 설정 매니저가 없으면 직접 업데이트
                from dspilot_app.ui.managers.ui_setup_manager import UISetupManager

                ui_manager = UISetupManager(self)
                ui_manager.update_container_themes()

        except Exception as e:
            logger.error(f"컨테이너 테마 업데이트 실패: {e}")

    def update_settings_window_theme(self) -> None:
        """설정창의 테마를 업데이트합니다."""
        try:
            # 설정창이 존재하고 표시 중인 경우 테마 업데이트
            if hasattr(self, "_settings_window") and self._settings_window is not None:
                if hasattr(self._settings_window, "update_theme"):
                    self._settings_window.update_theme()

        except Exception as e:
            logger.error(f"설정창 테마 업데이트 실패: {e}")
