"""Rate limiter por IP — janela deslizante."""

import time
from collections import defaultdict
from typing import Dict, List, Optional


class RateLimiter:
    """Limita requests por IP usando sliding window."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, ip: str) -> bool:
        now = time.time()
        self._requests[ip] = [
            t for t in self._requests[ip] if now - t < self.window
        ]
        if len(self._requests[ip]) >= self.max_requests:
            return False
        self._requests[ip].append(now)
        return True

    def reset(self, ip: Optional[str] = None):
        """Reset counters (útil pra testes)."""
        if ip:
            self._requests.pop(ip, None)
        else:
            self._requests.clear()


# Instância global
rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
