"""Opaque, revocable browser sessions. Store hashes, never the session secret."""

import hashlib
import secrets
import time

from fastapi import Depends, HTTPException, Request, Response

import config
from db.database import get_connection

COOKIE = "archimedes_session"


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(user: dict, response: Response, request: Request) -> str:
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    now = int(time.time())
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
        previous = request.cookies.get(COOKIE)
        if previous:
            conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (_digest(previous),))
        conn.execute(
            "DELETE FROM auth_sessions WHERE user_id = ? AND token_hash NOT IN (SELECT token_hash FROM auth_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 4)",
            (user["id"], user["id"]),
        )
        conn.execute(
            "INSERT INTO auth_sessions VALUES (?, ?, ?, ?, ?)",
            (_digest(token), user["id"], csrf, now + config.SESSION_TTL_SECONDS, now),
        )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=config.SESSION_TTL_SECONDS,
        path="/",
    )
    return csrf


def require_session(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Sign in to continue.")
    row = (
        get_connection()
        .execute(
            "SELECT u.id, u.username, u.email, s.csrf_token FROM auth_sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ?",
            (_digest(token), int(time.time())),
        )
        .fetchone()
    )
    if row is None:
        raise HTTPException(401, "Your session expired. Please sign in again.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        supplied = request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(supplied, row["csrf_token"]):
            raise HTTPException(403, "Invalid request token. Refresh and try again.")
    return dict(row)


def current_user_id(user: dict = Depends(require_session)) -> int:
    return user["id"]


def end_session(request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        conn = get_connection()
        with conn:
            conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (_digest(token),))
    response.delete_cookie(
        COOKIE, path="/", secure=config.COOKIE_SECURE, httponly=True, samesite="lax"
    )
