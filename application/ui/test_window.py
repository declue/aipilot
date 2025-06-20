import socket
import sys
import traceback

import requests
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QLabel, QMainWindow, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)

from application.config.config_manager import ConfigManager


class TestWindow(QMainWindow):
    """기능 테스트 전용 창"""

    def __init__(self):
        super().__init__()
        self.tray_app = None  # TrayApp 참조 저장용
        self.config_manager = ConfigManager()
        self.config_manager.load_config()
        self.host = self.config_manager.get_config_value("API", "host", "127.0.0.1")
        self.port = self.config_manager.get_config_value("API", "port", 8000)

        # 포트가 문자열로 올 수 있으므로 정수로 변환
        try:
            self.port = int(self.port)
        except (ValueError, TypeError):
            self.port = 8000

        print(f"[DEBUG] TestWindow API 설정 - Host: {self.host}, Port: {self.port}")
        print(f"[DEBUG] 운영체제: {sys.platform}")

        self.setWindowTitle("메신저 기능 테스트")
        self.resize(500, 500)

        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 제목
        title_label = QLabel("🧪 메신저 기능 테스트")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; margin: 10px; color: #2C3E50;"
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 운영체제 정보 표시
        os_label = QLabel(f"운영체제: {sys.platform}")
        os_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(os_label)

        # 상태 표시 라벨들
        self.status_btn = QPushButton("트레이 상태: 확인 중...")
        self.status_btn.setEnabled(False)
        layout.addWidget(self.status_btn)

        self.api_status_btn = QPushButton("API 서버 상태: 확인 중...")
        self.api_status_btn.setEnabled(False)
        layout.addWidget(self.api_status_btn)

        # 상태 확인 버튼
        btn_check_api = QPushButton("API 서버 상태 다시 확인")
        btn_check_api.clicked.connect(self.check_api_server_status)
        layout.addWidget(btn_check_api)

        # 구분선
        separator = QLabel("=" * 40)
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(separator)

        # 시스템 알림 테스트
        notification_label = QLabel("시스템 알림 테스트:")
        notification_label.setStyleSheet(
            "font-weight: bold; margin-top: 10px; color: #2196F3;"
        )
        layout.addWidget(notification_label)

        btn_direct_notify = QPushButton("💬 기본 시스템 알림")
        btn_direct_notify.clicked.connect(lambda: self.test_notification_api("info"))
        layout.addWidget(btn_direct_notify)

        btn_warning_notify = QPushButton("⚠️ 경고 알림")
        btn_warning_notify.clicked.connect(
            lambda: self.test_notification_api("warning")
        )
        layout.addWidget(btn_warning_notify)

        btn_error_notify = QPushButton("❌ 오류 알림")
        btn_error_notify.clicked.connect(lambda: self.test_notification_api("error"))
        layout.addWidget(btn_error_notify)

        # 커스텀 다이얼로그 테스트
        dialog_label = QLabel("커스텀 다이얼로그 테스트:")
        dialog_label.setStyleSheet(
            "font-weight: bold; margin-top: 10px; color: #FF6B6B;"
        )
        layout.addWidget(dialog_label)

        btn_dialog_test = QPushButton("💬 커스텀 다이얼로그")
        btn_dialog_test.clicked.connect(lambda: self.test_dialog_api("info"))
        layout.addWidget(btn_dialog_test)

        # HTML 테스트 버튼들
        html_label = QLabel("HTML 스타일 다이얼로그 테스트:")
        html_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #10B981;")
        layout.addWidget(html_label)

        btn_html_test = QPushButton("🎨 HTML 스타일 다이얼로그")
        btn_html_test.clicked.connect(self.test_html_dialog_api)
        layout.addWidget(btn_html_test)

        btn_image_test = QPushButton("🖼️ 이미지 포함 다이얼로그")
        btn_image_test.clicked.connect(self.test_image_dialog_api)
        layout.addWidget(btn_image_test)

        # API 연결 테스트
        api_label = QLabel("API 연결 테스트:")
        api_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #9C27B0;")
        layout.addWidget(api_label)

        btn_api_health = QPushButton("🏥 API 서버 Health Check")
        btn_api_health.clicked.connect(self.test_api_health)
        layout.addWidget(btn_api_health)

        btn_llm_simple = QPushButton("🤖 LLM 간단한 질문")
        btn_llm_simple.clicked.connect(self.test_llm_simple)
        layout.addWidget(btn_llm_simple)

        btn_llm_complex = QPushButton("🧠 LLM 복잡한 질문")
        btn_llm_complex.clicked.connect(self.test_llm_complex)
        layout.addWidget(btn_llm_complex)

        # 닫기 버튼
        close_btn = QPushButton("❌ 창 닫기")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("margin-top: 20px; font-weight: bold;")
        layout.addWidget(close_btn)

        # 초기 상태 확인
        QTimer.singleShot(1000, self.check_api_server_status)

    def check_api_server_status(self):
        """API 서버 상태 상세 확인"""
        print(f"[DEBUG] API 서버 상태 확인 시작 - {self.host}:{self.port}")

        try:
            # 1. 포트가 열려있는지 확인
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.host, self.port))
            sock.close()

            if result != 0:
                error_msg = f"포트 {self.port}이 닫혀있습니다 (연결 코드: {result})"
                self.api_status_btn.setText(f"API 서버 상태: ❌ {error_msg}")
                self.api_status_btn.setStyleSheet("color: red;")
                print(f"[ERROR] {error_msg}")
                return

            # 2. HTTP 요청으로 서버 응답 확인
            health_url = f"http://{self.host}:{self.port}/health"
            print(f"[DEBUG] Health check URL: {health_url}")

            response = requests.get(health_url, timeout=5)

            if response.status_code == 200:
                self.api_status_btn.setText("API 서버 상태: ✅ 정상 동작")
                self.api_status_btn.setStyleSheet("color: green;")
                print(f"[DEBUG] API 서버 정상 - 응답: {response.text}")
            else:
                error_msg = f"HTTP {response.status_code}"
                self.api_status_btn.setText(f"API 서버 상태: ⚠️ {error_msg}")
                self.api_status_btn.setStyleSheet("color: orange;")
                print(
                    f"[WARNING] API 서버 응답 이상 - {response.status_code}: {response.text}"
                )

        except requests.exceptions.ConnectionError as e:
            error_msg = f"연결 실패 - {str(e)}"
            self.api_status_btn.setText(f"API 서버 상태: ❌ {error_msg}")
            self.api_status_btn.setStyleSheet("color: red;")
            print(f"[ERROR] API 연결 실패: {e}")

        except requests.exceptions.Timeout:
            error_msg = "요청 시간 초과"
            self.api_status_btn.setText(f"API 서버 상태: ❌ {error_msg}")
            self.api_status_btn.setStyleSheet("color: red;")
            print("[ERROR] API 요청 시간 초과")

        except Exception as e:
            error_msg = f"알 수 없는 오류 - {str(e)}"
            self.api_status_btn.setText(f"API 서버 상태: ❌ {error_msg}")
            self.api_status_btn.setStyleSheet("color: red;")
            print(f"[ERROR] API 상태 확인 중 오류: {e}")
            print(f"[ERROR] 전체 스택 트레이스: {traceback.format_exc()}")

    def test_notification_api(self, notification_type="info"):
        """API를 통해 시스템 알림 테스트"""
        print(f"[DEBUG] {notification_type} 시스템 알림 API 테스트 시작")

        try:
            api_url = f"http://{self.host}:{self.port}/notifications/system"
            payload = {
                "type": notification_type,
                "title": f"{notification_type.capitalize()} 알림",
                "message": f"이것은 {notification_type} 시스템 알림입니다.",
            }

            response = requests.post(
                api_url,
                json=payload,
                timeout=5,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                QMessageBox.information(
                    self,
                    f"{notification_type.capitalize()} 알림 성공",
                    f"✅ {notification_type.capitalize()} 알림이 성공적으로 전송되었습니다.\n"
                    f"상태: {result.get('status', 'unknown')}\n"
                    f"메시지: {result.get('message', 'No message')}",
                )
                print(f"[SUCCESS] {notification_type} 알림 API 성공: {result}")
            else:
                QMessageBox.warning(
                    self,
                    f"{notification_type.capitalize()} 알림 실패",
                    f"❌ HTTP {response.status_code}\n응답: {response.text}",
                )
                print(
                    f"[ERROR] {notification_type} 알림 API 오류 - {response.status_code}: {response.text}"
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                f"{notification_type.capitalize()} 알림 오류",
                f"❌ {notification_type.capitalize()} 알림 요청 실패\n오류: {str(e)}",
            )
            print(f"[ERROR] {notification_type} 알림 API 호출 실패: {e}")

    def test_dialog_api(self, dialog_type="info"):
        """API를 통해 커스텀 다이얼로그 테스트"""
        print(f"[DEBUG] {dialog_type} 다이얼로그 API 테스트 시작")

        try:
            api_url = f"http://{self.host}:{self.port}/notifications/dialog"
            payload = {
                "type": dialog_type,
                "title": f"{dialog_type.capitalize()} 다이얼로그",
                "message": f"이것은 {dialog_type} 커스텀 다이얼로그입니다.\n화면 우측 하단에 표시됩니다.",
                "width": 350,
                "height": 120,
            }

            response = requests.post(
                api_url,
                json=payload,
                timeout=5,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                QMessageBox.information(
                    self,
                    f"{dialog_type.capitalize()} 다이얼로그 성공",
                    f"✅ {dialog_type.capitalize()} 다이얼로그가 성공적으로 전송되었습니다.\n"
                    f"상태: {result.get('status', 'unknown')}\n"
                    f"메시지: {result.get('message', 'No message')}",
                )
                print(f"[SUCCESS] {dialog_type} 다이얼로그 API 성공: {result}")
            else:
                QMessageBox.warning(
                    self,
                    f"{dialog_type.capitalize()} 다이얼로그 실패",
                    f"❌ HTTP {response.status_code}\n응답: {response.text}",
                )
                print(
                    f"[ERROR] {dialog_type} 다이얼로그 API 오류 - {response.status_code}: {response.text}"
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                f"{dialog_type.capitalize()} 다이얼로그 오류",
                f"❌ {dialog_type.capitalize()} 다이얼로그 요청 실패\n오류: {str(e)}",
            )
            print(f"[ERROR] {dialog_type} 다이얼로그 API 호출 실패: {e}")

    def test_html_dialog_api(self):
        """HTML 다이얼로그 알림 API 테스트"""
        try:
            api_url = f"http://{self.host}:{self.port}/notifications/dialog/html"

            # HTML 컨텐츠 준비
            html_content = """
            <div style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #2563EB; margin-bottom: 15px;">🎉 HTML 알림 테스트</h2>
                <p style="color: #4B5563; line-height: 1.6;">
                    이것은 <strong>HTML</strong> 형식의 알림 메시지입니다.<br>
                    <span style="color: #059669;">✅ 마크다운과 달리 HTML 태그가 직접 렌더링됩니다.</span>
                </p>
                <div style="background-color: #F3F4F6; padding: 10px; border-radius: 8px; margin-top: 10px;">
                    <code style="color: #DC2626;">HTML 태그가 그대로 표시됩니다!</code>
                </div>
            </div>
            """

            payload = {
                "title": "HTML 알림 테스트",
                "message": "이것은 일반 텍스트 메시지입니다.",
                "html_message": html_content,
                "notification_type": "info",
                "width": 400,
                "height": 250,
                "duration": 5000,
            }

            response = requests.post(
                api_url,
                json=payload,
                timeout=5,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                QMessageBox.information(
                    self,
                    "HTML 알림 성공",
                    f"✅ HTML 알림이 성공적으로 전송되었습니다.\n"
                    f"상태: {result.get('status', 'unknown')}\n"
                    f"메시지: {result.get('message', 'No message')}",
                )
                print(f"[SUCCESS] HTML 알림 API 성공: {result}")
            else:
                QMessageBox.warning(
                    self,
                    "HTML 알림 실패",
                    f"❌ HTTP {response.status_code}\n응답: {response.text}",
                )
                print(
                    f"[ERROR] HTML 알림 API 오류 - {response.status_code}: {response.text}"
                )

        except Exception as e:
            QMessageBox.critical(
                self, "HTML 알림 오류", f"❌ HTML 알림 요청 실패\n오류: {str(e)}"
            )
            print(f"[ERROR] HTML 알림 API 호출 실패: {e}")

    def test_image_dialog_api(self):
        """API를 통해 이미지 포함 다이얼로그 테스트"""
        print("[DEBUG] 이미지 포함 다이얼로그 API 테스트 시작")

        html_content = """
        <div style="font-family: Arial, sans-serif; text-align: center;">
            <h3 style="color: #FF6B6B; margin: 10px 0;">📷 이미지 다이얼로그</h3>
            <img src="https://via.placeholder.com/200x100/4CAF50/white?text=Sample+Image"
                 style="border-radius: 8px; margin: 10px 0;" width="200" height="100">
            <p style="margin: 10px 0;">
                위에 샘플 이미지가 표시됩니다.<br>
                <small style="color: #888;">이미지는 온라인에서 로드됩니다</small>
            </p>
        </div>
        """

        try:
            api_url = f"http://{self.host}:{self.port}/notifications/dialog/html"
            payload = {
                "title": "이미지 다이얼로그 테스트",
                "message": "이미지가 포함된 HTML 다이얼로그입니다.",
                "html_message": html_content,
                "notification_type": "info",
                "width": 250,
                "height": 200,
                "duration": 5000,
            }

            response = requests.post(
                api_url,
                json=payload,
                timeout=5,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                QMessageBox.information(
                    self,
                    "이미지 다이얼로그 성공",
                    f"✅ 이미지 포함 다이얼로그가 성공적으로 전송되었습니다.\n"
                    f"상태: {result.get('status', 'unknown')}\n"
                    f"메시지: {result.get('message', 'No message')}",
                )
                print(f"[SUCCESS] 이미지 다이얼로그 API 성공: {result}")
            else:
                QMessageBox.warning(
                    self,
                    "이미지 다이얼로그 실패",
                    f"❌ HTTP {response.status_code}\n응답: {response.text}",
                )
                print(
                    f"[ERROR] 이미지 다이얼로그 API 오류 - {response.status_code}: {response.text}"
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "이미지 다이얼로그 오류",
                f"❌ 이미지 다이얼로그 요청 실패\n오류: {str(e)}",
            )
            print(f"[ERROR] 이미지 다이얼로그 API 호출 실패: {e}")

    def test_api_health(self):
        """API Health Check 테스트"""
        print("[DEBUG] API Health Check 테스트 시작")

        try:
            health_url = f"http://{self.host}:{self.port}/health"
            response = requests.get(health_url, timeout=5)

            if response.status_code == 200:
                result = response.json()
                QMessageBox.information(
                    self,
                    "API Health Check 성공",
                    f"✅ API 서버 상태: {result.get('status', 'unknown')}\n"
                    f"메시지: {result.get('message', 'No message')}",
                )
                print(f"[SUCCESS] API Health Check 성공: {result}")
            else:
                QMessageBox.warning(
                    self,
                    "API Health Check 실패",
                    f"❌ HTTP {response.status_code}\n응답: {response.text}",
                )
                print(f"[ERROR] API Health Check 실패: {response.status_code}")

        except Exception as e:
            QMessageBox.critical(
                self, "API Health Check 오류", f"❌ API 연결 실패\n오류: {str(e)}"
            )
            print(f"[ERROR] API Health Check 오류: {e}")

    def test_llm_simple(self):
        """LLM 간단한 질문 테스트"""
        api_url = f"http://{self.host}:{self.port}/llm"
        payload = {"prompt": "안녕하세요! 간단한 인사말을 해주세요."}

        print(f"[DEBUG] LLM 간단 질문 요청 - URL: {api_url}")

        try:
            response = requests.post(
                api_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
            print(
                f"[DEBUG] LLM 간단 질문 API 응답: {response.status_code} - {response.text}"
            )

            if response.status_code == 200:
                result = response.json()
                QMessageBox.information(
                    self,
                    "LLM 요청 성공",
                    f"✅ LLM 요청이 성공적으로 전송되었습니다.\n"
                    f"상태: {result.get('status', 'unknown')}\n"
                    f"메시지: {result.get('message', 'No message')}",
                )
                print(f"[SUCCESS] LLM 간단 질문 성공: {result}")
            else:
                QMessageBox.warning(
                    self,
                    "LLM 요청 실패",
                    f"❌ HTTP {response.status_code}\n응답: {response.text}",
                )
                print(
                    f"[ERROR] LLM 간단 질문 오류 - {response.status_code}: {response.text}"
                )

        except Exception as exception:
            QMessageBox.critical(
                self, "LLM 요청 오류", f"❌ LLM 요청 실패\n오류: {str(exception)}"
            )
            print(f"[ERROR] LLM 간단 질문 API 호출 실패: {exception}")

    def test_llm_complex(self):
        """LLM 복잡한 질문 테스트"""
        api_url = f"http://{self.host}:{self.port}/llm"
        payload = {"prompt": "간단한 Python 함수 예제를 하나 보여주고 설명해주세요."}

        print(f"[DEBUG] LLM 복잡 질문 요청 - URL: {api_url}")

        try:
            response = requests.post(
                api_url,
                json=payload,
                timeout=15,
                headers={"Content-Type": "application/json"},
            )
            print(
                f"[DEBUG] LLM 복잡 질문 API 응답: {response.status_code} - {response.text}"
            )

            if response.status_code == 200:
                result = response.json()
                QMessageBox.information(
                    self,
                    "LLM 복잡 요청 성공",
                    f"✅ LLM 복잡 요청이 성공적으로 전송되었습니다.\n"
                    f"상태: {result.get('status', 'unknown')}\n"
                    f"메시지: {result.get('message', 'No message')}",
                )
                print(f"[SUCCESS] LLM 복잡 질문 성공: {result}")
            else:
                QMessageBox.warning(
                    self,
                    "LLM 복잡 요청 실패",
                    f"❌ HTTP {response.status_code}\n응답: {response.text}",
                )
                print(
                    f"[ERROR] LLM 복잡 질문 오류 - {response.status_code}: {response.text}"
                )

        except Exception as exception:
            QMessageBox.critical(
                self,
                "LLM 복잡 요청 오류",
                f"❌ LLM 복잡 요청 실패\n오류: {str(exception)}",
            )
            print(f"[ERROR] LLM 복잡 질문 API 호출 실패: {exception}")
