"""
LLM 성능 메트릭스 수집
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional


@dataclass
class LLMMetrics:
    """LLM 성능 메트릭스"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    tool_usage: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    agent_usage: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def average_response_time(self) -> float:
        """평균 응답 시간"""
        return self.total_response_time / max(1, self.total_requests)

    @property
    def success_rate(self) -> float:
        """성공률 (0.0 ~ 1.0)"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def failure_rate(self) -> float:
        """실패율 (0.0 ~ 1.0)"""
        return 1.0 - self.success_rate

    def add_request(
        self,
        response_time: float,
        success: bool = True,
        agent_type: Optional[str] = None,
        model: Optional[str] = None,
        tools_used: Optional[list] = None,
        error_type: Optional[str] = None,
    ) -> None:
        """요청 메트릭 추가"""
        self.total_requests += 1
        self.total_response_time += response_time
        self.response_times.append(response_time)

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.error_counts[error_type] += 1

        if agent_type:
            self.agent_usage[agent_type] += 1

        if tools_used:
            for tool in tools_used:
                self.tool_usage[tool] += 1

    def get_stats(self) -> Dict:
        """통계 정보 반환"""
        return {
            "total_requests": self.total_requests,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "average_response_time": self.average_response_time,
            "recent_response_times": list(self.response_times)[-10:],
            "top_tools": dict(sorted(self.tool_usage.items(), key=lambda x: x[1], reverse=True)[:5]),
            "agent_usage": dict(self.agent_usage),
            "error_distribution": dict(self.error_counts),
        }

    def reset(self) -> None:
        """메트릭스 초기화"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_response_time = 0.0
        self.response_times.clear()
        self.tool_usage.clear()
        self.error_counts.clear()
        self.agent_usage.clear()


# 간단한 전역 메트릭스 및 락
_global_metrics = LLMMetrics()
_metrics_lock = Lock()


def track_response(
    response_time: float,
    success: bool = True,
    agent_type: Optional[str] = None,
    model: Optional[str] = None,
    tools_used: Optional[list] = None,
    error_type: Optional[str] = None,
) -> None:
    """응답 메트릭스 추적 (편의 함수)"""
    with _metrics_lock:
        _global_metrics.add_request(
            response_time=response_time,
            success=success,
            agent_type=agent_type,
            model=model,
            tools_used=tools_used,
            error_type=error_type,
        )


def get_global_metrics() -> Dict:
    """전역 메트릭스 통계 반환"""
    with _metrics_lock:
        return _global_metrics.get_stats()


def reset_global_metrics() -> None:
    """전역 메트릭스 초기화"""
    with _metrics_lock:
        _global_metrics.reset() 