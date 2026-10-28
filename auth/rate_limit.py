"""Atomic shared-window rate limiting across processes using the application DB."""

import hashlib
import time

from fastapi import HTTPException, Request

from db.database import get_connection


def limit_auth(request: Request):
    host = request.client.host if request.client else "unknown"
    bucket = hashlib.sha256(("auth:" + host).encode()).hexdigest()
    now = time.time()
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM rate_limit_events WHERE at<?", (now - 600,))
        count = conn.execute(
            "SELECT COUNT(*) FROM rate_limit_events WHERE bucket=?", (bucket,)
        ).fetchone()[0]
        if count >= 30:
            raise HTTPException(
                429,
                "Too many sign-in attempts. Try again in ten minutes.",
                headers={"Retry-After": "600"},
            )
        conn.execute("INSERT INTO rate_limit_events(bucket,at) VALUES(?,?)", (bucket, now))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
