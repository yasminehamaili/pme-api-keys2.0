import pytest
import uuid
from sqlalchemy import text
from db import SessionLocal
from security import generate_api_key


async def _insert_key(active: bool):
    raw, prefix, key_hash = generate_api_key()
    async with SessionLocal() as s:
        await s.execute(
            text(
                "INSERT INTO api_keys (id, customer_id, name, key_prefix, key_hash, is_active) "
                "VALUES (:id, :cid, 'test', :p, :h, :a)"
            ),
            {"id": uuid.uuid4(), "cid": uuid.uuid4(), "p": prefix, "h": key_hash, "a": active},
        )
        await s.commit()
    return raw


@pytest.fixture
async def valid_key():
    return await _insert_key(True)


@pytest.fixture
async def revoked_key():
    return await _insert_key(False)