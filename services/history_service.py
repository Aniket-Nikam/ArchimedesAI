"""
Research history persistence service.
Manages saving and retrieving research sessions per user.
"""
import json
import logging

from db.database import get_connection

logger = logging.getLogger(__name__)


def save_research_session(user_id, query, report_payload):
    """
    Saves a completed research session to the database.
    
    Args:
        user_id: The authenticated user's ID.
        query: The original search query string.
        report_payload: The full report dict (will be serialized to JSON).
    
    Returns:
        The ID of the newly created session.
    """
    conn = get_connection()
    cursor = conn.cursor()

    report_json = json.dumps(report_payload, default=str)

    cursor.execute(
        "INSERT INTO research_sessions (user_id, query, report_json) VALUES (?, ?, ?)",
        (user_id, query, report_json)
    )
    conn.commit()

    session_id = cursor.lastrowid
    logger.info(f"Research session saved: id={session_id}, user_id={user_id}, query='{query[:50]}'")
    return session_id


def get_user_history(user_id, limit=20):
    """
    Retrieves a user's research history, ordered by most recent first.
    
    Args:
        user_id: The authenticated user's ID.
        limit: Maximum number of sessions to return.
    
    Returns:
        A list of dicts with id, query, and created_at.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, query, created_at FROM research_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_session_by_id(session_id, user_id):
    """
    Retrieves a specific research session.
    Includes a user_id check for authorization — users can only access their own sessions.
    
    Args:
        session_id: The session ID to retrieve.
        user_id: The authenticated user's ID (for authorization).
    
    Returns:
        A dict with id, query, report (deserialized), and created_at.
        Returns None if not found or not owned by user.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, user_id, query, report_json, created_at FROM research_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    )
    row = cursor.fetchone()

    if row:
        result = dict(row)
        result["report"] = json.loads(result.pop("report_json"))
        return result
    return None


def delete_session(session_id, user_id):
    """
    Deletes a research session. Only the owning user can delete their sessions.
    
    Args:
        session_id: The session ID to delete.
        user_id: The authenticated user's ID (for authorization).
    
    Returns:
        True if a row was deleted, False otherwise.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM research_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    )
    conn.commit()

    deleted = cursor.rowcount > 0
    if deleted:
        logger.info(f"Research session deleted: id={session_id}, user_id={user_id}")
    return deleted
