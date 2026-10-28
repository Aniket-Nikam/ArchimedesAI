"""Offline/local operations: create a snapshot or restore into a NEW data directory."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.backups import backup_database, restore_database

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["backup", "restore"])
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    digest = (backup_database if args.operation == "backup" else restore_database)(
        args.source, args.destination
    )
    print("Snapshot verified:", digest)
