"""Test-only environment bootstrapping; imported before the application."""

import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "tests"
ROOT.mkdir(parents=True, exist_ok=True)
DATA_DIR = tempfile.mkdtemp(prefix="run-", dir=ROOT)
os.environ["ARCHIMEDES_DATA_DIR"] = DATA_DIR
os.environ["GROQ_API_KEY"] = ""
