"""
Bookmark service for saving and managing paper bookmarks per user.
"""
import json
import logging
from db.database import get_connection

logger = logging.getLogger(__name__)


def add_bookmark(user_id, paper, notes=""):
    """Save a paper to the user's bookmarks."""
    conn = get_connection()
    cursor = conn.cursor()
    paper_json = json.dumps(paper, default=str)
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO bookmarks (user_id, paper_title, paper_json, notes) VALUES (?, ?, ?, ?)",
            (user_id, paper.get("title", ""), paper_json, notes)
        )
        conn.commit()
        logger.info(f"Bookmark added: user={user_id}, paper='{paper.get('title', '')[:40]}'")
        return True
    except Exception as e:
        logger.error(f"Error adding bookmark: {e}")
        return False


def remove_bookmark(user_id, paper_title):
    """Remove a paper from the user's bookmarks."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM bookmarks WHERE user_id = ? AND paper_title = ?",
        (user_id, paper_title)
    )
    conn.commit()
    return cursor.rowcount > 0


def get_bookmarks(user_id):
    """Get all bookmarks for a user, newest first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, paper_title, paper_json, notes, created_at FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["paper"] = json.loads(item.pop("paper_json"))
        result.append(item)
    return result


def is_bookmarked(user_id, paper_title):
    """Check if a paper is bookmarked by the user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM bookmarks WHERE user_id = ? AND paper_title = ?",
        (user_id, paper_title)
    )
    return cursor.fetchone() is not None


def update_bookmark_notes(user_id, paper_title, notes):
    """Update the notes on a bookmark."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bookmarks SET notes = ? WHERE user_id = ? AND paper_title = ?",
        (notes, user_id, paper_title)
    )
    conn.commit()
    return cursor.rowcount > 0
