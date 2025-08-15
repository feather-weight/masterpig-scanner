from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

_client = None
_db = None

async def get_db():
    global _client, _db
    if _db:
        return _db
    if not settings.mongo_uri:
        return None
    _client = AsyncIOMotorClient(settings.mongo_uri, uuidRepresentation="standard")
    _db = _client[settings.mongo_db]
    # indices
    await _db.addresses.create_index("address", unique=True)
    await _db.addresses.create_index([("tx_count", 1), ("last_seen", -1)])
    await _db.edges.create_index([("src", 1), ("dst", 1)], unique=True)
    await _db.stats.create_index("bucket")
    return _db
