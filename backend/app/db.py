"""MongoDB access with an in-memory fallback so the app still runs without a DB."""
import logging
import threading
import time

from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

from .config import settings

log = logging.getLogger("db")
_db = None
_lock = threading.Lock()
_failed_at = 0.0
RETRY_AFTER_S = 15  # after a failed connect, fail fast instead of stalling every request for 2s


def get_db():
    global _db, _failed_at
    if _db is not None:
        return _db
    with _lock:
        if _db is not None:  # another thread connected while we waited
            return _db
        if time.monotonic() - _failed_at < RETRY_AFTER_S:
            raise PyMongoError("MongoDB unavailable (recent connection failure)")
        try:
            client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=2000)
            client.admin.command("ping")
            db = client[settings.mongo_db]
            log.info("Connected to MongoDB", extra={"database": settings.mongo_db})
        except PyMongoError as exc:
            if not settings.allow_mongomock_fallback:
                _failed_at = time.monotonic()
                log.error("MongoDB unavailable: %s", exc)
                raise
            import mongomock

            log.warning("MongoDB unavailable (%s); using in-memory mongomock", exc)
            db = mongomock.MongoClient()[settings.mongo_db]
        _ensure_indexes(db)
        _db = db
        return _db


def ping() -> bool:
    """True if the database answers; used by the readiness endpoint."""
    try:
        get_db().list_collection_names()  # a real round trip on MongoDB; works on mongomock too
        return True
    except Exception as exc:
        log.error("Database readiness check failed: %s", exc)
        return False


def _ensure_indexes(db) -> None:
    ttl = settings.cache_ttl_days * 86400
    for name in ("raw_series", "analyses"):
        try:
            db[name].create_index([("fetched_at", ASCENDING)], expireAfterSeconds=ttl)
        except Exception as exc:  # mongomock may not support every option; a changed TTL conflicts with the old index
            log.warning("Could not create TTL index on %s: %s", name, exc)


def set_db(db) -> None:
    global _db
    _db = db
