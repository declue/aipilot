from PySide6.QtCore import QObject, Signal


class NotificationSignals(QObject):
    # 알림 관련 시그널 (기존 - 채팅창 알림용)
    show_notification = Signal(str, str, str, int)  # type, title, message, duration

    # 새로운 알림 시그널들 (다양한 알림 타입용)
    show_system_notification = Signal(str, str, str)  # title, message, icon_path
    show_dialog_notification = Signal(
        dict
    )  # notification_data - TrayNotificationDialog용

    # 채팅 메시지 관련 시그널
    add_api_message = Signal(
        str, str
    )  # message_type, content - API로 받은 메시지를 대화창에 추가
    add_user_message = Signal(str)  # content - 사용자 메시지를 대화창에 추가
    trigger_llm_response = Signal(str)  # prompt - LLM 응답 요청

    # 채팅 관리 시그널
    clear_chat = Signal()  # 채팅 내용 지우기
    save_chat = Signal(str)  # file_path - 채팅 내용 저장
    load_chat = Signal(str)  # file_path - 채팅 내용 불러오기

    # UI 설정 관련 시그널
    update_ui_settings = Signal(dict)  # settings_dict - UI 설정 업데이트

    # 대화 관련 시그널
    new_conversation = Signal()  # 새 대화 시작

    def __init__(self):
        super().__init__()
        self.main_window = None  # 메인 윈도우 참조용
