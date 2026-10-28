"""
Project/workspace service for organizing research sessions.
"""

import logging

from db.database import get_connection

logger = logging.getLogger(__name__)


def create_project(user_id, name, description=""):
    """Create a new research project."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (user_id, name, description) VALUES (?, ?, ?)",
        (user_id, name, description),
    )
    conn.commit()
    project_id = cursor.lastrowid
    logger.info(f"Project created: id={project_id}, user={user_id}, name='{name}'")
    return project_id


def get_projects(user_id):
    """Get all projects for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT p.id, p.name, p.description, p.created_at, COUNT(s.id) AS session_count
           FROM projects p LEFT JOIN research_sessions s
             ON s.project_id = p.id AND s.user_id = p.user_id
           WHERE p.user_id = ? GROUP BY p.id ORDER BY p.created_at DESC, p.id DESC""",
        (user_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def update_project(user_id, project_id, name=None, description=None):
    """Update a project's name or description."""
    conn = get_connection()
    cursor = conn.cursor()
    if name is not None:
        cursor.execute(
            "UPDATE projects SET name = ? WHERE id = ? AND user_id = ?", (name, project_id, user_id)
        )
    if description is not None:
        cursor.execute(
            "UPDATE projects SET description = ? WHERE id = ? AND user_id = ?",
            (description, project_id, user_id),
        )
    conn.commit()
    return cursor.rowcount > 0


def delete_project(user_id, project_id):
    """Delete a project (sessions remain, just unlinked)."""
    conn = get_connection()
    cursor = conn.cursor()
    # Unlink sessions first
    cursor.execute(
        "UPDATE research_sessions SET project_id = NULL WHERE project_id = ? AND user_id = ?",
        (project_id, user_id),
    )
    cursor.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id))
    conn.commit()
    return cursor.rowcount > 0


def assign_session_to_project(user_id, session_id, project_id):
    """Assign a research session to a project."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE research_sessions SET project_id = ? WHERE id = ? AND user_id = ? AND EXISTS (SELECT 1 FROM projects WHERE id = ? AND user_id = ?)",
        (project_id, session_id, user_id, project_id, user_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def get_project_sessions(user_id, project_id):
    """Get all sessions in a project."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, query, created_at FROM research_sessions WHERE project_id = ? AND user_id = ? ORDER BY created_at DESC",
        (project_id, user_id),
    )
    return [dict(row) for row in cursor.fetchall()]
