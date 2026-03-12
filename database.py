"""Database layer — SQLite with encrypted API key storage."""
import os
import sqlite3
import time
from cryptography.fernet import Fernet

from config import ENCRYPTION_KEY, DATABASE_PATH

# ── Encryption ──────────────────────────────────────────────
_fernet = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None


def encrypt_key(api_key: str) -> str:
    """Encrypt an API key for storage."""
    if not _fernet:
        raise RuntimeError("ENCRYPTION_KEY not configured")
    return _fernet.encrypt(api_key.encode()).decode()


def decrypt_key(encrypted: str) -> str:
    """Decrypt a stored API key."""
    if not _fernet:
        raise RuntimeError("ENCRYPTION_KEY not configured")
    return _fernet.decrypt(encrypted.encode()).decode()


# ── Database Init ───────────────────────────────────────────

def init_db():
    """Create tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            picture TEXT,
            encrypted_api_key TEXT,
            theme_preference TEXT DEFAULT 'light',
            has_seen_tutorial INTEGER DEFAULT 0,
            created_at REAL
        )
    """)
    conn.commit()
    conn.close()


# ── User Operations ─────────────────────────────────────────

def get_or_create_user(email: str, name: str = None, picture: str = None) -> dict:
    """Get existing user or create a new one. Returns user dict."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row:
        # Update name/picture from Google in case they changed
        conn.execute(
            "UPDATE users SET name = ?, picture = ? WHERE email = ?",
            (name or row["name"], picture or row["picture"], email),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        user = dict(row)
    else:
        conn.execute(
            "INSERT INTO users (email, name, picture, created_at) VALUES (?, ?, ?, ?)",
            (email, name, picture, time.time()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        user = dict(row)

    conn.close()
    return user


def save_api_key(user_id: int, api_key: str):
    """Encrypt and store a user's Claude API key."""
    encrypted = encrypt_key(api_key)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute(
        "UPDATE users SET encrypted_api_key = ? WHERE id = ?",
        (encrypted, user_id),
    )
    conn.commit()
    conn.close()


def get_api_key(user_id: int) -> str | None:
    """Retrieve and decrypt a user's Claude API key. Returns None if not set."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT encrypted_api_key FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row and row["encrypted_api_key"]:
        return decrypt_key(row["encrypted_api_key"])
    return None


def has_api_key(user_id: int) -> bool:
    """Check if user has a stored API key."""
    conn = sqlite3.connect(DATABASE_PATH)
    row = conn.execute(
        "SELECT encrypted_api_key FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return bool(row and row[0])


def get_user_by_id(user_id: int) -> dict | None:
    """Get user by ID."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_theme(user_id: int, theme: str):
    """Save user's theme preference."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute(
        "UPDATE users SET theme_preference = ? WHERE id = ?",
        (theme, user_id),
    )
    conn.commit()
    conn.close()


def mark_tutorial_seen(user_id: int):
    """Mark that user has completed the tutorial."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute(
        "UPDATE users SET has_seen_tutorial = 1 WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
