"""HTTP retries with finite timeouts and capped backoff."""

import logging
import threading
import time
from urllib.parse import urlsplit

import requests

from db.database import get_connection

logger = logging.getLogger(__name__)
_observations = threading.local()


def begin_observation():
    _observations.events = []


def observations():
    return list(getattr(_observations, "events", []))


def pace(host):
    interval = {
        "api.semanticscholar.org": 1.1,
        "export.arxiv.org": 3.1,
        "eutils.ncbi.nlm.nih.gov": 0.35,
    }.get(host)
    if not interval:
        return
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT next_at FROM provider_schedule WHERE host=?", (host,)).fetchone()
        reserved = max(time.time(), row[0] if row else 0)
        conn.execute(
            "INSERT INTO provider_schedule VALUES(?,?) ON CONFLICT(host) DO UPDATE SET next_at=excluded.next_at",
            (host, reserved + interval),
        )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    time.sleep(max(0, reserved - time.time()))


def resilient_request(url, max_retries=2, backoff_factor=1.0, timeout=10, headers=None):
    host = urlsplit(url).netloc
    for attempt in range(max_retries):
        pace(host)
        wait = min(5.0, backoff_factor * 2**attempt)
        try:
            started = time.monotonic()
            response = requests.get(url, timeout=timeout, headers=headers)
            if hasattr(_observations, "events"):
                _observations.events.append(
                    {
                        "host": host,
                        "status": response.status_code,
                        "seconds": round(time.monotonic() - started, 3),
                    }
                )
            if response.status_code not in {429, 500, 502, 503, 504}:
                return response
            try:
                wait = max(0.0, min(5.0, float(response.headers.get("Retry-After", wait))))
            except (ValueError, TypeError):
                pass
            response.close()
        except requests.RequestException:
            if hasattr(_observations, "events"):
                _observations.events.append({"host": host, "status": "network_error"})
            logger.warning("Academic request failed: %s (attempt %s)", host, attempt + 1)
        if attempt + 1 < max_retries:
            time.sleep(wait)
    return None
