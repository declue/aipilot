from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from dspilot_app.ui.presentation.ai_chat_bubble import AIChatBubble


class StreamingState:
    """스트리밍 상태를 관리하는 클래스"""

    def __init__(self) -> None:
        self._initialize()

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------
    def _initialize(self) -> None:
        """공통 초기화 로직 (reset / __init__ 공유)."""
        self.is_streaming: bool = False
        self.streaming_content: str = ""
        self.reasoning_content: str = ""
        self.final_answer: str = ""
        self.is_reasoning_model: bool = False
        self.used_tools: list = []
        self.pending_chunks: list[str] = []
        self.current_streaming_bubble: Optional["AIChatBubble"] = None
        self.current_worker: Any = None

    # ---- 상태 메서드 ----
    def reset(self) -> None:
        """상태 초기화 (in-place)."""
        self._initialize()

    def start_streaming(self) -> None:
        """스트리밍 시작"""
        self.is_streaming = True
        self.streaming_content = ""
        self.reasoning_content = ""
        self.final_answer = ""
        self.is_reasoning_model = False
        self.used_tools = []
        self.pending_chunks = []

    def add_chunk(self, chunk: str) -> None:
        """스트리밍 청크 추가"""
        if self.is_streaming:
            self.pending_chunks.append(chunk)

    def process_pending_chunks(self) -> bool:
        """대기 중인 청크들 처리

        Returns True if any chunk processed.
        """
        if not self.pending_chunks:
            return False

        self.streaming_content += "".join(self.pending_chunks)
        self.pending_chunks.clear()
        return True
