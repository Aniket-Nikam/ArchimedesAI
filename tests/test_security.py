from pathlib import Path

from conftest import register
from fastapi.testclient import TestClient

from db.database import get_connection
from main import app
from services.history_service import save_research_session
from services.project_service import create_project


def test_protected_routes_require_session(client):
    assert client.get("/api/history/?user_id=1").status_code == 401
    assert client.post("/api/research/", json={"query": "test", "user_id": 1}).status_code == 401
    assert client.get("/api/bookmarks/?user_id=1").status_code == 401


def test_csrf_and_logout_revocation(client):
    register(client)
    cookie = client.cookies.get("archimedes_session")
    session = client.get("/api/auth/session")
    assert session.json()["csrf_token"] == client.headers["X-CSRF-Token"]
    del client.headers["X-CSRF-Token"]
    assert client.post("/api/bookmarks/", json={"paper": {"title": "Paper"}}).status_code == 403
    client.headers["X-CSRF-Token"] = session.json()["csrf_token"]
    assert client.post("/api/auth/logout").status_code == 200
    client.cookies.set("archimedes_session", cookie)
    assert client.get("/api/auth/session").status_code == 401


def test_caller_cannot_impersonate_other_user(client):
    alice = register(client)
    session_id = save_research_session(alice["id"], "Alice private research", {"seminal": []})
    project_id = create_project(alice["id"], "Alice private project")
    with TestClient(app) as bob:
        user = register(bob, "bob")
        assert bob.get(f"/api/history/?user_id={alice['id']}").json() == []
        assert bob.get(f"/api/history/{session_id}?user_id={alice['id']}").status_code == 404
        assert (
            bob.post(
                "/api/export/",
                json={"session_id": session_id, "user_id": alice["id"], "format": "csv"},
            ).status_code
            == 404
        )
        result = bob.post(
            "/api/bookmarks/", json={"user_id": alice["id"], "paper": {"title": "Bob bookmark"}}
        )
        assert result.status_code == 200
        assert client.get("/api/bookmarks/").json() == []
        own_session = save_research_session(user["id"], "Bob research", {})
        result = bob.post(
            "/api/projects/assign",
            json={"session_id": own_session, "project_id": project_id, "user_id": alice["id"]},
        )
        assert result.status_code == 404
        assert (
            get_connection()
            .execute("SELECT project_id FROM research_sessions WHERE id=?", (own_session,))
            .fetchone()[0]
            is None
        )


def test_session_secret_is_hashed_and_expires(client):
    register(client)
    conn = get_connection()
    row = conn.execute("SELECT token_hash FROM auth_sessions").fetchone()
    assert row[0] != client.cookies.get("archimedes_session")
    with conn:
        conn.execute("UPDATE auth_sessions SET expires_at = 0")
    assert client.get("/api/auth/session").status_code == 401


def test_origin_and_multibyte_password_validation(client):
    payload = {"username": "alice", "email": "alice@example.com", "password": "test-password"}
    assert (
        client.post(
            "/api/auth/register", json=payload, headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )
    payload["password"] = "é" * 40
    assert client.post("/api/auth/register", json=payload).status_code == 400


def test_session_migration_reversible_preserves_users(client):
    register(client)
    conn = get_connection()
    directory = Path(__file__).resolve().parents[1] / "db/migrations"
    conn.executescript((directory / "001_sessions.down.sql").read_text())
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    conn.executescript((directory / "001_sessions.up.sql").read_text())
    conn.executescript((directory / "001_sessions.up.sql").read_text())
    assert conn.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0] == 0
