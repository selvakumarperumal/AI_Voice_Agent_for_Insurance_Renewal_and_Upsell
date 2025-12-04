"""Backend Middleware - Request logging and rate limiting."""
import time
import logging
from typing import Callable, Dict
from collections import defaultdict
from datetime import datetime, timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log HTTP requests with timing."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/health":
            return await call_next(request)
        
        start = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000
        
        logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.2f}ms")
        response.headers["X-Response-Time"] = f"{duration:.2f}ms"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory rate limiting by IP."""
    
    def __init__(self, app, requests_per_minute: int = 100, burst_limit: int = 20):
        super().__init__(app)
        self.limit = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
    
    def _get_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        return forwarded.split(",")[0].strip() if forwarded else (request.client.host or "unknown")
    
    def _is_limited(self, ip: str) -> bool:
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        self.requests[ip] = [t for t in self.requests[ip] if t > cutoff]
        if len(self.requests[ip]) >= self.limit:
            return True
        self.requests[ip].append(now)
        return False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/health":
            return await call_next(request)
        
        ip = self._get_ip(request)
        if self._is_limited(ip):
            logger.warning(f"Rate limit: {ip}")
            return JSONResponse(status_code=429, content={"error": "Too many requests"})
        return await call_next(request)
