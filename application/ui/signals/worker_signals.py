from PySide6.QtCore import QObject, Signal


class WorkerSignals(QObject):
    result = Signal(str)
    error = Signal(str)
    # 스트리밍 응답용 시그널 추가
    streaming_started = Signal()  # 스트리밍 시작
    streaming_chunk = Signal(str)  # 스트리밍 청크 (부분 응답)
    streaming_finished = Signal()  # 스트리밍 완료
