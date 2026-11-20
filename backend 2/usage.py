"""
usage.py  --  Person 1 (Tasks: "API Protection" + "Traffic & Limits")

Two jobs:
  1. record_usage(key_id): called every time a key is used.
     Updates last_used_at and adds +1 to today's counter.
     -> Person 2's auth middleware will call this after a key is validated.
  2. get_usage_today(customer_id): total requests today for ALL of a
     customer's keys, so the dashboard can show "450 / 1,000 requests today".
"""

from datetime import datetime, timezone

from database import get_conn

# The PME's plan limit. Hard-coded for now; later it can come from a plans table.
DAILY_LIMIT = 1000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_usage(key_id: int) -> None:
    """Mark a key as used just now and count the request."""
    now = _now()
    today = now.strftime("%Y-%m-%d")
    with get_conn() as conn:
        conn.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
            (now.strftime("%Y-%m-%d %H:%M:%S"), key_id),
        )
        # "Upsert": insert a row for today, or add 1 if it already exists.
        conn.execute(
            """
            INSERT INTO usage_log (api_key_id, day, request_count)
            VALUES (?, ?, 1)
            ON CONFLICT(api_key_id, day)
            DO UPDATE SET request_count = request_count + 1
            """,
            (key_id, today),
        )


def get_usage_today(customer_id: str) -> dict:
    """Requests made today across all keys that belong to this customer."""
    today = _now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(u.request_count), 0) AS used
            FROM usage_log u
            JOIN api_keys k ON k.id = u.api_key_id
            WHERE k.customer_id = ? AND u.day = ?
            """,
            (customer_id, today),
        ).fetchone()
    used = row["used"]
    return {
        "used": used,
        "limit": DAILY_LIMIT,
        "remaining": max(DAILY_LIMIT - used, 0),
        "percent": round(min(used / DAILY_LIMIT, 1) * 100, 1),
    }
