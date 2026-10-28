"""HTTP retries with finite timeouts and capped backoff."""

import logging
import time
from urllib.parse import urlsplit

import requests

logger = logging.getLogger(__name__)


def resilient_request(url, max_retries=2, backoff_factor=1.0, timeout=10, headers=None):
    host = urlsplit(url).netloc
    for attempt in range(max_retries):
        wait = min(5.0, backoff_factor * 2**attempt)
        try:
            response = requests.get(url, timeout=timeout, headers=headers)
            if response.status_code not in {429, 500, 502, 503, 504}:
                return response
            try:
                wait = max(0.0, min(5.0, float(response.headers.get("Retry-After", wait))))
            except (ValueError, TypeError):
                pass
            response.close()
        except requests.RequestException:
            logger.warning("Academic request failed: %s (attempt %s)", host, attempt + 1)
        if attempt + 1 < max_retries:
            time.sleep(wait)
    return None
