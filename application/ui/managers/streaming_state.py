class StreamingState:
    """스트리밍 상태를 관리하는 클래스"""

    def __init__(self):
        self.is_streaming = False
        self.streaming_content = ""
        self.reasoning_content = ""
        self.final_answer = ""
        self.is_reasoning_model = False
        self.used_tools = []
        self.pending_chunks = []
        self.current_streaming_bubble = None
        self.current_worker = None

    def reset(self):
        """상태 초기화"""
        self.is_streaming = False
        self.streaming_content = ""
        self.reasoning_content = ""
        self.final_answer = ""
        self.is_reasoning_model = False
        self.used_tools = []
        self.pending_chunks = []
        self.current_streaming_bubble = None
        self.current_worker = None

    def start_streaming(self):
        """스트리밍 시작"""
        self.is_streaming = True
        self.streaming_content = ""
        self.reasoning_content = ""
        self.final_answer = ""
        self.is_reasoning_model = False
        self.used_tools = []
        self.pending_chunks = []

    def add_chunk(self, chunk: str):
        """스트리밍 청크 추가"""
        if self.is_streaming:
            self.pending_chunks.append(chunk)

    def process_pending_chunks(self):
        """대기 중인 청크들 처리"""
        if not self.pending_chunks:
            return False

        for chunk in self.pending_chunks:
            self.streaming_content += chunk
        self.pending_chunks.clear()
        return True
