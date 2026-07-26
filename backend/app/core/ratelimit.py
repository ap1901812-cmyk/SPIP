from __future__ import annotations

import time
from typing import ClassVar

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import RateLimitExceededError


class MemoryRateLimiter:
    """In-memory sliding window rate limiter for V1 foundation.
    Designed for easy swap with Redis in multi-instance scale phase.
    """

    _requests: ClassVar[dict[str, list[float]]] = {}

    @classmethod
    def check_rate_limit(cls, client_identifier: str, limit_per_minute: int | None = None) -> None:
        cfg = get_settings()
        limit = limit_per_minute if limit_per_minute is not None else cfg.rate_limit_per_minute
        now = time.time()
        window_start = now - 60.0

        history = cls._requests.get(client_identifier, [])
        valid_history = [ts for ts in history if ts > window_start]

        if len(valid_history) >= limit:
            raise RateLimitExceededError()

        valid_history.append(now)
        cls._requests[client_identifier] = valid_history

    @classmethod
    def clear(cls) -> None:
        cls._requests.clear()


async def rate_limit_dependency(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    MemoryRateLimiter.check_rate_limit(client_ip)
