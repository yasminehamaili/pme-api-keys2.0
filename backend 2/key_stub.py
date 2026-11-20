"""
key_stub.py  --  TEMPORARY placeholder

Generating and hashing keys securely is PERSON 2's job
("Build the key generation & hashing engine", HMAC-SHA256 + server pepper).

So that YOUR dashboard's "Generate Key" button works while you wait,
this file contains a simple stand-in. When Person 2 is done, they replace
this function with theirs. Keep the same inputs/outputs and nothing else
in your code has to change:

    generate_key() -> (full_key, key_prefix, key_hash)

DO NOT use this in production: it has no pepper (HMAC).
"""

import hashlib
import secrets


def generate_key() -> tuple[str, str, str]:
    full_key = "pme_" + secrets.token_urlsafe(32)   # shown to the customer ONCE
    key_prefix = full_key[:12]                       # safe to display later
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()  # what we store
    return full_key, key_prefix, key_hash
