from PySide6.QtCore import QObject, Signal


class WorkerSignals(QObject):
    # result 는 문자열 또는 딕셔너리 등 다양한 형태로 전달될 수 있으므로 object 타입으로 선언
    result = Signal(object)
    error = Signal(str)
    finished = Signal(object)
    # 스트리밍 응답용 시그널 추가
    streaming_started = Signal()  # 스트리밍 시작
    streaming_chunk = Signal(str)  # 스트리밍 청크 (부분 응답)
    streaming_finished = Signal()  # 스트리밍 완료
