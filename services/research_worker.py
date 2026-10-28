"""Isolated worker entry point. Persistent state is the database, not this process."""

import sys

from services.job_service import run_worker

if __name__ == "__main__":
    run_worker(sys.argv[1], sys.argv[2])
