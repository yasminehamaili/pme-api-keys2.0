"""
test_person1.py -- checks that every Person 1 task works.
Run with:  python test_person1.py
"""

import os
import tempfile
from pathlib import Path

# Use a throwaway database so we don't touch your real keys.db
import database
database.DB_PATH = Path(tempfile.mkdtemp()) / "test.db"

from fastapi.testclient import TestClient
from main import app
from usage import record_usage

client = TestClient(app)
A = {"X-Customer-Id": "customer_A"}
B = {"X-Customer-Id": "customer_B"}


def check(label, condition):
    print(("PASS  " if condition else "FAIL  ") + label)
    assert condition, label


# 1. Table + empty list
r = client.get("/api/keys", headers=A)
check("list starts empty", r.status_code == 200 and r.json() == [])

# 2. Generate a key
r = client.post("/api/keys", json={"name": "Prod"}, headers=A)
created = r.json()
key_id = created["id"]
check("create returns 201 + full key once", r.status_code == 201 and created["key"].startswith("pme_"))

# 3. List never leaks the hash or the full key
r = client.get("/api/keys", headers=A)
row = r.json()[0]
check("list has expected fields", {"name", "key_prefix", "is_active", "last_used_at"} <= set(row))
check("list NEVER contains key_hash", "key_hash" not in row)
check("list NEVER contains full key", created["key"] not in r.text)
check("new key is active and unused", row["is_active"] is True and row["last_used_at"] is None)

# 4. Rename
r = client.patch(f"/api/keys/{key_id}", json={"name": "Staging"}, headers=A)
check("rename works", r.status_code == 200 and client.get("/api/keys", headers=A).json()[0]["name"] == "Staging")
r = client.patch(f"/api/keys/{key_id}", json={"name": ""}, headers=A)
check("empty name rejected (422)", r.status_code == 422)

# 5. Usage tracking: last_used_at + counts
for _ in range(3):
    record_usage(key_id)
row = client.get("/api/keys", headers=A).json()[0]
check("last_used_at updated", row["last_used_at"] is not None)
u = client.get("/api/usage", headers=A).json()
check("usage counts 3 / 1000", u["used"] == 3 and u["limit"] == 1000 and u["remaining"] == 997)

# 6. Customer isolation
check("customer B sees no keys", client.get("/api/keys", headers=B).json() == [])
check("customer B usage is 0", client.get("/api/usage", headers=B).json()["used"] == 0)
check("customer B cannot rename A's key",
      client.patch(f"/api/keys/{key_id}", json={"name": "hack"}, headers=B).status_code == 404)
check("customer B cannot revoke A's key",
      client.post(f"/api/keys/{key_id}/revoke", headers=B).status_code == 404)

# 7. Revoke
r = client.post(f"/api/keys/{key_id}/revoke", headers=A)
row = client.get("/api/keys", headers=A).json()[0]
check("revoke sets is_active false", r.status_code == 200 and row["is_active"] is False)
check("simulate-use refused on revoked key",
      client.post(f"/api/dev/simulate-use/{key_id}", headers=A).status_code == 403)

# 8. Dashboard page loads
check("dashboard HTML served", "Generate Key" in client.get("/").text)

print("\nAll Person 1 checks passed.")
