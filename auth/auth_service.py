"""
Authentication service for Archimedes.
Handles user registration, login, and password security using bcrypt.
"""

import logging
import re
import sqlite3

import bcrypt

import config
from db.database import get_connection

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when authentication or validation fails."""

    pass


def _validate_username(username):
    """Validates username format and length."""
    if not username or not isinstance(username, str):
        raise AuthError("Username is required.")
    username = username.strip()
    if len(username) < config.USERNAME_MIN_LENGTH:
        raise AuthError(f"Username must be at least {config.USERNAME_MIN_LENGTH} characters.")
    if len(username) > config.USERNAME_MAX_LENGTH:
        raise AuthError(f"Username must be at most {config.USERNAME_MAX_LENGTH} characters.")
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        raise AuthError("Username can only contain letters, numbers, and underscores.")
    return username


def _validate_email(email):
    """Validates email format."""
    if not email or not isinstance(email, str):
        raise AuthError("Email is required.")
    email = email.strip().lower()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise AuthError("Please enter a valid email address.")
    return email


def _validate_password(password):
    """Validates password strength."""
    if not password or not isinstance(password, str):
        raise AuthError("Password is required.")
    if len(password) < config.PASSWORD_MIN_LENGTH:
        raise AuthError(f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters.")
    if len(password.encode("utf-8")) > 72:
        raise AuthError("Password must be at most 72 bytes.")
    return password


def hash_password(password):
    """
    Hashes a password using bcrypt with configurable rounds.
    Returns the hash as a UTF-8 string for database storage.
    """
    salt = bcrypt.gensalt(rounds=config.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password, password_hash):
    """
    Verifies a password against its bcrypt hash.
    Uses constant-time comparison to prevent timing attacks.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def register_user(username, email, password):
    """
    Registers a new user.
    Returns the user dict on success.
    Raises AuthError on validation failure or duplicate user.
    """
    username = _validate_username(username)
    email = _validate_email(email)
    _validate_password(password)

    conn = get_connection()
    cursor = conn.cursor()

    # Check for existing username
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        raise AuthError("This username is already taken.")

    # Check for existing email
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        raise AuthError("An account with this email already exists.")

    # Hash and store
    pw_hash = hash_password(password)
    try:
        with conn:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, pw_hash),
            )
    except sqlite3.IntegrityError as exc:
        raise AuthError("Username or email is already in use.") from exc

    user_id = cursor.lastrowid
    logger.info(f"User registered successfully: {username} (id={user_id})")

    return {"id": user_id, "username": username, "email": email}


def login_user(username, password):
    """
    Authenticates a user by username and password.
    Returns the user dict on success.
    Raises AuthError on failure (generic message to prevent enumeration).
    """
    if not username or not password:
        raise AuthError("Username and password are required.")

    username = username.strip()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, email, password_hash FROM users WHERE username = ?", (username,)
    )
    row = cursor.fetchone()

    if not row:
        # Generic error to prevent username enumeration
        raise AuthError("Invalid username or password.")

    if not verify_password(password, row["password_hash"]):
        raise AuthError("Invalid username or password.")

    logger.info(f"User logged in: {row['username']} (id={row['id']})")
    return {"id": row["id"], "username": row["username"], "email": row["email"]}


def get_user_by_id(user_id):
    """Fetches a user by their ID. Returns None if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None
