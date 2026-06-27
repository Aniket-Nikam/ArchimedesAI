"""
API response caching service using SQLite.
Caches search results with a 24-hour TTL to avoid redundant API calls.
"""
import json
import hashlib
import logging
from datetime import datetime, timedelta

from db.database import get_connection

logger = logging.getLogger(__name__)

CACHE_TTL_HOURS = 24


def _hash_query(query, source):
    """Generate a deterministic hash for a query + source combination."""
    key = f"{source}::{query.strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()


def get_cached(query, source):
    """
    Retrieve cached results for a query + source.
    Returns the deserialized list of papers, or None if not cached / stale.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query_hash = _hash_query(query, source)
        
        cursor.execute(
            "SELECT results_json, created_at FROM api_cache WHERE query_hash = ? AND source = ?",
            (query_hash, source)
        )
        row = cursor.fetchone()
        
        if row:
            created_at = datetime.fromisoformat(row["created_at"])
            if datetime.utcnow() - created_at < timedelta(hours=CACHE_TTL_HOURS):
                logger.info(f"Cache HIT for {source}: '{query[:40]}...'")
                return json.loads(row["results_json"])
            else:
                # Stale — delete it
                cursor.execute(
                    "DELETE FROM api_cache WHERE query_hash = ? AND source = ?",
                    (query_hash, source)
                )
                conn.commit()
                logger.info(f"Cache STALE for {source}: '{query[:40]}...'")
        
        return None
    except Exception as e:
        logger.error(f"Cache read error: {e}")
        return None


def set_cached(query, source, results):
    """
    Store search results in the cache.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query_hash = _hash_query(query, source)
        results_json = json.dumps(results, default=str)
        
        cursor.execute(
            """INSERT OR REPLACE INTO api_cache (query_hash, source, results_json, created_at)
               VALUES (?, ?, ?, ?)""",
            (query_hash, source, results_json, datetime.utcnow().isoformat())
        )
        conn.commit()
        logger.info(f"Cache SET for {source}: '{query[:40]}...' ({len(results)} results)")
    except Exception as e:
        logger.error(f"Cache write error: {e}")


def cleanup_stale():
    """Remove all cache entries older than TTL."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS)).isoformat()
        cursor.execute("DELETE FROM api_cache WHERE created_at < ?", (cutoff,))
        deleted = cursor.rowcount
        conn.commit()
        if deleted:
            logger.info(f"Cache cleanup: removed {deleted} stale entries")
    except Exception as e:
        logger.error(f"Cache cleanup error: {e}")
