import os
import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS friendships (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    friend_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'accepted', 'blocked')),
    trust_weight REAL NOT NULL DEFAULT 0.5 CHECK (trust_weight BETWEEN 0 AND 1),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, friend_id),
    CHECK (user_id != friend_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tmdb_id INTEGER NOT NULL,
    media_type TEXT NOT NULL CHECK (media_type IN ('movie', 'tv', 'short')),
    rating REAL CHECK (rating BETWEEN 0.5 AND 5),
    review_text TEXT NOT NULL DEFAULT '',
    contains_spoilers INTEGER NOT NULL DEFAULT 0,
    watched_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, tmdb_id, media_type)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider_id INTEGER NOT NULL,
    provider_name TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'US',
    PRIMARY KEY (user_id, provider_id, region)
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tmdb_id INTEGER NOT NULL,
    media_type TEXT NOT NULL CHECK (media_type IN ('movie', 'tv', 'short')),
    note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'unseen'
        CHECK (status IN ('unseen', 'saved', 'watched', 'dismissed')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (sender_id != recipient_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_title ON reviews (tmdb_id, media_type);
CREATE INDEX IF NOT EXISTS idx_recommendations_recipient
    ON recommendations (recipient_id, status, created_at);
"""


def database_path():
    configured = os.getenv("DINNERCUE_DATABASE_PATH")
    return Path(configured) if configured else Path(__file__).resolve().parents[1] / "instance" / "dinnercue.db"


def connect(path=None):
    target = Path(path) if path else database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(path=None):
    connection = connect(path)
    try:
        connection.executescript(SCHEMA)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
        if "password_hash" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            connection.commit()
    finally:
        connection.close()
