import sys
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
    QSystemTrayIcon,
    QStyle,
    QMenu
)
from notifypy import Notify  # notify-py 사용

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("메신저 프로토타입 (notify-py)")
        self.resize(400, 300)

        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 상태 표시 라벨
        self.status_btn = QPushButton("트레이 상태: 확인 중...")
        self.status_btn.setEnabled(False)
        layout.addWidget(self.status_btn)

        # 버튼: 3초간 자동 사라지는 알림
        btn_timed = QPushButton("3초 자동 알림 띄우기")
        btn_timed.clicked.connect(self.show_timed_notification)
        layout.addWidget(btn_timed)

        # 버튼: 확인 눌러야 닫히는 알림
        btn_confirm = QPushButton("확인 버튼 알림 띄우기")
        btn_confirm.clicked.connect(self.show_confirm_notification)
        layout.addWidget(btn_confirm)

        # 버튼: 트레이로 숨기기
        btn_hide = QPushButton("트레이로 숨기기")
        btn_hide.clicked.connect(self.hide_to_tray)
        layout.addWidget(btn_hide)

        # 버튼: 트레이 아이콘 강제 표시
        btn_show_tray = QPushButton("트레이 아이콘 다시 표시")
        btn_show_tray.clicked.connect(self.force_show_tray)
        layout.addWidget(btn_show_tray)

    def update_tray_status(self, message):
        """트레이 상태 업데이트"""
        self.status_btn.setText(f"트레이 상태: {message}")
        print(f"[DEBUG] 트레이 상태: {message}")

    def hide_to_tray(self):
        """트레이로 숨기기"""
        self.hide()
        # 트레이 메시지 표시
        if hasattr(self, 'tray_app') and self.tray_app.tray.isVisible():
            self.tray_app.tray.showMessage(
                "프로그램 숨김",
                "프로그램이 트레이로 숨겨졌습니다.\n트레이 아이콘을 더블클릭하여 다시 열 수 있습니다.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )

    def force_show_tray(self):
        """트레이 아이콘 강제 표시"""
        if hasattr(self, 'tray_app'):
            self.tray_app.force_show_tray_icon()

    def show_timed_notification(self):
        """
        notify-py를 이용해 윈도우 네이티브 토스트 알림을 띄웁니다.
        notify.send() 이후 알림은 OS가 지정한 기본 시간(Windows 기준 약 5~7초) 동안 화면에 머무르고 사라집니다.
        """
        notification = Notify()
        notification.title = "새 메시지 도착"
        notification.message = "3초 후에 자동으로 사라지는 알림 예제입니다."
        # (선택) 아이콘이 필요하다면 아래처럼 경로를 지정할 수 있습니다.
        # notification.icon = "icon.png"
        notification.send()

        # ※ 윈도우에서 notify-py로 duration을 강제 3초로 지정하는 기능은 제공하지 않습니다.
        #   OS가 기본으로 지정한 시간(약 5~7초) 동안 보여진 뒤 자동으로 사라집니다.
        #   프로토타입이라면 이 동작만으로 충분하고, 만약 "정확히 3초"를 보장해야 한다면
        #   Windows ToastNotification API를 직접 호출해야 합니다.

    def show_confirm_notification(self):
        """
        확인 버튼을 눌러야 닫히는 알림을 PySide6의 QMessageBox로 구현합니다.
        실제로 Windows 네이티브 토스트에서 "버튼 클릭" 기반 상호작용을 구현하려면
        별도의 WinRT/Windows API 호출이 필요하지만, 프로토타입 수준에서는 QMessageBox로 대체합니다.
        """
        dlg = QMessageBox(self)
        dlg.setWindowTitle("확인 필요")
        dlg.setText("이 알림은 확인(OK) 버튼을 눌러야 닫힙니다.")
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
        dlg.exec()

    def closeEvent(self, event):
        """
        윈도우 닫기 버튼 클릭 시 트레이로 숨기기
        """
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            event.ignore()  # 실제 종료를 막음
            print("[DEBUG] 창 닫기 -> 트레이로 숨김")
        else:
            event.accept()  # 트레이가 지원되지 않으면 종료


class TrayApp:
    def __init__(self, app: QApplication):
        self.app = app
        
        # 시스템 트레이 지원 여부 확인
        print(f"[DEBUG] 시스템 트레이 지원 여부: {QSystemTrayIcon.isSystemTrayAvailable()}")
        
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(
                None, 
                "시스템 트레이", 
                "시스템 트레이를 사용할 수 없습니다.\n"
                "이 프로그램은 시스템 트레이가 필요합니다."
            )
            sys.exit(1)
        
        self.window = MainWindow()
        self.window.tray_app = self  # 창에서 트레이앱 참조 가능하도록

        self.create_tray_icon()
        
        # 시작 시 윈도우 보이기 (사용자가 확인할 수 있도록)
        self.window.show()
        
        # (테스트용) 앱 실행 10초 후에 자동으로 3초 알림 띄우기
        QTimer.singleShot(10000, self.window.show_timed_notification)

    def create_custom_icon(self):
        """커스텀 아이콘 생성 (더 잘 보이는 아이콘)"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 파란색 원 그리기
        painter.setBrush(Qt.GlobalColor.blue)
        painter.setPen(Qt.GlobalColor.darkBlue)
        painter.drawEllipse(2, 2, 28, 28)
        
        # 흰색 M 글자 그리기
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(painter.font())
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "M")
        
        painter.end()
        
        return QIcon(pixmap)

    def create_tray_icon(self):
        """트레이 아이콘 생성"""
        print("[DEBUG] 트레이 아이콘 생성 시작")
        
        # 여러 아이콘 시도
        icon = None
        
        # 1. 커스텀 아이콘 시도
        try:
            icon = self.create_custom_icon()
            print("[DEBUG] 커스텀 아이콘 생성 성공")
        except Exception as e:
            print(f"[DEBUG] 커스텀 아이콘 생성 실패: {e}")
            
        # 2. 기본 시스템 아이콘 시도
        if icon is None or icon.isNull():
            try:
                icon = self.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
                print("[DEBUG] 시스템 아이콘 사용")
            except Exception as e:
                print(f"[DEBUG] 시스템 아이콘 실패: {e}")
                
        # 3. 다른 시스템 아이콘들 시도
        if icon is None or icon.isNull():
            icon_types = [
                QStyle.StandardPixmap.SP_MessageBoxInformation,
                QStyle.StandardPixmap.SP_FileDialogStart,
                QStyle.StandardPixmap.SP_DirIcon
            ]
            for icon_type in icon_types:
                try:
                    icon = self.app.style().standardIcon(icon_type)
                    if not icon.isNull():
                        print(f"[DEBUG] 대체 아이콘 사용: {icon_type}")
                        break
                except:
                    continue

        # 트레이 아이콘 생성
        self.tray = QSystemTrayIcon(icon, parent=self.app)
        self.tray.setToolTip("메신저 프로토타입 (notify-py)\n더블클릭하여 창 열기")

        # 트레이 아이콘 활성화 시그널 연결
        self.tray.activated.connect(self.on_tray_activated)

        # 트레이 아이콘 우클릭 메뉴 (컨텍스트 메뉴) 설정
        self.menu = QMenu()
        
        action_show = QAction("창 열기", self.window)
        action_show.triggered.connect(self.show_window)
        self.menu.addAction(action_show)
        
        action_hide = QAction("창 숨기기", self.window)
        action_hide.triggered.connect(self.hide_window)
        self.menu.addAction(action_hide)
        
        self.menu.addSeparator()
        
        action_notification = QAction("테스트 알림", self.window)
        action_notification.triggered.connect(self.window.show_timed_notification)
        self.menu.addAction(action_notification)
        
        self.menu.addSeparator()
        
        action_quit = QAction("종료", self.window)
        action_quit.triggered.connect(self.exit_app)
        self.menu.addAction(action_quit)
        
        self.tray.setContextMenu(self.menu)

        # 트레이 아이콘 표시
        self.force_show_tray_icon()

    def force_show_tray_icon(self):
        """트레이 아이콘 강제 표시"""
        print("[DEBUG] 트레이 아이콘 표시 시도")
        
        try:
            self.tray.show()
            
            # 아이콘이 실제로 표시되었는지 확인
            QTimer.singleShot(1000, self.check_tray_visibility)
            
            # 트레이 아이콘이 표시되었다는 알림
            self.tray.showMessage(
                "메신저 프로토타입",
                "프로그램이 시스템 트레이에서 실행 중입니다.\n"
                "트레이 아이콘을 더블클릭하여 창을 열 수 있습니다.\n"
                "\n"
                "※ 아이콘이 보이지 않으면 작업표시줄 설정에서\n"
                "'숨겨진 아이콘 표시'를 클릭하거나\n"
                "알림 영역 설정을 확인해주세요.",
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )
            
            print("[DEBUG] 트레이 아이콘 표시 완료")
            self.window.update_tray_status("표시됨 (작업표시줄 우측 하단 확인)")
            
        except Exception as e:
            print(f"[DEBUG] 트레이 아이콘 표시 실패: {e}")
            self.window.update_tray_status(f"표시 실패: {e}")

    def check_tray_visibility(self):
        """트레이 아이콘 가시성 확인"""
        is_visible = self.tray.isVisible()
        print(f"[DEBUG] 트레이 아이콘 가시성: {is_visible}")
        
        if is_visible:
            self.window.update_tray_status("정상 표시됨")
        else:
            self.window.update_tray_status("표시되지 않음 - Windows 설정 확인 필요")
            # 다시 시도
            QTimer.singleShot(2000, self.retry_show_tray)

    def retry_show_tray(self):
        """트레이 아이콘 재시도"""
        print("[DEBUG] 트레이 아이콘 재시도")
        self.tray.hide()
        QTimer.singleShot(500, lambda: self.tray.show())

    def on_tray_activated(self, reason):
        """
        트레이 아이콘이 클릭/더블클릭될 때 발생하는 콜백.
        DoubleClick(더블 클릭) 이벤트 발생 시 메인 윈도우 토글.
        """
        print(f"[DEBUG] 트레이 아이콘 클릭: {reason}")
        
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            print("[DEBUG] 더블클릭 -> 창 토글")
            self.toggle_window()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 단일 클릭 시에도 창 토글 (일부 시스템에서 더블클릭이 잘 안되는 경우를 위해)
            print("[DEBUG] 단일클릭 -> 창 토글")
            self.toggle_window()

    def toggle_window(self):
        """
        메인 윈도우를 보이거나 숨깁니다.
        """
        if self.window.isVisible():
            print("[DEBUG] 창 숨기기")
            self.hide_window()
        else:
            print("[DEBUG] 창 보이기")
            self.show_window()

    def show_window(self):
        """
        메인 윈도우를 표시합니다.
        """
        self.window.show()
        self.window.raise_()        # 최상위로 올리기
        self.window.activateWindow()
        # 최소화 상태 해제
        self.window.setWindowState(self.window.windowState() & ~Qt.WindowState.Minimized)

    def hide_window(self):
        """
        메인 윈도우를 숨깁니다.
        """
        self.window.hide()

    def exit_app(self):
        """
        애플리케이션 종료 처리
        """
        print("[DEBUG] 애플리케이션 종료")
        self.tray.hide()
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 윈도우에서는 트레이 아이콘만 켜져 있어도 앱이 살아있도록 설정해야 합니다.
    app.setQuitOnLastWindowClosed(False)

    print("[DEBUG] 애플리케이션 시작")
    tray_app = TrayApp(app)
    
    sys.exit(app.exec())
