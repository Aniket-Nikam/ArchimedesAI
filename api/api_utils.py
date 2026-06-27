"""
Resilient HTTP request utility with exponential backoff and rate limit awareness.
Used by all API clients to handle transient failures gracefully.
"""
import requests
import time
import logging

logger = logging.getLogger(__name__)


def resilient_request(url, max_retries=3, backoff_factor=1.0, timeout=12, headers=None):
    """
    Makes an HTTP GET request with retry logic and exponential backoff.
    
    - Retries on 429 (rate limit), 503 (service unavailable), and connection errors
    - Exponential backoff: 1s, 2s, 4s by default
    - Returns the Response object on success, or None on total failure
    """
    for attempt in range(max_retries):
        try:
            res = requests.get(url, timeout=timeout, headers=headers)
            
            # Success
            if res.status_code == 200:
                return res
            
            # Rate limited — wait and retry
            if res.status_code == 429:
                retry_after = int(res.headers.get("Retry-After", backoff_factor * (2 ** attempt)))
                logger.warning(f"Rate limited on {url[:80]}. Retrying in {retry_after}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_after)
                continue
            
            # Server error — retry with backoff
            if res.status_code in (500, 502, 503, 504):
                wait = backoff_factor * (2 ** attempt)
                logger.warning(f"Server error {res.status_code} on {url[:80]}. Retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            
            # Client error (4xx except 429) — don't retry
            if 400 <= res.status_code < 500:
                logger.warning(f"Client error {res.status_code} on {url[:80]}. Not retrying.")
                return res
            
            # Other status codes — return as-is
            return res
            
        except requests.exceptions.Timeout:
            wait = backoff_factor * (2 ** attempt)
            logger.warning(f"Timeout on {url[:80]}. Retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
        except requests.exceptions.ConnectionError:
            wait = backoff_factor * (2 ** attempt)
            logger.warning(f"Connection error on {url[:80]}. Retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
        except Exception as e:
            logger.error(f"Unexpected error on {url[:80]}: {e}")
            return None
    
    logger.error(f"All {max_retries} retries exhausted for {url[:80]}")
    return None
