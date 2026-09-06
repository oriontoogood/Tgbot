# ─────────────────────────────────────────────
#  DATABASE — handles all SQLite operations
# ─────────────────────────────────────────────
import sqlite3
import os
from config import DB_FILE


def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS messages ("
        "id          INTEGER PRIMARY KEY AUTOINCREMENT,"
        "timestamp   TEXT    NOT NULL,"
        "chat_id     INTEGER NOT NULL,"
        "user_id     INTEGER,"
        "username    TEXT,"
        "full_name   TEXT,"
        "message_id  INTEGER,"
        "text        TEXT,"
        "media_type  TEXT,"
        "media_path  TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS user_filters ("
        "user_id    INTEGER PRIMARY KEY,"
        "username   TEXT,"
        "list_type  TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()


def save_message(timestamp, chat_id, user_id, username, full_name, message_id, text, media_type, media_path=None):
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO messages (timestamp, chat_id, user_id, username, full_name, message_id, text, media_type, media_path)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (timestamp, chat_id, user_id, username, full_name, message_id, text, media_type, media_path),
    )
    conn.commit()
    conn.close()


def get_stats():
    conn = sqlite3.connect(DB_FILE)
    total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    by_type = conn.execute(
        "SELECT media_type, COUNT(*) FROM messages GROUP BY media_type ORDER BY COUNT(*) DESC"
    ).fetchall()
    unique_users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM messages").fetchone()[0]
    today = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE DATE(timestamp) = DATE('now')"
    ).fetchone()[0]
    conn.close()
    return {"total": total, "by_type": by_type, "unique_users": unique_users, "today": today}


def get_filter_lists():
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute("SELECT user_id, list_type FROM user_filters").fetchall()
    conn.close()
    return rows


def add_user_filter(user_id, username, list_type):
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT OR REPLACE INTO user_filters (user_id, username, list_type) VALUES (?, ?, ?)",
        (user_id, username, list_type),
    )
    conn.commit()
    conn.close()


def remove_user_filter(user_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM user_filters WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def save_wallet(user_id, pubkey, balance):
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS wallets ("
        "user_id INTEGER PRIMARY KEY,"
        "pubkey TEXT NOT NULL,"
        "balance REAL DEFAULT 0)"
    )
    conn.execute(
        "INSERT OR REPLACE INTO wallets (user_id, pubkey, balance) VALUES (?, ?, ?)",
        (user_id, pubkey, balance),
    )
    conn.commit()
    conn.close()


def get_wallet(user_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS wallets ("
        "user_id INTEGER PRIMARY KEY,"
        "pubkey TEXT NOT NULL,"
        "balance REAL DEFAULT 0)"
    )
    row = conn.execute(
        "SELECT pubkey, balance FROM wallets WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return {"pubkey": row[0], "balance": row[1]}
    return None
