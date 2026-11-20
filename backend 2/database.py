"""
database.py  --  Person 1 (Task: "Database")

Creates the api_keys table and opens connections to the database.
We use SQLite because it needs ZERO setup (it's just a file: keys.db).
Later your team can move to PostgreSQL; the SQL below is almost identical.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "keys.db"


def get_conn() -> sqlite3.Connection:
    """Open a connection. row_factory lets us read columns by name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the tables if they don't exist yet. Safe to call every startup."""
    with get_conn() as conn:
        # The table required by the task: api_keys
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id  TEXT    NOT NULL,
                name         TEXT    NOT NULL,
                key_hash     TEXT    NOT NULL,          -- never sent to the browser
                key_prefix   TEXT    NOT NULL,          -- e.g. "pme_a1b2c3d4" (safe to show)
                is_active    INTEGER NOT NULL DEFAULT 1,-- 1 = active, 0 = revoked
                last_used_at TEXT,                      -- NULL until first use
                created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            )
            """
        )

        # Small helper table for "usage counts for the customer dashboard".
        # One row per key per day, with a counter.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_log (
                api_key_id    INTEGER NOT NULL REFERENCES api_keys(id),
                day           TEXT    NOT NULL,         -- 'YYYY-MM-DD' (UTC)
                request_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (api_key_id, day)
            )
            """
        )
        # Note: the index on key_hash (for fast lookups) is Person 2's task.


if __name__ == "__main__":
    init_db()
    print(f"Database ready at {DB_PATH}")
