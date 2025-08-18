# app/db.py
import os
from functools import lru_cache
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "").strip()
MONGO_DB  = os.getenv("MONGO_DB", "MasterPig").strip()

_client: AsyncIOMotorClient | None = None

async def get_db():
    """
    Returns an async Motor database or None if MONGO_URI is not set or not reachable.
    """
    global _client
    if not MONGO_URI:
        return None
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    try:
        # quick connectivity check
        await _client.admin.command("ping")
    except Exception:
        return None
    return _client[MONGO_DB]
