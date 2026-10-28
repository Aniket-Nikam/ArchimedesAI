import _environment
import pytest
from fastapi.testclient import TestClient

import config
from db.database import close_connection, get_connection
from main import app

assert config.DATABASE_DIR == _environment.DATA_DIR


@pytest.fixture(autouse=True)
def clean_db(monkeypatch):
    from auth.rate_limit import _attempts

    _attempts.clear()
    monkeypatch.setattr(config, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(config, "GROQ_API_KEY", None)
    conn = get_connection()
    with conn:
        for table in (
            "auth_sessions",
            "research_sessions",
            "bookmarks",
            "projects",
            "users",
            "api_cache",
        ):
            conn.execute(f"DELETE FROM {table}")
    yield
    close_connection()


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def register(client, username="alice"):
    result = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "test-password-123",
        },
    )
    assert result.status_code == 200, result.text
    data = result.json()
    client.headers["X-CSRF-Token"] = data["csrf_token"]
    return data["user"]
