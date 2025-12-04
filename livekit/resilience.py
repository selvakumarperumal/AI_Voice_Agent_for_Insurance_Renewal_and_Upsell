"""
Resilience utilities - Retry decorator and circuit breaker.
"""
import asyncio
import logging
import functools
from typing import TypeVar, Callable, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)
T = TypeVar('T')


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""
    
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure: Optional[datetime] = None
        self.success_count = 0
    
    def _should_allow(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN and self.last_failure:
            if (datetime.now() - self.last_failure).total_seconds() >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        return True
    
    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        else:
            self.failure_count = 0
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure = datetime.now()
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} OPEN")
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        if not self._should_allow():
            raise Exception(f"Circuit {self.name} is OPEN")
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, exceptions: tuple = (Exception,)):
    """Decorator for retrying with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), 30)
                        logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__} in {delay:.1f}s")
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


class HealthChecker:
    """Track service health status."""
    
    def __init__(self):
        self.services: dict = {}
    
    def update(self, name: str, healthy: bool, latency_ms: Optional[float] = None):
        self.services[name] = {"healthy": healthy, "latency_ms": latency_ms, "checked": datetime.now().isoformat()}
    
    def is_healthy(self, name: str) -> bool:
        return self.services.get(name, {}).get("healthy", False)
    
    def get_status(self) -> dict:
        return {"services": self.services, "all_healthy": all(s["healthy"] for s in self.services.values())}


health_checker = HealthChecker()
