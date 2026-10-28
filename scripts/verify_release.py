"""Reproduce the release checks and retain portable, machine-readable evidence."""

import json
import platform
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "test-results"
OUTPUT.mkdir(parents=True, exist_ok=True)
NPM = shutil.which("npm.cmd") or shutil.which("npm")
if not NPM:
    raise SystemExit("npm is required")
checks = []


def redact(text):
    return text.replace(str(ROOT), "<repository>").replace(str(Path.home()), "<user-home>")


def run(name, args, cwd=ROOT):
    start = time.monotonic()
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = round(time.monotonic() - start, 3)
    (OUTPUT / f"{name}.log").write_text(redact(result.stdout).rstrip() + "\n", encoding="utf-8")
    checks.append({"name": name, "exit_code": result.returncode, "elapsed_seconds": elapsed})
    print(f"{name}: {'PASS' if result.returncode == 0 else 'FAIL'} ({elapsed}s)", flush=True)


for number in range(1, 4):
    xml = ROOT / "data" / f"backend-run-{number}.xml"
    run(
        f"backend-run-{number}",
        [sys.executable, "-m", "pytest", "-q", f"--junitxml={xml}", "--durations=10"],
    )
    if xml.exists():
        tree = ET.parse(xml)
        for element in tree.iter():
            element.attrib.pop("hostname", None)
            for key, value in list(element.attrib.items()):
                element.set(key, redact(value))
            if element.text:
                element.text = redact(element.text)
        tree.write(OUTPUT / f"backend-run-{number}.xml", encoding="utf-8", xml_declaration=True)
for name, command in (
    ("python-lint", ["-m", "ruff", "check"]),
    ("python-format", ["-m", "ruff", "format", "--check"]),
):
    run(
        name,
        [
            sys.executable,
            *command,
            "auth",
            "api",
            "ai",
            "db",
            "routers",
            "services",
            "utils",
            "main.py",
            "tests",
            "scripts",
        ],
    )
run("dependencies", [sys.executable, "-m", "pip", "check"])
for name, task in (
    ("frontend-tests", "test"),
    ("frontend-lint", "lint"),
    ("frontend-build", "build"),
):
    run(name, [NPM, "run", task], ROOT / "frontend")
summary = {
    "executed_at_utc": datetime.now(UTC).isoformat(),
    "source_base_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip(),
    "working_tree_note": "Any tested working-tree changes are included in the report commit; the base SHA precedes those changes.",
    "python": platform.python_version(),
    "node": subprocess.check_output(["node", "--version"], text=True).strip(),
    "platform": platform.system(),
    "checks": checks,
    "all_checks_passed": all(check["exit_code"] == 0 for check in checks),
    "provider_note": "Backend tests stub academic and AI providers; no live Groq calls.",
}
(OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
raise SystemExit(0 if summary["all_checks_passed"] else 1)
