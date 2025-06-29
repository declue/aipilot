from __future__ import annotations

"""Session 관리 모듈

현재 CLI 애플리케이션에서 세션 정보를 `session_start`, `query_count` 두 필드로만
직접 관리하고 있었지만, 기능 확장성을 위해 별도의 세션 객체로 추상화한다.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Session:  # pylint: disable=too-many-instance-attributes
    """DSPilot CLI 세션 정보를 보관하는 데이터 클래스

    Attributes
    ----------
    session_id : str
        UUID4 기반 세션 고유 식별자
    start_time : datetime
        세션 시작 시각
    query_count : int, default 0
        현재 세션 동안 처리된 쿼리 수
    last_query_time : Optional[datetime]
        마지막 쿼리 처리 시각. `increment_query_count()` 호출 시 갱신된다.
    """

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime = field(default_factory=datetime.now)
    query_count: int = 0
    last_query_time: Optional[datetime] = None

    # === 상태 갱신 메서드 === #
    def increment_query_count(self) -> None:
        """쿼리 카운터를 1 증가시키고 `last_query_time` 을 현재 시각으로 설정한다."""
        self.query_count += 1
        self.last_query_time = datetime.now()

    # === 통계/헬퍼 메서드 === #
    def get_elapsed(self) -> float:
        """세션 시작 이후 경과 시간을 초 단위로 반환한다."""
        return (datetime.now() - self.start_time).total_seconds()

    def __repr__(self) -> str:  # pragma: no cover – 가독성용
        return (
            f"Session(id={self.session_id}, start={self.start_time.isoformat()}, "
            f"queries={self.query_count})"
        )
