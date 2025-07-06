from dequest.utils import get_logger

logger = get_logger()


class DjangoCacheDriver:
    def __init__(self):
        from django.core.cache import cache  # noqa: PLC0415

        self.cache = cache
        logger.info("Django cache initialized")

    def delete_key(self, key):
        return self.cache.delete(key)

    def set_key(self, key, value, expire=None):
        self.cache.set(key, value, timeout=expire)

    def get_key(self, key):
        value = self.cache.get(key)
        if value is not None:
            logger.info("Cache hit for key: %s", key)
        return value

    def clear(self):
        self.cache.clear()
        logger.info("Django cache cleared")
