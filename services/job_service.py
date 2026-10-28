"""SQLite-backed admission, resumable event streams and isolated worker processes."""

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import HTTPException

import config
from db.database import close_connection, get_connection
from services import research_pipeline

INLINE_TESTING = False
_children = {}
_children_lock = threading.Lock()
_dispatcher_lock = threading.Lock()


def enqueue(user_id, payload):
    conn = get_connection()
    now = time.time()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute(
            "SELECT 1 FROM research_jobs WHERE user_id=? AND status IN ('queued','running')",
            (user_id,),
        ).fetchone():
            raise HTTPException(409, "A research job is already running for your account.")
        count = conn.execute(
            "SELECT COUNT(*) FROM research_jobs WHERE status IN ('queued','running')"
        ).fetchone()[0]
        if count >= config.MAX_CONCURRENT_RESEARCH:
            raise HTTPException(
                429,
                "Research capacity is full. Please retry shortly.",
                headers={"Retry-After": "10"},
            )
        job = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO research_jobs(id,user_id,request_json,status,deadline,created_at,updated_at) VALUES(?,?,?,'queued',?,?,?)",
            (job, user_id, json.dumps(payload), now + config.RESEARCH_TIMEOUT_SECONDS, now, now),
        )
        conn.commit()
        return job
    except BaseException:
        conn.rollback()
        raise


def get_job(job_id, user_id):
    row = (
        get_connection()
        .execute(
            "SELECT id,status,session_id,error,created_at,updated_at,request_json FROM research_jobs WHERE id=? AND user_id=?",
            (job_id, user_id),
        )
        .fetchone()
    )
    if not row:
        raise HTTPException(404, "Research job not found.")
    result = dict(row)
    if result["error"]:
        result["error"] = "Research could not finish. Review the progress messages or retry."
    result["query"] = json.loads(result.pop("request_json"))["query"]
    return result


def append_event(conn, job, kind, data):
    conn.execute(
        "INSERT INTO research_job_events(job_id,payload,created_at) VALUES(?,?,?)",
        (job, json.dumps({"type": kind, "data": data}), time.time()),
    )


def cancel(job_id, user_id):
    conn = get_connection()
    with conn:
        cursor = conn.execute(
            "UPDATE research_jobs SET status='cancelled',updated_at=? WHERE id=? AND user_id=? AND status IN ('queued','running')",
            (time.time(), job_id, user_id),
        )
        if cursor.rowcount:
            append_event(conn, job_id, "error", "Research cancelled. No further stages will run.")
    get_job(job_id, user_id)
    with _children_lock:
        process = _children.get(job_id)
    # Only terminate a process handle launched by this server, never an arbitrary PID.
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
    return get_job(job_id, user_id)


def dispatch():
    if not _dispatcher_lock.acquire(blocking=False):
        return
    try:
        conn = get_connection()
        now = time.time()
        with conn:
            expired = conn.execute(
                "SELECT id FROM research_jobs WHERE status IN ('queued','running') AND deadline<=?",
                (now,),
            ).fetchall()
            for row in expired:
                conn.execute(
                    "UPDATE research_jobs SET status='error',error='Research deadline exceeded',updated_at=? WHERE id=?",
                    (now, row["id"]),
                )
                append_event(
                    conn, row["id"], "error", "Research timed out. Try a narrower question."
                )
            conn.execute(
                "UPDATE research_jobs SET status='queued' WHERE status='running' AND lease_until<? AND deadline>? AND attempts<3",
                (now, now),
            )
            exhausted = conn.execute(
                "SELECT id FROM research_jobs WHERE status='running' AND lease_until<? AND attempts>=3",
                (now,),
            ).fetchall()
            for row in exhausted:
                conn.execute(
                    "UPDATE research_jobs SET status='error',error='Worker recovery exhausted',updated_at=? WHERE id=?",
                    (now, row["id"]),
                )
                append_event(
                    conn, row["id"], "error", "Research was interrupted repeatedly. Please retry."
                )
        for row in conn.execute(
            "SELECT id FROM research_jobs WHERE status='queued' ORDER BY created_at"
        ).fetchall():
            generation = uuid.uuid4().hex
            with conn:
                claimed = conn.execute(
                    "UPDATE research_jobs SET status='running',generation=?,lease_until=?,attempts=attempts+1 WHERE id=? AND status='queued'",
                    (generation, time.time() + 15, row["id"]),
                ).rowcount
            if not claimed:
                continue
            if INLINE_TESTING:
                threading.Thread(
                    target=run_worker, args=(row["id"], generation, False), daemon=True
                ).start()
            else:
                try:
                    process = subprocess.Popen(
                        [sys.executable, "-m", "services.research_worker", row["id"], generation],
                        cwd=Path(__file__).resolve().parents[1],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                    with _children_lock:
                        _children[row["id"]] = process
                except OSError:
                    with conn:
                        conn.execute(
                            "UPDATE research_jobs SET status='error',error='Could not start worker' WHERE id=?",
                            (row["id"],),
                        )
                        append_event(conn, row["id"], "error", "Research worker could not start.")
        with _children_lock:
            for job, process in list(_children.items()):
                if process.poll() is not None:
                    del _children[job]
    finally:
        _dispatcher_lock.release()


def run_worker(job, generation, hard_exit=True):
    from routers.research_router import ResearchRequest

    stopped = threading.Event()
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM research_jobs WHERE id=? AND generation=?", (job, generation)
    ).fetchone()
    if not row:
        return
    req = ResearchRequest.model_validate_json(row["request_json"])
    user_id = row["user_id"]
    terminal = False

    def checkpoint():
        state = (
            get_connection()
            .execute("SELECT status,generation,deadline FROM research_jobs WHERE id=?", (job,))
            .fetchone()
        )
        if not state or state["generation"] != generation or state["status"] != "running":
            raise InterruptedError("Research stopped.")
        if state["deadline"] <= time.time():
            raise TimeoutError("Research timed out. Try a narrower question.")

    def monitor():
        while not stopped.wait(0.4):
            try:
                checkpoint()
                db = get_connection()
                with db:
                    db.execute(
                        "UPDATE research_jobs SET lease_until=?,updated_at=? WHERE id=? AND generation=? AND status='running'",
                        (time.time() + 15, time.time(), job, generation),
                    )
            except (InterruptedError, TimeoutError):
                if hard_exit:
                    os._exit(0)
                return
        close_connection()

    def emit(kind, data):
        nonlocal terminal
        checkpoint()
        db = get_connection()
        with db:
            # Recheck under a write lock so cancellation cannot race a saved report.
            db.execute("UPDATE research_jobs SET updated_at=updated_at WHERE id=?", (job,))
            checkpoint()
            if kind in {"complete", "followup_complete"}:
                if kind == "complete":
                    cursor = db.execute(
                        "INSERT INTO research_sessions(user_id,query,report_json) VALUES(?,?,?)",
                        (user_id, req.query, json.dumps(data)),
                    )
                    data["session_id"] = cursor.lastrowid
                    db.execute(
                        "UPDATE research_jobs SET session_id=? WHERE id=?", (cursor.lastrowid, job)
                    )
                db.execute(
                    "UPDATE research_jobs SET status='complete',updated_at=? WHERE id=?",
                    (time.time(), job),
                )
                terminal = True
            append_event(db, job, kind, data)

    threading.Thread(target=monitor, daemon=True).start()
    try:
        research_pipeline.execute_pipeline(req, user_id, emit, checkpoint)
        if not terminal:
            raise RuntimeError("Worker returned without a result.")
    except InterruptedError:
        pass
    except Exception as exc:
        db = get_connection()
        with db:
            updated = db.execute(
                "UPDATE research_jobs SET status='error',error=?,updated_at=? WHERE id=? AND generation=? AND status='running'",
                ((type(exc).__name__ + ": " + str(exc))[:500], time.time(), job, generation),
            ).rowcount
            if updated:
                append_event(
                    db,
                    job,
                    "error",
                    str(exc)
                    if isinstance(exc, (ValueError, TimeoutError))
                    else "Research could not finish. Please retry or check provider availability.",
                )
    finally:
        stopped.set()
        close_connection()
