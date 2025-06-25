"""
성능 추적 및 데코레이터
"""

import asyncio
import functools
import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Callable, Generator, Optional

from application.llm.monitoring.metrics import track_response
from application.util.logger import setup_logger

logger = setup_logger(__name__) or logging.getLogger(__name__)


class PerformanceTracker:
    """성능 추적 컨텍스트 매니저 및 데코레이터"""
    
    def __init__(
        self,
        operation_name: str,
        agent_type: Optional[str] = None,
        model: Optional[str] = None,
        track_metrics: bool = True,
    ):
        self.operation_name = operation_name
        self.agent_type = agent_type
        self.model = model
        self.track_metrics = track_metrics
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        self.success: bool = True
        self.error_message: Optional[str] = None
    
    @contextmanager
    def track(self) -> Generator["PerformanceTracker", None, None]:
        """동기 컨텍스트 매니저"""
        self.start_time = time.time()
        try:
            logger.debug(f"성능 추적 시작: {self.operation_name}")
            yield self
        except Exception as e:
            self.success = False
            self.error_message = str(e)
            logger.error(f"성능 추적 중 오류 발생: {self.operation_name} - {e}")
            raise
        finally:
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
            self._log_performance()
            self._track_metrics_if_enabled()
    
    @asynccontextmanager
    async def atrack(self) -> AsyncGenerator["PerformanceTracker", None]:
        """비동기 컨텍스트 매니저"""
        self.start_time = time.time()
        try:
            logger.debug(f"비동기 성능 추적 시작: {self.operation_name}")
            yield self
        except Exception as e:
            self.success = False
            self.error_message = str(e)
            logger.error(f"비동기 성능 추적 중 오류 발생: {self.operation_name} - {e}")
            raise
        finally:
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
            self._log_performance()
            self._track_metrics_if_enabled()
    
    def _log_performance(self) -> None:
        """성능 로그 기록"""
        if self.duration is not None:
            if self.success:
                logger.info(
                    f"성능 추적 완료: {self.operation_name} - {self.duration:.3f}초"
                )
            else:
                logger.warning(
                    f"성능 추적 실패: {self.operation_name} - {self.duration:.3f}초 - {self.error_message}"
                )
    
    def _track_metrics_if_enabled(self) -> None:
        """메트릭스 추적 (활성화된 경우)"""
        if self.track_metrics and self.agent_type and self.model and self.duration is not None:
            track_response(
                agent_type=self.agent_type,
                model=self.model,
                response_time=self.duration,
                success=self.success,
                error_type=self.error_message,  # error_message -> error_type으로 수정
            )


def track_performance(
    operation_name: Optional[str] = None,
    agent_type: Optional[str] = None,
    model: Optional[str] = None,
    track_metrics: bool = False,
):
    """성능 추적 데코레이터"""
    
    def decorator(func: Callable) -> Callable:
        func_name = operation_name or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            # 비동기 함수용 데코레이터
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                tracker = PerformanceTracker(
                    operation_name=func_name,
                    agent_type=agent_type,
                    model=model,
                    track_metrics=track_metrics,
                )
                async with tracker.atrack():
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            # 동기 함수용 데코레이터
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                tracker = PerformanceTracker(
                    operation_name=func_name,
                    agent_type=agent_type,
                    model=model,
                    track_metrics=track_metrics,
                )
                with tracker.track():
                    return func(*args, **kwargs)
            return sync_wrapper
    
    return decorator


def track_agent_performance(agent_type: str, model: str):
    """Agent 성능 추적 전용 데코레이터"""
    return track_performance(
        agent_type=agent_type,
        model=model,
        track_metrics=True,
    )


# 편의 함수들
@contextmanager
def track_operation(operation_name: str) -> Generator[PerformanceTracker, None, None]:
    """간단한 동기 성능 추적"""
    tracker = PerformanceTracker(operation_name, track_metrics=False)
    with tracker.track():
        yield tracker


@asynccontextmanager
async def atrack_operation(operation_name: str) -> AsyncGenerator[PerformanceTracker, None]:
    """간단한 비동기 성능 추적"""
    tracker = PerformanceTracker(operation_name, track_metrics=False)
    async with tracker.atrack():
        yield tracker


def measure_time(func_name: str = "operation"):
    """시간 측정 전용 데코레이터 (로깅만)"""
    def decorator(func: Callable) -> Callable:
        name = f"{func_name}:{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.debug(f"실행 시간: {name} - {duration:.3f}초")
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(f"실행 실패: {name} - {duration:.3f}초 - {e}")
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.debug(f"실행 시간: {name} - {duration:.3f}초")
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(f"실행 실패: {name} - {duration:.3f}초 - {e}")
                    raise
            return sync_wrapper
    
    return decorator 