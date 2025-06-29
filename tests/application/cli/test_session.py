from datetime import datetime

from dspilot_cli.session import Session


def test_session_initial_state():
    """Session 인스턴스 생성 시 기본값 검증"""
    session = Session()
    assert session.query_count == 0
    assert isinstance(session.start_time, datetime)
    # 생성 직후 elapsed 는 1초 미만이어야 한다
    assert session.get_elapsed() < 1.0


def test_session_increment_query_count():
    """increment_query_count()가 카운트와 시간 갱신하는지 확인"""
    session = Session()
    session.increment_query_count()
    assert session.query_count == 1
    first_time = session.last_query_time

    # 잠시 대기 후 다시 호출
    session.increment_query_count()
    assert session.query_count == 2
    assert session.last_query_time >= first_time

    # elapsed 는 최소 0초 이상이어야 한다
    assert session.get_elapsed() >= 0 