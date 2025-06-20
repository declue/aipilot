import logging
import os
import signal
import sys
import webbrowser

from notifypy import Notify  # type: ignore
from PySide6.QtCore import QObject, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QStyle, QSystemTrayIcon

from application.api.fastapi_thread import FastAPIThread
from application.config.config_manager import ConfigManager
from application.ui.main_window import MainWindow
from application.ui.signals.tray_noficiation_signals import TrayNotificationSignals
from application.ui.test_window import TestWindow
from application.ui.tray_notification_dialog import TrayNotificationDialog
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("tray_app") or logging.getLogger("tray_app")


class TrayApp(QObject):
    def __init__(self, app, mcp_manager=None, mcp_tool_manager=None, app_instance=None):
        super().__init__()

        self.app = app
        self.mcp_manager = mcp_manager
        self.mcp_tool_manager = mcp_tool_manager
        self.app_instance = app_instance

        # 설정 관리자 초기화
        self.config_manager = ConfigManager()
        self.config_manager.load_config()

        # 시그널 초기화
        self.notification_signals = TrayNotificationSignals()
        self.notification_signals.api_notification.connect(self.handle_api_notification)

        # 트레이 아이콘 깜박임 관련 변수들
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.toggle_blink_icon)
        self.is_blinking = False
        self.blink_state = False  # True: 깜박임 상태, False: 일반 상태
        self.has_unread_messages = False
        self.normal_icon = None
        self.blink_icon = None

        # 시스템 트레이 아이콘 지원 확인
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.error("시스템 트레이를 사용할 수 없습니다.")
            return

        logger.debug(
            "시스템 트레이 지원 여부: %s", QSystemTrayIcon.isSystemTrayAvailable()
        )

        # 창 인스턴스 생성
        self.main_window = MainWindow(self.mcp_manager, self.mcp_tool_manager)

        # 메인 윈도우에 트레이 앱 참조 설정
        self.main_window.tray_app = self

        # 테스트 창 참조
        self.test_window = None

        # MainWindow 참조를 app_instance의 notification_signals에 설정
        if self.app_instance:
            self.app_instance.notification_signals.main_window = self.main_window

            # 기존 알림 시그널을 MainWindow와 연결 (트레이 알림용)
            self.app_instance.notification_signals.show_notification.connect(
                self.handle_notification_signal
            )

            # 새로운 알림 시그널들 연결
            self.app_instance.notification_signals.show_system_notification.connect(
                self.handle_system_notification
            )
            self.app_instance.notification_signals.show_dialog_notification.connect(
                self.handle_dialog_notification
            )

            # 메시지 관련 시그널들을 MainWindow 메서드에 연결
            self.app_instance.notification_signals.add_api_message.connect(
                self.main_window.add_api_message_to_chat
            )
            self.app_instance.notification_signals.add_user_message.connect(
                self.main_window.add_user_message_from_api
            )
            self.app_instance.notification_signals.trigger_llm_response.connect(
                self.main_window.trigger_llm_response_from_api
            )

            # 메시지 수신 시 트레이 아이콘 깜박임 처리
            self.app_instance.notification_signals.add_api_message.connect(
                self.on_message_received
            )
            self.app_instance.notification_signals.add_user_message.connect(
                self.on_message_received
            )
            self.app_instance.notification_signals.trigger_llm_response.connect(
                self.on_message_received
            )

            # UI 설정 관련 시그널 연결
            self.app_instance.notification_signals.update_ui_settings.connect(
                self.handle_ui_settings_update
            )

            # 채팅 관리 시그널들 연결
            self.app_instance.notification_signals.clear_chat.connect(
                self.main_window.start_new_conversation
            )
            self.app_instance.notification_signals.save_chat.connect(
                self.handle_save_chat
            )
            self.app_instance.notification_signals.load_chat.connect(
                self.handle_load_chat
            )

        # 트레이 아이콘 설정
        self.setup_tray_icon()

        # FastAPI 서버 시작
        self.start_fastapi_server()

        # 시그널 처리
        signal.signal(signal.SIGINT, self.handle_exit_signal)
        signal.signal(signal.SIGTERM, self.handle_exit_signal)

        # 주기적으로 Python 신호 처리
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: None)
        self.timer.start(100)

    def on_message_received(self, *_args):
        """메시지 수신 시 트레이 아이콘 깜박임 시작"""
        # 윈도우 상태 디버깅
        is_visible = self.main_window.isVisible()
        is_active = self.main_window.isActiveWindow()
        is_minimized = self.main_window.isMinimized()

        logger.debug(
            f"메시지 수신 - 윈도우 상태: visible={is_visible}, active={is_active}, minimized={is_minimized}"
        )
        print(
            f"[DEBUG] 메시지 수신 - 윈도우 상태: visible={is_visible}, active={is_active}, minimized={is_minimized}"
        )

        # 깜박임 시작 조건을 더 정확하게 체크
        should_blink = (
            not is_visible  # 윈도우가 숨겨져 있거나
            or not is_active  # 활성화되지 않았거나
            or is_minimized  # 최소화되어 있을 때
        )

        if should_blink:
            logger.debug("조건 만족 - 트레이 아이콘 깜박임 시작")
            print("[DEBUG] 조건 만족 - 트레이 아이콘 깜박임 시작")
            self.start_tray_blink()
        else:
            logger.debug("조건 불만족 - 깜박임 시작하지 않음")
            print("[DEBUG] 조건 불만족 - 깜박임 시작하지 않음")

    def start_tray_blink(self):
        """트레이 아이콘 깜박임 시작"""
        if not self.is_blinking:
            self.is_blinking = True
            self.has_unread_messages = True
            self.blink_state = False
            self.blink_timer.start(600)  # 600ms 간격으로 깜박임 (더 빠르게)
            # 툴크 업데이트
            if hasattr(self, "tray_icon"):
                self.tray_icon.setToolTip("DSPilot - AI 채팅 도구 (새 메시지 있음) 💬")

            # Windows 작업 표시줄 깜박임 추가
            self._flash_taskbar_icon()

            logger.debug("트레이 아이콘 깜박임 시작됨")

    def _flash_taskbar_icon(self):
        """Windows 작업 표시줄 아이콘 깜박임"""
        try:
            # Qt의 윈도우 alert 기능 사용
            if self.main_window and hasattr(self.main_window, "windowHandle"):
                window_handle = self.main_window.windowHandle()
                if window_handle:
                    window_handle.alert(5000)  # 5초간 깜박임
                    logger.debug("Qt 윈도우 alert 시작됨")

            # Windows API 직접 호출 (추가적인 효과)
            if sys.platform == "win32":
                try:
                    import ctypes
                    from ctypes import wintypes

                    # FlashWindow API 정의
                    user32 = ctypes.windll.user32

                    # 윈도우 핸들 얻기
                    hwnd = int(self.main_window.winId())

                    # FLASHWINFO 구조체
                    class FLASHWINFO(ctypes.Structure):
                        _fields_ = [
                            ("cbSize", wintypes.UINT),
                            ("hwnd", wintypes.HWND),
                            ("dwFlags", wintypes.DWORD),
                            ("uCount", wintypes.UINT),
                            ("dwTimeout", wintypes.DWORD),
                        ]

                    # 플래시 플래그
                    FLASHW_CAPTION = 0x00000001  # 캡션 표시줄 깜박임
                    FLASHW_TRAY = 0x00000002  # 작업 표시줄 버튼 깜박임
                    FLASHW_ALL = FLASHW_CAPTION | FLASHW_TRAY
                    FLASHW_TIMERNOFG = 0x0000000C  # 포그라운드가 아닐 때만

                    # FLASHWINFO 설정
                    flash_info = FLASHWINFO()
                    flash_info.cbSize = ctypes.sizeof(FLASHWINFO)
                    flash_info.hwnd = hwnd
                    flash_info.dwFlags = FLASHW_ALL | FLASHW_TIMERNOFG
                    flash_info.uCount = 10  # 10번 깜박임
                    flash_info.dwTimeout = 0  # 시스템 기본값 사용

                    # FlashWindowEx 호출
                    user32.FlashWindowEx(ctypes.byref(flash_info))
                    logger.debug("Windows API FlashWindowEx 호출됨")

                except Exception as win_api_error:
                    logger.warning("Windows API 깜박임 실패: %s", win_api_error)

        except Exception as e:
            logger.warning("작업 표시줄 깜박임 실패: %s", e)

    def stop_tray_blink(self):
        """트레이 아이콘 깜박임 중지"""
        if self.is_blinking:
            self.is_blinking = False
            self.has_unread_messages = False
            self.blink_timer.stop()
            # 정상 아이콘으로 복원
            if self.normal_icon and hasattr(self, "tray_icon"):
                self.tray_icon.setIcon(self.normal_icon)
                # 툴크도 원래대로 복원
                self.tray_icon.setToolTip("DSPilot - AI 채팅 도구")

            # Windows 작업 표시줄 깜박임 중지
            self._stop_taskbar_flash()

            logger.debug("트레이 아이콘 깜박임 중지됨")

    def _stop_taskbar_flash(self):
        """Windows 작업 표시줄 깜박임 중지"""
        try:
            import sys

            if sys.platform == "win32":
                try:
                    import ctypes
                    from ctypes import wintypes

                    # FlashWindow API 정의
                    user32 = ctypes.windll.user32

                    # 윈도우 핸들 얻기
                    hwnd = int(self.main_window.winId())

                    # FLASHWINFO 구조체
                    class FLASHWINFO(ctypes.Structure):
                        _fields_ = [
                            ("cbSize", wintypes.UINT),
                            ("hwnd", wintypes.HWND),
                            ("dwFlags", wintypes.DWORD),
                            ("uCount", wintypes.UINT),
                            ("dwTimeout", wintypes.DWORD),
                        ]

                    # 깜박임 중지 플래그
                    FLASHW_STOP = 0

                    # FLASHWINFO 설정
                    flash_info = FLASHWINFO()
                    flash_info.cbSize = ctypes.sizeof(FLASHWINFO)
                    flash_info.hwnd = hwnd
                    flash_info.dwFlags = FLASHW_STOP
                    flash_info.uCount = 0
                    flash_info.dwTimeout = 0

                    # FlashWindowEx 호출하여 깜박임 중지
                    user32.FlashWindowEx(ctypes.byref(flash_info))
                    logger.debug("Windows API 깜박임 중지됨")

                except Exception as win_api_error:
                    logger.warning("Windows API 깜박임 중지 실패: %s", win_api_error)

        except Exception as e:
            logger.warning("작업 표시줄 깜박임 중지 실패: %s", e)

    def toggle_blink_icon(self):
        """트레이 아이콘 깜박임 토글"""
        if not hasattr(self, "tray_icon") or not self.tray_icon:
            return

        self.blink_state = not self.blink_state

        if self.blink_state:
            # 깜박임 상태 - 알림 아이콘 표시
            if self.blink_icon:
                self.tray_icon.setIcon(self.blink_icon)
        else:
            # 일반 상태 - 기본 아이콘 표시
            if self.normal_icon:
                self.tray_icon.setIcon(self.normal_icon)

    def on_window_activated(self):
        """윈도우가 활성화되었을 때 호출 (메인 윈도우에서 호출)"""
        if self.has_unread_messages:
            logger.debug("윈도우 활성화 - 트레이 깜박임 중지")
            self.stop_tray_blink()

    def handle_api_notification(self, notification_type, title):
        """API로부터 받은 알림 처리"""
        logger.debug("API 알림 수신: %s - %s", notification_type, title)

        # 시스템 트레이 알림 표시
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "AI 어시스턴트 알림",
                f"{notification_type}: {title}",
                QSystemTrayIcon.Information,
                3000,  # 3초간 표시
            )

    def handle_notification_signal(self, notification_type, title, message, duration):
        """show_notification 시그널 처리 (크로스 플랫폼 알림 표시)"""
        logger.debug(
            "🔔 알림 시그널 수신: %s - %s - %s", notification_type, title, message
        )
        print(f"[DEBUG] 🔔 알림 시그널 수신: {notification_type} - {title} - {message}")

        # 윈도우 상태 디버깅
        is_visible = self.main_window.isVisible()
        is_active = self.main_window.isActiveWindow()
        is_minimized = self.main_window.isMinimized()

        logger.debug(
            f"알림 수신 - 윈도우 상태: visible={is_visible}, active={is_active}, minimized={is_minimized}"
        )
        print(
            f"[DEBUG] 알림 수신 - 윈도우 상태: visible={is_visible}, active={is_active}, minimized={is_minimized}"
        )

        # 깜박임 시작 조건을 더 정확하게 체크
        should_blink = (
            not is_visible  # 윈도우가 숨겨져 있거나
            or not is_active  # 활성화되지 않았거나
            or is_minimized  # 최소화되어 있을 때
        )

        if should_blink:
            logger.debug("알림 조건 만족 - 트레이 아이콘 깜박임 시작")
            print("[DEBUG] 알림 조건 만족 - 트레이 아이콘 깜박임 시작")
            self.start_tray_blink()
        else:
            logger.debug("알림 조건 불만족 - 깜박임 시작하지 않음")
            print("[DEBUG] 알림 조건 불만족 - 깜박임 시작하지 않음")

        # macOS에서는 notifypy를 우선 사용 (더 안정적)
        try:

            system_notification = Notify()
            system_notification.title = title
            system_notification.message = message
            system_notification.send()
            logger.debug("✅ 시스템 알림 표시됨 (notifypy)")
            print(f"[DEBUG] ✅ 시스템 알림 표시됨: {title}")
            return  # 성공하면 트레이 알림은 생략
        except Exception as e:
            logger.warning("시스템 알림 실패, 트레이 알림으로 대체: %s", e)
            print(f"[DEBUG] ⚠️ 시스템 알림 실패: {e}")

        # 시스템 알림 실패 시 트레이 알림 시도
        if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.Information,
                duration if duration > 0 else 3000,
            )
            logger.debug("✅ 트레이 알림 표시됨")
            print(f"[DEBUG] ✅ 트레이 알림 표시됨: {title}")
        else:
            logger.warning("❌ 모든 알림 방법 실패")
            print(
                f"[DEBUG] ❌ 트레이 아이콘 상태 - hasattr: {hasattr(self, 'tray_icon')}, isVisible: {self.tray_icon.isVisible() if hasattr(self, 'tray_icon') else 'N/A'}"
            )

            # 최후의 수단: 커스텀 다이얼로그
            try:
                if hasattr(self, "main_window"):
                    notification_dialog = TrayNotificationDialog(
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        width=350,
                        height=120,
                        parent=self.main_window,
                    )
                    notification_dialog.show_notification()
                    print(f"[DEBUG] 🔄 커스텀 다이얼로그 표시됨: {title}")
            except Exception as dialog_error:
                print(f"[DEBUG] ❌ 커스텀 다이얼로그도 실패: {dialog_error}")

    def handle_system_notification(self, title, message, icon_path):
        """시스템 알림 처리 (notifypy 사용)"""
        logger.debug("🖥️ 시스템 알림 요청: %s - %s", title, message)
        print(f"[DEBUG] 🖥️ 시스템 알림 요청: {title} - {message}")

        # 윈도우 상태 디버깅
        is_visible = self.main_window.isVisible()
        is_active = self.main_window.isActiveWindow()
        is_minimized = self.main_window.isMinimized()

        logger.debug(
            f"시스템 알림 - 윈도우 상태: visible={is_visible}, active={is_active}, minimized={is_minimized}"
        )
        print(
            f"[DEBUG] 시스템 알림 - 윈도우 상태: visible={is_visible}, active={is_active}, minimized={is_minimized}"
        )

        # 깜박임 시작 조건을 더 정확하게 체크
        should_blink = (
            not is_visible  # 윈도우가 숨겨져 있거나
            or not is_active  # 활성화되지 않았거나
            or is_minimized  # 최소화되어 있을 때
        )

        if should_blink:
            logger.debug("시스템 알림 조건 만족 - 트레이 아이콘 깜박임 시작")
            print("[DEBUG] 시스템 알림 조건 만족 - 트레이 아이콘 깜박임 시작")
            self.start_tray_blink()
        else:
            logger.debug("시스템 알림 조건 불만족 - 깜박임 시작하지 않음")
            print("[DEBUG] 시스템 알림 조건 불만족 - 깜박임 시작하지 않음")

        try:
            system_notification = Notify()
            system_notification.title = title
            system_notification.message = message

            # 아이콘 설정 (있는 경우)
            if icon_path and os.path.exists(icon_path):
                system_notification.icon = icon_path

            system_notification.send()
            logger.debug("✅ 시스템 알림 표시됨 (notifypy)")
            print(f"[DEBUG] ✅ 시스템 알림 표시됨: {title}")

        except Exception as e:
            logger.error("❌ 시스템 알림 실패: %s", e)
            print(f"[DEBUG] ❌ 시스템 알림 실패: {e}")

            # 실패 시 트레이 알림으로 대체
            if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    title,
                    message,
                    QSystemTrayIcon.Information,
                    3000,
                )
                print(f"[DEBUG] 🔄 트레이 알림으로 대체됨: {title}")

    def handle_dialog_notification(self, dialog_data):
        """다이얼로그 알림 처리 (TrayNotificationDialog 사용)"""
        logger.debug("🗨️ 다이얼로그 알림 요청: %s", dialog_data.get("title", "Unknown"))

        # 윈도우 상태 디버깅
        is_visible = self.main_window.isVisible()
        is_active = self.main_window.isActiveWindow()
        is_minimized = self.main_window.isMinimized()

        logger.debug(
            f"다이얼로그 알림 - 윈도우 상태: visible={is_visible}, active={is_active}, minimized={is_minimized}"
        )
        print(
            f"[DEBUG] 다이얼로그 알림 - 윈도우 상태: visible={is_visible}, active={is_active}, minimized={is_minimized}"
        )

        # 깜박임 시작 조건을 더 정확하게 체크
        should_blink = (
            not is_visible  # 윈도우가 숨겨져 있거나
            or not is_active  # 활성화되지 않았거나
            or is_minimized  # 최소화되어 있을 때
        )

        if should_blink:
            logger.debug("다이얼로그 알림 조건 만족 - 트레이 아이콘 깜박임 시작")
            print("[DEBUG] 다이얼로그 알림 조건 만족 - 트레이 아이콘 깜박임 시작")
            self.start_tray_blink()
        else:
            logger.debug("다이얼로그 알림 조건 불만족 - 깜박임 시작하지 않음")
            print("[DEBUG] 다이얼로그 알림 조건 불만족 - 깜박임 시작하지 않음")

        try:

            notification_dialog = TrayNotificationDialog(
                title=dialog_data.get("title", "알림"),
                message=dialog_data.get("message", ""),
                html_message=dialog_data.get("html_message"),
                notification_type=dialog_data.get("notification_type", "info"),
                width=dialog_data.get("width", 350),
                height=dialog_data.get("height", 150),
                parent=self.main_window,
            )
            notification_dialog.show_notification()
            logger.debug("✅ 다이얼로그 알림 표시됨")
            print(f"[DEBUG] ✅ 다이얼로그 알림 표시됨: {dialog_data.get('title')}")

        except Exception as e:
            logger.error("❌ 다이얼로그 알림 실패: %s", e)
            print(f"[DEBUG] ❌ 다이얼로그 알림 실패: {e}")

    def handle_ui_settings_update(self, settings_dict):
        """UI 설정 업데이트 처리"""
        logger.debug("⚙️ UI 설정 업데이트: %s", settings_dict)
        print(f"[DEBUG] ⚙️ UI 설정 업데이트: {settings_dict}")

        try:
            # 설정 업데이트
            for key, value in settings_dict.items():
                self.config_manager.set_config_value("UI", key, value)

            self.config_manager.save_config()

            # 메인 윈도우에 설정 변경 알림
            if hasattr(self, "main_window"):
                self.main_window.on_settings_changed()

            logger.debug("✅ UI 설정 업데이트 완료")
            print("[DEBUG] ✅ UI 설정 업데이트 완료")

        except Exception as e:
            logger.error("❌ UI 설정 업데이트 실패: %s", e)
            print(f"[DEBUG] ❌ UI 설정 업데이트 실패: {e}")

    def handle_save_chat(self, file_path):
        """채팅 저장 처리"""
        logger.debug("💾 채팅 저장 요청: %s", file_path)
        print(f"[DEBUG] 💾 채팅 저장 요청: {file_path}")

        try:
            # 현재는 로그만 출력
            logger.info("채팅 저장 기능 구현 필요: %s", file_path)
            print(f"[DEBUG] ℹ️ 채팅 저장 기능 구현 필요: {file_path}")

        except Exception as e:
            logger.error("❌ 채팅 저장 실패: %s", e)
            print(f"[DEBUG] ❌ 채팅 저장 실패: {e}")

    def handle_load_chat(self, file_path):
        """채팅 불러오기 처리"""
        logger.debug("📂 채팅 불러오기 요청: %s", file_path)
        print(f"[DEBUG] 📂 채팅 불러오기 요청: {file_path}")

        try:
            # 현재는 로그만 출력
            logger.info("채팅 불러오기 기능 구현 필요: %s", file_path)
            print(f"[DEBUG] ℹ️ 채팅 불러오기 기능 구현 필요: {file_path}")

        except Exception as e:
            logger.error("❌ 채팅 불러오기 실패: %s", e)
            print(f"[DEBUG] ❌ 채팅 불러오기 실패: {e}")

    def start_fastapi_server(self):
        """FastAPI 서버를 별도 스레드에서 시작"""
        if self.app_instance:
            self.config_manager.load_config()
            host = self.config_manager.get_config_value("API", "host", "127.0.0.1")
            port = self.config_manager.get_config_value("API", "port", 8000)
            logger.info("FastAPI 서버 시작(trayapp): http://%s:%s", host, port)
            self.fastapi_thread = FastAPIThread(
                self.app_instance.api_app, host, int(port)
            )

            # 서버가 알림 보낼 때 트레이 알림 시그널과 연결
            # 여기에 알림 시스템이 있다면 연결

            self.fastapi_thread.start()
        else:
            logger.warning("app_instance가 없어서 FastAPI 서버를 시작할 수 없습니다.")

    def create_test_window_action(self):
        """테스트 윈도우 열기 액션 생성"""

        def open_test_window():
            self.test_window = TestWindow()
            self.test_window.show()
            logger.debug("테스트 윈도우 열기")

        test_action = QAction("API 테스트", self)
        test_action.triggered.connect(open_test_window)
        return test_action

    def create_docs_action(self):
        """API 문서 열기 액션"""

        def open_docs():
            self.config_manager.load_config()
            host = self.config_manager.get_config_value("API", "host", "127.0.0.1")
            port = self.config_manager.get_config_value("API", "port", 8000)
            webbrowser.open(f"http://{host}:{port}/docs")
            logger.debug("FastAPI 서버가 별도 스레드에서 시작되었습니다")
            logger.info("API 테스트 URL: http://%s:%s/docs", host, port)

        docs_action = QAction("API 문서", self)
        docs_action.triggered.connect(open_docs)
        return docs_action

    def create_icon_with_fallback(self):
        """아이콘 생성 (fallback 포함)"""
        icon = QIcon()

        try:
            # logo.png 아이콘 시도 (루트 디렉토리)
            logo_path = "logo.png"
            if os.path.exists(logo_path):
                icon = QIcon(logo_path)
                if not icon.isNull():
                    # 다양한 크기의 아이콘 추가 (Windows 작업 표시줄 및 트레이 대응)
                    icon.addFile(logo_path, QSize(16, 16))
                    icon.addFile(logo_path, QSize(24, 24))
                    icon.addFile(logo_path, QSize(32, 32))
                    icon.addFile(logo_path, QSize(48, 48))
                    icon.addFile(logo_path, QSize(64, 64))
                    icon.addFile(logo_path, QSize(128, 128))
                    icon.addFile(logo_path, QSize(256, 256))

                    logger.debug("logo.png 트레이 아이콘 생성 성공 (다중 크기)")
                    return icon

            # 커스텀 아이콘 시도
            icon_path = "resources/icon.png"
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                if not icon.isNull():
                    logger.debug("트레이 아이콘 생성 시작")
                    return icon

            # SVG 아이콘 시도
            svg_path = "resources/icon.svg"
            if os.path.exists(svg_path):
                icon = QIcon(svg_path)
                if not icon.isNull():
                    logger.debug("커스텀 아이콘 생성 성공")
                    return icon
        except Exception as exception:
            logger.warning("커스텀 아이콘 생성 실패: %s", exception)

        # 시스템 기본 아이콘들 시도 (PySide6에서 사용 가능한 것들)
        try:

            system_icon_types = [
                QStyle.StandardPixmap.SP_MessageBoxInformation,
                QStyle.StandardPixmap.SP_DialogApplyButton,
                QStyle.StandardPixmap.SP_FileDialogStart,
                QStyle.StandardPixmap.SP_DirIcon,
                QStyle.StandardPixmap.SP_FileIcon,
                QStyle.StandardPixmap.SP_DesktopIcon,
            ]

            for icon_type in system_icon_types:
                try:
                    system_icon = self.app.style().standardIcon(icon_type)
                    if not system_icon.isNull():
                        logger.debug("시스템 아이콘 사용: %s", icon_type)
                        return system_icon
                except Exception:
                    continue

        except Exception as exception:
            logger.warning("시스템 아이콘 실패: %s", exception)

        # 최후의 대체 방법 - 텍스트 기반 아이콘
        try:

            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.blue)

            painter = QPainter(pixmap)
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial", 8, QFont.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "D")
            painter.end()

            icon = QIcon(pixmap)
            logger.debug("텍스트 기반 아이콘 생성 성공")
            return icon

        except Exception as exception:
            logger.error("모든 아이콘 생성 실패: %s", exception)
            return QIcon()  # 빈 아이콘 반환

    def create_blink_icon(self):
        """깜박임용 알림 아이콘 생성 (빨간색 표시)"""
        try:
            # 기본 아이콘 크기를 더 크게
            size = 24
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            # 빨간색 원 그리기 (알림 표시) - 더 큰 크기
            painter.setBrush(Qt.red)
            painter.setPen(Qt.darkRed)
            painter.drawEllipse(2, 2, size - 4, size - 4)

            # 가운데에 알림 표시 (느낌표) - 더 큰 폰트
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "!")

            painter.end()

            icon = QIcon(pixmap)
            # 다양한 크기 추가
            icon.addPixmap(pixmap, QIcon.Normal)
            icon.addPixmap(pixmap, QIcon.Selected)

            logger.debug("깜박임용 알림 아이콘 생성 성공 (개선된 크기)")
            return icon

        except Exception as exception:
            logger.warning("깜박임용 아이콘 생성 실패, 기본 아이콘 사용: %s", exception)
            # 실패시 기본 아이콘 반환
            return self.normal_icon if self.normal_icon else QIcon()

    def setup_tray_icon(self):
        """시스템 트레이 아이콘 설정"""
        # 아이콘 생성
        icon = self.create_icon_with_fallback()

        # 정상 아이콘과 깜박임용 아이콘 저장
        self.normal_icon = icon
        self.blink_icon = self.create_blink_icon()

        # 트레이 아이콘 생성
        self.tray_icon = QSystemTrayIcon(icon, self)

        # 컨텍스트 메뉴 생성
        tray_menu = QMenu()

        # 메뉴 아이템들
        show_action = QAction("채팅 창 보기", self)
        show_action.triggered.connect(self.show_main_window)

        test_action = self.create_test_window_action()
        docs_action = self.create_docs_action()

        quit_action = QAction("종료", self)
        quit_action.triggered.connect(self.quit_application)

        # 메뉴에 아이템 추가
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(test_action)
        tray_menu.addAction(docs_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        # 메뉴 설정
        self.tray_icon.setContextMenu(tray_menu)

        # 시그널 연결
        self.tray_icon.activated.connect(self.tray_icon_activated)

        # 트레이 아이콘 표시
        self.show_tray_icon()

    def show_tray_icon(self):
        """트레이 아이콘 표시"""
        try:
            logger.debug("트레이 아이콘 표시 시도")
            self.tray_icon.show()

            # 툴크 설정
            self.tray_icon.setToolTip("DSPilot - AI 채팅 도구")

            # 트레이 아이콘이 제대로 표시되었는지 확인
            QTimer.singleShot(1000, self.check_tray_visibility)

        except Exception as exception:
            logger.error("트레이 아이콘 표시 실패: %s", exception)
            # 대안: 윈도우를 바로 표시
            self.show_main_window()

    def check_tray_visibility(self):
        """트레이 아이콘 가시성 확인"""
        try:
            is_visible = self.tray_icon.isVisible()
            logger.debug("트레이 아이콘 표시 완료")

            if not is_visible:
                # 트레이 아이콘이 보이지 않으면 다시 시도하거나 창을 표시
                QTimer.singleShot(2000, self.retry_tray_icon)

        except Exception as exception:
            logger.error("트레이 아이콘 표시 실패: %s", exception)
            self.show_main_window()

    def check_tray_icon_visibility(self):
        """트레이 아이콘 가시성 체크"""
        is_visible = self.tray_icon.isVisible()
        logger.debug("트레이 아이콘 가시성: %s", is_visible)

        if not is_visible:
            # 트레이 아이콘이 표시되지 않았다면 메인 창을 표시
            self.show_main_window()

    def retry_tray_icon(self):
        """트레이 아이콘 재시도"""
        try:
            if not self.tray_icon.isVisible():
                self.tray_icon.hide()
                self.tray_icon.show()
                logger.debug("트레이 아이콘 재시도")
        except Exception:
            # 트레이 아이콘 재시도 실패 시 메인 창 표시
            self.show_main_window()

    def tray_icon_activated(self, reason):
        """트레이 아이콘 클릭 이벤트"""
        logger.debug("트레이 아이콘 클릭: %s", reason)

        if reason == QSystemTrayIcon.DoubleClick:
            logger.debug("더블클릭 -> 창 토글")
            self.toggle_main_window()
        elif reason == QSystemTrayIcon.Trigger:
            # 단일 클릭도 창 토글로 처리 (사용자 편의성)
            logger.debug("단일클릭 -> 창 토글")
            self.toggle_main_window()

    def toggle_main_window(self):
        """메인 창 토글"""
        if self.main_window.isVisible():
            logger.debug("창 숨기기")
            self.main_window.hide()
        else:
            logger.debug("창 보이기")
            self.show_main_window()

    def show_main_window(self):
        """메인 창 표시"""
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

        # 트레이 깜박임 중지 (창이 표시되므로)
        self.on_window_activated()

        # 윈도우가 완전히 표시된 후 최신 알림으로 스크롤
        QTimer.singleShot(200, self.main_window.force_scroll_to_bottom)

    def handle_exit_signal(self, _signum, _frame):
        """시그널 핸들러"""
        self.app.quit()

    def quit_application(self):
        """애플리케이션 종료"""
        logger.debug("애플리케이션 종료")

        # FastAPI 서버 종료
        if hasattr(self, "fastapi_thread") and self.fastapi_thread:
            logger.debug("FastAPI 서버 종료 중...")
            try:
                self.fastapi_thread.stop_server()
                self.fastapi_thread.quit()
                # 최대 3초간 대기
                if not self.fastapi_thread.wait(3000):
                    logger.warning(
                        "FastAPI 스레드가 정상 종료되지 않아 강제 종료합니다."
                    )
                    self.fastapi_thread.terminate()
            except Exception as exception:
                logger.error("FastAPI 서버 종료 중 오류: %s", exception)

        # 트레이 아이콘 숨김
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()

        # 애플리케이션 종료
        self.app.quit()
