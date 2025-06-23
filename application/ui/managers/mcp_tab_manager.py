import os

from PySide6.QtCore import QObject, QTimer, Signal

from application.ui.managers.mcp_data_manager import MCPDataManager
from application.ui.managers.mcp_log_manager import MCPLogManager
from application.ui.managers.mcp_server_status_manager import MCPServerStatusManager
from application.ui.managers.mcp_tools_manager import MCPToolsManager
from application.ui.managers.mcp_ui_builder import MCPUIBuilder


class MCPSignals(QObject):
    """MCP 관련 시그널"""

    status_updated = Signal()


class MCPTabManager:
    """MCP 탭 관리 클래스 - 리팩토링된 버전 (SOLID 원칙 준수)

    각 클래스는 단일 책임을 가집니다:
    - MCPTabManager: 전체 조율 및 생명주기 관리
    - MCPUIBuilder: UI 생성 및 레이아웃
    - MCPDataManager: 데이터 로딩 및 캐싱
    - MCPServerStatusManager: 서버 상태 표시
    - MCPToolsManager: 도구 정보 표시
    - MCPLogManager: 로그 관리
    """

    def __init__(self, parent, mcp_manager, mcp_tool_manager):
        self.parent = parent
        self.mcp_manager = mcp_manager
        self.mcp_tool_manager = mcp_tool_manager
        self.signals = MCPSignals()

        # 서브 매니저들 (의존성 주입)
        self.ui_builder = MCPUIBuilder()
        self.data_manager = MCPDataManager(mcp_manager, mcp_tool_manager)

        # UI 컴포넌트들 (초기화 후 설정됨)
        self.ui_components = None
        self.log_manager = None
        self.server_status_manager = None
        self.tools_manager = None

        # 타이머 (자동 새로고침용)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)

    def create_mcp_tab(self):
        """MCP 설정 탭 생성 - 새로운 아키텍처"""

        # UI 생성
        self.ui_components = self.ui_builder.create_main_tab()

        # 서브 매니저들 초기화
        self._initialize_managers()

        # 이벤트 연결
        self._connect_events()

        # MCP 설정 파일 확인 및 생성
        self._create_initial_mcp_config_if_needed()

        # 초기 데이터 로드 (2초 후 시작)
        QTimer.singleShot(2000, self.refresh_data)

        # 자동 새로고침 시작 (30초마다) - 다소 지연시켜 시작
        QTimer.singleShot(10000, lambda: self.refresh_timer.start(30000))

        return self.ui_components["tab"]

    def _initialize_managers(self):
        """서브 매니저들 초기화"""
        # 로그 매니저
        self.log_manager = MCPLogManager(self.ui_components["logs_text"])

        # 서버 상태 매니저
        self.server_status_manager = MCPServerStatusManager(
            self.ui_components["server_status_tree"],
            self.ui_components["tool_details_text"],
            self.log_manager,
        )

        # 도구 매니저
        self.tools_manager = MCPToolsManager(
            self.ui_components["tools_tree"],
            self.ui_components["tool_details_text"],
            self.log_manager,
        )

    def _connect_events(self):
        """이벤트 연결"""
        # 새로고침 버튼
        self.ui_components["refresh_button"].clicked.connect(self.refresh_data)

    def _create_initial_mcp_config_if_needed(self):
        """필요한 경우 초기 MCP 설정 생성"""
        try:
            config_file = "mcp.json"

            if not os.path.exists(config_file):
                self.log_manager.log_initial_config_creation()

                # 기본 설정 생성
                self.mcp_manager.config_manager.create_default_config()

                # 설정 파일 위치 안내
                current_dir = os.getcwd()
                self.log_manager.log_config_file_location(os.path.join(current_dir, config_file))
            else:
                self.log_manager.log_config_found(config_file)

        except Exception as e:
            self.log_manager.add_log(f"❌ MCP 설정 초기화 실패: {str(e)}")

    def refresh_data(self):
        """데이터 새로고침 - 새로운 아키텍처"""
        # 이미 로딩 중이면 무시
        if self.data_manager.is_loading():
            return

        # UI 상태 업데이트
        self._update_ui_loading_state(True)

        # 로그
        self.log_manager.log_data_refresh_start()

        # 데이터 로드 시작
        self.data_manager.refresh_data(
            on_success=self._on_data_loaded, on_error=self._on_data_error
        )

    def _update_ui_loading_state(self, loading):
        """UI 로딩 상태 업데이트"""
        if loading:
            self.ui_components["status_label"].setText("데이터 로드 중...")
            self.ui_components["status_label"].setStyleSheet(
                """
                QLabel {
                    color: #d97706;
                    font-weight: 500;
                    padding: 4px 8px;
                    background-color: #fef3c7;
                    border-radius: 4px;
                }
            """
            )
            self.ui_components["progress_bar"].setVisible(True)
            self.ui_components["progress_bar"].setRange(0, 0)  # 무한 진행률
            self.ui_components["refresh_button"].setEnabled(False)
        else:
            self.ui_components["progress_bar"].setVisible(False)
            self.ui_components["refresh_button"].setEnabled(True)

    def _on_data_loaded(self, server_data, tools_data):
        """데이터 로드 완료 시 호출"""
        try:
            # 데이터 매니저에 캐시 업데이트
            self.data_manager.update_cache(server_data, tools_data)

            # UI 업데이트
            self.server_status_manager.update_server_status(server_data)
            self.tools_manager.update_tools(tools_data)

            # 로그 업데이트
            self.log_manager.log_data_refresh_success(len(server_data), len(tools_data))

            # 안내 메시지
            enabled_count = sum(1 for data in server_data.values() if data["config"].enabled)
            self.log_manager.log_guidance_messages(len(server_data), len(tools_data), enabled_count)

            # 상태 업데이트
            self.ui_components["status_label"].setText(
                f"서버 {len(server_data)}개, 도구 {len(tools_data)}개"
            )
            self.ui_components["status_label"].setStyleSheet(
                """
                QLabel {
                    color: #059669;
                    font-weight: 500;
                    padding: 4px 8px;
                    background-color: #d1fae5;
                    border-radius: 4px;
                }
            """
            )

        except Exception as e:
            self._on_data_error(str(e))

        finally:
            # UI 상태 복원
            self._update_ui_loading_state(False)

    def _on_data_error(self, error_message):
        """데이터 로드 오류 시 호출"""
        self.log_manager.log_data_refresh_error(error_message)
        self.ui_components["status_label"].setText(f"오류: {error_message}")
        self.ui_components["status_label"].setStyleSheet(
            """
            QLabel {
                color: #dc2626;
                font-weight: 500;
                padding: 4px 8px;
                background-color: #fecaca;
                border-radius: 4px;
            }
        """
        )

        # UI 상태 복원
        self._update_ui_loading_state(False)

    def cleanup(self):
        """리소스 정리"""
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()

        # 데이터 매니저 정리
        if self.data_manager:
            self.data_manager.cleanup()

    # Backward compatibility - 기존 API 유지
    def get_server_data(self):
        """서버 데이터 반환 (기존 호환성)"""
        return self.data_manager.get_server_data() if self.data_manager else {}

    def get_tools_data(self):
        """도구 데이터 반환 (기존 호환성)"""
        return self.data_manager.get_tools_data() if self.data_manager else []

    def update_theme(self):
        """테마 업데이트"""
        try:
            if hasattr(self.parent, "theme_manager"):
                colors = self.parent.theme_manager.get_theme_colors()

                # UI 컴포넌트들이 있으면 테마 적용
                if self.ui_components:
                    self._update_status_labels_theme(colors)
                    self._update_ui_builder_theme(colors)

        except Exception as e:
            print(f"MCP 탭 테마 업데이트 실패: {e}")

    def _update_status_labels_theme(self, _colors):
        """상태 라벨 테마 업데이트"""
        if self.ui_components and "status_label" in self.ui_components:
            # 기본 상태 라벨 스타일은 그대로 두고, 배경만 테마에 맞게 조정
            pass

    def _update_ui_builder_theme(self, colors):
        """UI 빌더 컴포넌트 테마 업데이트"""
        # UI 빌더에 테마 업데이트 메서드가 있으면 호출
        if hasattr(self.ui_builder, "update_theme"):
            self.ui_builder.update_theme(colors)
