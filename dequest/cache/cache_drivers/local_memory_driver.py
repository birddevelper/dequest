import time
from collections import defaultdict

from dequest.utils import get_logger

logger = get_logger()


class InMemoryCacheDriver:
    def __init__(self):
        self.store = defaultdict(dict)
        logger.info("Local memory cache initialized")

    def expire_key(self, key, seconds):
        self.store[key]["expires_at"] = int(time.time()) + seconds

    def set_key(self, key, value, expire=None):
        expires_at = None
        if expire:
            expires_at = int(time.time()) + expire

        self.store[key] = {"data": value, "expires_at": expires_at}

    def get_key(self, key):
        cached_entry = self.store[key]

        if cached_entry and (cached_entry["expires_at"] is None or time.time() < cached_entry["expires_at"]):
            logger.info("Cache hit for key: %s", key)
            return cached_entry["data"]

        if cached_entry and cached_entry["expires_at"] is not None and time.time() > cached_entry["expires_at"]:
            logger.info("Cache expired for key: %s", key)
            self.store.pop(key, None)

        return None

    def clear(self):
        self.store.clear()
