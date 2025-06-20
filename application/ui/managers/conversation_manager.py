import logging

logger = logging.getLogger("main_window")


class ConversationManager:
    """대화 히스토리 관리 담당 클래스"""

    def __init__(self):
        self.conversation_history = []

    def add_user_message(self, content: str):
        """사용자 메시지를 히스토리에 추가"""
        self.conversation_history.append({"role": "user", "content": content})
        logger.debug("대화 히스토리 길이: %s", len(self.conversation_history))

    def add_assistant_message(self, content: str):
        """어시스턴트 메시지를 히스토리에 추가"""
        self.conversation_history.append({"role": "assistant", "content": content})
        logger.debug(
            "AI 응답 추가 후 대화 히스토리 길이: %s", len(self.conversation_history)
        )

    def clear_history(self):
        """대화 히스토리 초기화"""
        self.conversation_history = []

    def get_history(self):
        """대화 히스토리 반환"""
        return self.conversation_history
