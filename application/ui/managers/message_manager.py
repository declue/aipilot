import logging

from PySide6.QtCore import QTimer

from application.ui.ai_chat_bubble import AIChatBubble
from application.ui.system_chat_bubble import SystemChatBubble
from application.ui.user_chat_bubble import UserChatBubble

logger = logging.getLogger("main_window")


class MessageManager:
    """메시지 추가/관리 담당 클래스"""

    def __init__(self, main_window):
        self.main_window = main_window
        self.ui_config = main_window.ui_config
        self.current_ai_bubble = None  # 현재 스트리밍 중인 AI 버블 추적

    def add_user_message(self, message: str):
        """사용자 메시지 추가"""
        # 마지막 스페이서 제거 (있다면)
        if self.main_window.chat_layout.count() > 0:
            last_item = self.main_window.chat_layout.itemAt(
                self.main_window.chat_layout.count() - 1
            )
            if last_item and last_item.spacerItem():
                self.main_window.chat_layout.removeItem(last_item)

        # 최신 UI 설정 사용
        current_ui_config = self.main_window.ui_config
        bubble = UserChatBubble(message, ui_config=current_ui_config)
        self.main_window.chat_layout.addWidget(bubble)

        # 스페이서 다시 추가
        self.main_window.chat_layout.addStretch()

        # 스크롤을 맨 아래로 (자동 스크롤 활성화 시에만)
        self.main_window.scroll_to_bottom()

    def add_ai_message(self, message: str, used_tools=None):
        """AI 메시지 추가"""
        # 마지막 스페이서 제거 (있다면)
        if self.main_window.chat_layout.count() > 0:
            last_item = self.main_window.chat_layout.itemAt(
                self.main_window.chat_layout.count() - 1
            )
            if last_item and last_item.spacerItem():
                self.main_window.chat_layout.removeItem(last_item)

        # 최신 UI 설정 사용
        current_ui_config = self.main_window.ui_config
        bubble = AIChatBubble(message, ui_config=current_ui_config)

        # 도구 정보 설정 (있는 경우)
        if used_tools:
            bubble.set_used_tools(used_tools)

        self.main_window.chat_layout.addWidget(bubble)

        # 현재 AI 버블 추적 (스트리밍 완료 시 Raw 버튼 표시용)
        self.current_ai_bubble = bubble

        # 일반 AI 응답의 경우 즉시 Raw 버튼 표시
        bubble.show_raw_button()

        # 스페이서 다시 추가
        self.main_window.chat_layout.addStretch()

        # 스크롤을 맨 아래로 (자동 스크롤 활성화 시에만)
        self.main_window.scroll_to_bottom()

    def add_github_message(self, message: str):
        """GitHub webhook 메시지 추가"""
        # 마지막 스페이서 제거 (있다면)
        if self.main_window.chat_layout.count() > 0:
            last_item = self.main_window.chat_layout.itemAt(
                self.main_window.chat_layout.count() - 1
            )
            if last_item and last_item.spacerItem():
                self.main_window.chat_layout.removeItem(last_item)

        # GitHub 버블 생성
        current_ui_config = self.main_window.ui_config
        bubble = AIChatBubble.create_github_bubble(
            message=message, ui_config=current_ui_config
        )

        # Raw 버튼 즉시 표시
        bubble.show_raw_button()

        self.main_window.chat_layout.addWidget(bubble)

        # 스페이서 다시 추가
        self.main_window.chat_layout.addStretch()

        # 스크롤을 맨 아래로 (자동 스크롤 활성화 시에만)
        self.main_window.scroll_to_bottom()

    def add_system_message(self, message: str):
        """시스템 메시지 추가 (API 알림 등)"""
        logger.debug("시스템 메시지 추가: %s...", message[:50])

        # 마지막 스페이서 제거 (있다면)
        if self.main_window.chat_layout.count() > 0:
            last_item = self.main_window.chat_layout.itemAt(
                self.main_window.chat_layout.count() - 1
            )
            if last_item and last_item.spacerItem():
                self.main_window.chat_layout.removeItem(last_item)

        # 최신 UI 설정 사용
        current_ui_config = self.main_window.ui_config
        bubble = SystemChatBubble(message, ui_config=current_ui_config)
        self.main_window.chat_layout.addWidget(bubble)

        # 스페이서 다시 추가
        self.main_window.chat_layout.addStretch()

        # 높이 자동 조정 (지연 실행으로 레이아웃 적용 후)
        QTimer.singleShot(50, lambda: bubble.adjust_browser_height(bubble.text_browser))

        # 스크롤을 맨 아래로 (더 긴 지연으로) (자동 스크롤 활성화 시에만)
        QTimer.singleShot(100, self.main_window.scroll_to_bottom)

    def add_html_message(self, html_content: str):
        """HTML 메시지 추가 (HTML 다이얼로그 알림용)"""
        logger.debug("HTML 메시지 추가: %s...", html_content[:50])

        # 마지막 스페이서 제거 (있다면)
        if self.main_window.chat_layout.count() > 0:
            last_item = self.main_window.chat_layout.itemAt(
                self.main_window.chat_layout.count() - 1
            )
            if last_item and last_item.spacerItem():
                self.main_window.chat_layout.removeItem(last_item)

        # 최신 UI 설정 사용
        current_ui_config = self.main_window.ui_config
        bubble = SystemChatBubble(
            html_content, ui_config=current_ui_config, is_html=True
        )
        self.main_window.chat_layout.addWidget(bubble)

        # 스페이서 다시 추가
        self.main_window.chat_layout.addStretch()

        # 높이 자동 조정 (지연 실행으로 레이아웃 적용 후)
        QTimer.singleShot(50, lambda: bubble.adjust_browser_height(bubble.text_browser))

        # 스크롤을 맨 아래로 (더 긴 지연으로) (자동 스크롤 활성화 시에만)
        QTimer.singleShot(100, self.main_window.scroll_to_bottom)

    def show_current_ai_raw_button(self):
        """현재 AI 버블의 Raw 버튼 표시 (스트리밍 완료 후 호출)"""
        if self.current_ai_bubble:
            self.current_ai_bubble.show_raw_button()
            logger.debug("Raw button shown for current AI bubble")
            self.current_ai_bubble = None  # 추적 해제

    def update_all_message_styles(self):
        """모든 메시지 스타일을 새로운 UI 설정으로 업데이트"""
        logger.debug("모든 메시지 스타일 업데이트 시작")

        # UI 설정 업데이트
        self.ui_config = self.main_window.ui_config
        logger.debug(
            f"새 UI 설정: 폰트={self.ui_config.get('font_family')}, 크기={self.ui_config.get('font_size')}px"
        )

        updated_count = 0

        # 모든 채팅 버블 위젯들 찾기
        for i in range(self.main_window.chat_layout.count()):
            item = self.main_window.chat_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    # 각 버블 타입에 따라 스타일 업데이트
                    if hasattr(widget, "update_ui_config") and hasattr(
                        widget, "update_styles"
                    ):
                        widget.update_ui_config(self.ui_config)
                        widget.update_styles()
                        updated_count += 1

        logger.debug(f"총 {updated_count}개 버블 스타일 업데이트 완료")

        # 채팅 영역 레이아웃 새로고침
        if hasattr(self.main_window, "chat_area") and self.main_window.chat_area:
            self.main_window.chat_area.updateGeometry()
            self.main_window.chat_area.update()

        # 스크롤 영역 새로고침
        if hasattr(self.main_window, "scroll_area") and self.main_window.scroll_area:
            self.main_window.scroll_area.updateGeometry()
            self.main_window.scroll_area.update()

        logger.debug("채팅 영역 레이아웃 새로고침 완료")

    def clear_chat_area(self):
        """채팅 영역 비우기"""
        # 기존 채팅 버블들 제거
        for i in reversed(range(self.main_window.chat_layout.count())):
            item = self.main_window.chat_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                else:
                    # 스페이서 아이템인 경우
                    self.main_window.chat_layout.removeItem(item)
