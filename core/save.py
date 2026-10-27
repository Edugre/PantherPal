"""SQLite-backed persistence: pet state, points, settings, chat and game logs."""
import json
import sqlite3
import time

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_log (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      REAL NOT NULL,
    role    TEXT NOT NULL,          -- 'child' | 'sunny'
    text    TEXT NOT NULL,
    flagged INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS game_results (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        REAL NOT NULL,
    game      TEXT NOT NULL,
    score     INTEGER NOT NULL,
    max_score INTEGER NOT NULL,
    points    INTEGER NOT NULL
);
"""


class SaveStore:
    def __init__(self, path=config.DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # --- generic key/value (JSON) ---
    def get(self, key, default=None):
        row = self.conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        self.conn.execute(
            "INSERT INTO kv (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )
        self.conn.commit()

    # --- convenience accessors ---
    def load_settings(self):
        return {**config.DEFAULT_SETTINGS, **self.get("settings", {})}

    def save_settings(self, settings):
        self.set("settings", settings)

    # --- logs ---
    def log_chat(self, role, text, flagged=False):
        self.conn.execute(
            "INSERT INTO chat_log (ts, role, text, flagged) VALUES (?, ?, ?, ?)",
            (time.time(), role, text, int(flagged)),
        )
        self.conn.commit()

    def chat_count_since(self, since_ts):
        row = self.conn.execute(
            "SELECT COUNT(*) FROM chat_log WHERE role = 'child' AND ts >= ?", (since_ts,)
        ).fetchone()
        return row[0]

    def log_game(self, game, score, max_score, points):
        self.conn.execute(
            "INSERT INTO game_results (ts, game, score, max_score, points) VALUES (?, ?, ?, ?, ?)",
            (time.time(), game, score, max_score, points),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
