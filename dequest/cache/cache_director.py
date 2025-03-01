from dequest.cache.cache_drivers import InMemoryCacheDriver, RedisDriver
from dequest.config import DequestConfig


class CacheDirector:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self.strategy = DequestConfig.CACHE_PROVIDER
            self.driver = None
            if self.strategy == "in_memory":
                self.driver = InMemoryCacheDriver()
            elif self.strategy == "redis":
                self.driver = RedisDriver(
                    host=DequestConfig.REDIS_HOST,
                    port=DequestConfig.REDIS_PORT,
                    db=DequestConfig.REDIS_DB,
                    password=DequestConfig.REDIS_PASSWORD,
                    ssl=DequestConfig.REDIS_SSL,
                )
            else:
                raise ValueError("Invalid cache provider")
            self._initialized = True

    def expire_key(self, key, seconds):
        return self.driver.expire_key(key, seconds)

    def set_key(self, key, value, expire=None):
        return self.driver.set_key(key, value, expire)

    def get_key(self, key):
        return self.driver.get_key(key)

    def clear(self):
        return self.driver.clear()
