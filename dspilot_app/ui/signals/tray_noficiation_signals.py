from PySide6.QtCore import QObject, Signal


class TrayNotificationSignals(QObject):
    """트레이 알림 시그널"""

    api_notification = Signal(str, str)  # notification_type, title
