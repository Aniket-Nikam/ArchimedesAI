"""Bound paid AI utility work independently from ordinary API requests."""

import threading
from contextlib import contextmanager

from fastapi import HTTPException

import config

_slots = threading.BoundedSemaphore(2)


@contextmanager
def ai_job():
    if not config.GROQ_API_KEY:
        raise HTTPException(
            503,
            "AI tools are currently unavailable. Ask the workspace administrator to enable them.",
        )
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "AI tools are busy. Please retry shortly.")
    try:
        yield
    except RuntimeError as exc:
        raise HTTPException(
            502, "The AI provider could not complete this request. Please retry."
        ) from exc
    finally:
        _slots.release()
