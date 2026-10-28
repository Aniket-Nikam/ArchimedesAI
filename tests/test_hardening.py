import json
import random
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from conftest import register

import config
from db.database import close_connection, get_connection
from services import history_service, job_service, research_pipeline
from services.backups import backup_database, restore_database
from services.evidence import attach_evidence_ids, validate_findings


def wait_job(job, user):
    until = time.monotonic() + 5
    while time.monotonic() < until:
        state = job_service.get_job(job, user)
        if state["status"] not in {"queued", "running"}:
            return state
        time.sleep(0.02)
    raise AssertionError("Job did not finish")


def fake_pipeline(req, user, emit, checkpoint):
    emit("log", "Synthetic test progress")
    emit(
        "complete",
        {
            "query": req.query,
            "seminal": [],
            "total_crawled": 0,
            "ai_synthesis": {"overview": "Test fixture"},
        },
    )


def test_job_events_replay_without_duplicate_save(client, monkeypatch):
    user = register(client)
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(research_pipeline, "execute_pipeline", fake_pipeline)
    job = client.post("/api/research/jobs", json={"query": "test job replay"}).json()["job_id"]
    state = wait_job(job, user["id"])
    assert state["status"] == "complete"
    first = client.get(f"/api/research/jobs/{job}/events")
    second = client.get(f"/api/research/jobs/{job}/events")
    assert "complete" in first.text and first.text == second.text
    assert len(client.get("/api/history/").json()) == 1
    assert first.headers["x-accel-buffering"] == "no"


def test_expired_worker_lease_recovers_once(client, monkeypatch):
    user = register(client)
    monkeypatch.setattr(research_pipeline, "execute_pipeline", fake_pipeline)
    job = job_service.enqueue(user["id"], {"query": "recover interrupted job"})
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE research_jobs SET status='running',generation='old-worker',attempts=1,lease_until=0 WHERE id=?",
            (job,),
        )
    job_service.dispatch()
    assert wait_job(job, user["id"])["status"] == "complete"
    assert conn.execute("SELECT attempts FROM research_jobs WHERE id=?", (job,)).fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM research_sessions").fetchone()[0] == 1


def test_cancellation_terminates_owned_process(client):
    user = register(client)
    job = job_service.enqueue(user["id"], {"query": "cancel running work"})
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    job_service._children[job] = process
    try:
        state = job_service.cancel(job, user["id"])
        assert state["status"] == "cancelled"
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            process.kill()
        job_service._children.pop(job, None)


def test_shared_rate_limit_survives_process_boundary(client):
    code = """from starlette.requests import Request
from auth.rate_limit import limit_auth
from fastapi import HTTPException
request=Request({'type':'http','client':('cross-process-test',1)})
try:
 for _ in range(15): limit_auth(request)
 print('accepted')
except HTTPException as error:
 print(error.status_code)
"""
    for _ in range(2):
        assert (
            subprocess.check_output([sys.executable, "-c", code], text=True).strip() == "accepted"
        )
    assert subprocess.check_output([sys.executable, "-c", code], text=True).strip() == "429"


def test_backup_restore_large_history(client, tmp_path):
    user = register(client)
    conn = get_connection()
    with conn:
        conn.executemany(
            "INSERT INTO research_sessions(user_id,query,report_json) VALUES(?,?,?)",
            ((user["id"], f"record-{i}", "{}") for i in range(25000)),
        )
    snapshot = tmp_path / "snapshot.db"
    restored = tmp_path / "restored.db"
    backup_database(config.DATABASE_PATH, snapshot)
    restore_database(snapshot, restored)
    with sqlite3.connect(restored) as result:
        assert result.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert result.execute("SELECT COUNT(*) FROM research_sessions").fetchone()[0] == 25000
    assert len(client.get("/api/history/").json()) == 20


def test_corrupt_backup_is_rejected(client, tmp_path):
    backup = tmp_path / "bad.db"
    backup_database(config.DATABASE_PATH, backup)
    backup.write_bytes(backup.read_bytes() + b"tampered")
    try:
        restore_database(backup, tmp_path / "restore.db")
        raise AssertionError("Corruption accepted")
    except ValueError as error:
        assert "checksum" in str(error)


def test_concurrent_writes_preserve_every_record(client):
    user = register(client)

    def write_batch(batch):
        conn = get_connection()
        try:
            for i in range(50):
                title = f"batch-{batch}-{i}"
                with conn:
                    conn.execute(
                        "INSERT INTO bookmarks(user_id,paper_title,paper_json) VALUES(?,?,?)",
                        (user["id"], title, json.dumps({"title": title})),
                    )
        finally:
            close_connection()

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write_batch, range(8)))
    assert get_connection().execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0] == 400
    assert get_connection().execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_sqlite_full_rolls_back_without_filling_disk(tmp_path):
    with sqlite3.connect(tmp_path / "quota.db") as conn:
        conn.execute("CREATE TABLE sample(value BLOB)")
        pages = conn.execute("PRAGMA page_count").fetchone()[0]
        conn.execute(f"PRAGMA max_page_count={pages + 1}")
        try:
            with conn:
                conn.execute("INSERT INTO sample VALUES(?)", (b"x" * 1024 * 1024,))
            raise AssertionError("Expected virtual database quota failure")
        except sqlite3.OperationalError as error:
            assert error.sqlite_errorcode == sqlite3.SQLITE_FULL
        assert conn.execute("SELECT COUNT(*) FROM sample").fetchone()[0] == 0
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_storage_failure_is_actionable_not_internal_trace(client, monkeypatch):
    register(client)

    def fail():
        raise sqlite3.OperationalError("disk is full: private internal path")

    monkeypatch.setattr(history_service, "get_connection", fail)
    result = client.get("/api/history/")
    assert result.status_code == 503
    assert "private internal path" not in result.text


def test_oversized_json_rejected(client):
    register(client)
    result = client.post(
        "/api/bookmarks/",
        content=b"x" * (2 * 1024 * 1024 + 1),
        headers={"Content-Type": "application/json"},
    )
    assert result.status_code == 413


def test_adversarial_validation_corpus_does_not_create_accounts(client):
    corpus = [
        "' OR 1=1--",
        "<script>alert(1)</script>",
        "../etc/passwd",
        "a" * 1000,
        "\x00",
        "😀" * 20,
        "a b",
        "; DROP TABLE users;",
    ]
    for name in corpus:
        result = client.post(
            "/api/auth/register",
            json={"username": name, "email": "test@example.com", "password": "valid-password"},
        )
        assert result.status_code in {400, 422}, (name, result.status_code)
    assert get_connection().execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_unknown_citations_are_flagged_and_downgraded():
    papers = attach_evidence_ids([{"title": "Known paper"}])
    result = validate_findings(
        {
            "key_findings": [
                {"text": "A claim", "confidence": "HIGH", "sources": ["S1", "Invented source"]}
            ]
        },
        papers,
    )
    finding = result["key_findings"][0]
    assert finding["sources"] == ["Known paper"]
    assert finding["confidence"] == "LOW"
    assert finding["unverified_sources"] == ["Invented source"]
    assert result["evidence_review"]["unmatched_citations"] == 1


def test_seeded_malformed_body_corpus_has_no_server_errors(client):
    register(client)
    randomizer = random.Random(42)
    for _ in range(100):
        data = bytes(randomizer.randrange(256) for _ in range(randomizer.randrange(1, 300)))
        response = client.post(
            "/api/bookmarks/", content=data, headers={"Content-Type": "application/json"}
        )
        assert 400 <= response.status_code < 500
    for _ in range(100):
        data = bytes(randomizer.randrange(256) for _ in range(100))
        response = client.post(
            "/api/upload/", files={"file": ("malformed.pdf", data, "application/pdf")}
        )
        assert response.status_code == 400


def test_chunked_request_body_limit(client):
    register(client)

    def chunks():
        for _ in range(33):
            yield b"x" * 65536

    response = client.post(
        "/api/bookmarks/", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413


def test_security_headers_and_private_paths(client):
    response = client.get("/api/health")
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    for path in ("/.env", "/.git/config", "/data/secrets/nonexistent.dpapi"):
        assert client.get(path).status_code == 404


def test_additive_migrations_rollback_preserves_existing_research(client):
    user = register(client)
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO research_sessions(user_id,query,report_json) VALUES(?,?,?)",
            (user["id"], "preserved research", "{}"),
        )
    migrations = Path(__file__).resolve().parents[1] / "db/migrations"
    for name in ("005_provider_schedule", "004_utility_leases", "003_durable_jobs"):
        conn.executescript((migrations / f"{name}.down.sql").read_text())
    assert conn.execute("SELECT COUNT(*) FROM research_sessions").fetchone()[0] == 1
    for name in ("003_durable_jobs", "004_utility_leases", "005_provider_schedule"):
        conn.executescript((migrations / f"{name}.up.sql").read_text())
        conn.executescript((migrations / f"{name}.up.sql").read_text())
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
