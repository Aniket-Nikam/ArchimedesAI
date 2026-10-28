"""Bound paid AI utility work independently from ordinary API requests."""

import threading
import time
import uuid
from contextlib import contextmanager

from fastapi import HTTPException

import config
from db.database import get_connection

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
    lease = None
    try:
        conn = get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM work_leases WHERE expires_at<?", (time.time(),))
            if (
                conn.execute("SELECT COUNT(*) FROM work_leases WHERE pool='utility'").fetchone()[0]
                >= 2
            ):
                raise HTTPException(429, "AI tools are busy. Please retry shortly.")
            lease = uuid.uuid4().hex
            conn.execute(
                "INSERT INTO work_leases VALUES(?,'utility',?)", (lease, time.time() + 180)
            )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        yield
    except RuntimeError as exc:
        raise HTTPException(
            502, "The AI provider could not complete this request. Please retry."
        ) from exc
    finally:
        try:
            if lease:
                with get_connection() as conn:
                    conn.execute("DELETE FROM work_leases WHERE id=?", (lease,))
        finally:
            _slots.release()
