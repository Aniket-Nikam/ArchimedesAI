"""Consistent SQLite snapshots; restoration always targets a new database file."""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def backup_database(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.exists():
        raise ValueError("Choose a new backup filename.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as src:
        with sqlite3.connect(destination) as target:
            src.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Backup integrity check failed.")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(destination.suffix + ".json").write_text(
        json.dumps({"sha256": digest, "created_at": datetime.now(UTC).isoformat()}, indent=2),
        encoding="utf-8",
    )
    return digest


def restore_database(backup, destination):
    backup, destination = Path(backup).resolve(), Path(destination).resolve()
    expected = json.loads(backup.with_suffix(backup.suffix + ".json").read_text())["sha256"]
    if hashlib.sha256(backup.read_bytes()).hexdigest() != expected:
        raise ValueError("Backup checksum mismatch.")
    return backup_database(backup, destination)
