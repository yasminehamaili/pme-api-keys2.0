"""
main.py  --  Person 1 (Tasks: "Key Lifecycle" + "Traffic & Limits" endpoints)

Run with:   uvicorn main:app --reload
Docs UI:    http://127.0.0.1:8000/docs      (try every endpoint from the browser)
Dashboard:  http://127.0.0.1:8000/
"""

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database import get_conn, init_db
from key_stub import generate_key          # Person 2 will replace this
from usage import get_usage_today, record_usage

app = FastAPI(title="PME API Keys - Person 1")
init_db()


# --------------------------------------------------------------------------
# Who is the customer?
# Real login/auth is Person 2's area. For now we read an optional header so
# you can test with different customers:  X-Customer-Id: pme_42
# If it's missing we use "demo-customer".
# --------------------------------------------------------------------------
def current_customer(x_customer_id: str | None) -> str:
    return x_customer_id or "demo-customer"


# --------------------------------------------------------------------------
# Request bodies (Pydantic validates them for us)
# --------------------------------------------------------------------------
class CreateKey(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class RenameKey(BaseModel):
    name: str = Field(min_length=1, max_length=60)


# --------------------------------------------------------------------------
# Helper: fetch one key, but ONLY if it belongs to this customer.
# This stops customer A from touching customer B's keys.
# --------------------------------------------------------------------------
def get_owned_key(key_id: int, customer_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE id = ? AND customer_id = ?",
            (key_id, customer_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return row


# ============================ KEY LIFECYCLE ===============================

@app.get("/api/keys")
def list_keys(x_customer_id: str | None = Header(default=None)):
    """List this customer's keys. NEVER returns key_hash."""
    customer = current_customer(x_customer_id)
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, name, key_prefix, is_active, last_used_at, created_at
            FROM api_keys
            WHERE customer_id = ?
            ORDER BY id DESC
            """,
            (customer,),
        ).fetchall()
    return [
        {**dict(r), "is_active": bool(r["is_active"])}  # 1/0 -> true/false
        for r in rows
    ]


@app.post("/api/keys", status_code=201)
def create_key(body: CreateKey, x_customer_id: str | None = Header(default=None)):
    """
    Used by the dashboard's "Generate Key" button.
    The real generation logic is Person 2's; we call their function here.
    The full key is returned ONE time only -- we store just the hash.
    """
    customer = current_customer(x_customer_id)
    full_key, key_prefix, key_hash = generate_key()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO api_keys (customer_id, name, key_hash, key_prefix) "
            "VALUES (?, ?, ?, ?)",
            (customer, body.name.strip(), key_hash, key_prefix),
        )
        key_id = cur.lastrowid
    return {"id": key_id, "name": body.name.strip(), "key_prefix": key_prefix,
            "key": full_key}


@app.patch("/api/keys/{key_id}")
def rename_key(key_id: int, body: RenameKey,
               x_customer_id: str | None = Header(default=None)):
    """Rename a key."""
    customer = current_customer(x_customer_id)
    get_owned_key(key_id, customer)  # 404 if it isn't theirs
    with get_conn() as conn:
        conn.execute("UPDATE api_keys SET name = ? WHERE id = ?",
                     (body.name.strip(), key_id))
    return {"id": key_id, "name": body.name.strip()}


@app.post("/api/keys/{key_id}/revoke")
def revoke_key(key_id: int, x_customer_id: str | None = Header(default=None)):
    """Revoke = set is_active to false. We keep the row (for history/audit)."""
    customer = current_customer(x_customer_id)
    get_owned_key(key_id, customer)
    with get_conn() as conn:
        conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,))
    return {"id": key_id, "is_active": False}


# ============================ TRAFFIC & LIMITS ============================

@app.get("/api/usage")
def usage(x_customer_id: str | None = Header(default=None)):
    """Powers the '450 / 1,000 requests used today' bar."""
    return get_usage_today(current_customer(x_customer_id))


# ============================ DEV-ONLY HELPER =============================

@app.post("/api/dev/simulate-use/{key_id}")
def simulate_use(key_id: int, x_customer_id: str | None = Header(default=None)):
    """
    TESTING ONLY - pretends the key was used once, so you can see
    last_used_at and the usage bar change before Person 2's middleware
    exists. DELETE this endpoint before going to production.
    Person 2's middleware will call record_usage(key_id) for real.
    """
    key = get_owned_key(key_id, current_customer(x_customer_id))
    if not key["is_active"]:
        raise HTTPException(status_code=403, detail="Key is revoked")
    record_usage(key_id)
    return {"ok": True}


# ============================ DASHBOARD PAGE ==============================

@app.get("/")
def dashboard():
    return FileResponse(Path(__file__).parent / "index.html")
