"""Small, process-local abuse guard for password endpoints."""

import threading
import time
from collections import OrderedDict

from fastapi import HTTPException, Request

_attempts: OrderedDict[str, list[float]] = OrderedDict()
_lock = threading.Lock()


def limit_auth(request: Request):
    host = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _lock:
        times = [t for t in _attempts.pop(host, []) if now - t < 600]
        _attempts[host] = times
        while len(_attempts) > 10000:
            _attempts.popitem(last=False)
        if len(times) >= 30:
            raise HTTPException(
                429,
                "Too many sign-in attempts. Try again in ten minutes.",
                headers={"Retry-After": "600"},
            )
        times.append(now)
