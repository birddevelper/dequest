from dequest.cache.cache_drivers.cache_driver import CacheDriver
from dequest.cache.cache_drivers.django_driver import DjangoCacheDriver
from dequest.cache.cache_drivers.local_memory_driver import InMemoryCacheDriver
from dequest.cache.cache_drivers.redis_driver import RedisDriver
from dequest.config import DequestConfig


class CacheDriverFactory:
    @staticmethod
    def create_driver(strategy: str) -> CacheDriver:
        if strategy == "in_memory":
            return InMemoryCacheDriver()
        if strategy == "redis":
            return RedisDriver(
                host=DequestConfig.REDIS_HOST,
                port=DequestConfig.REDIS_PORT,
                db=DequestConfig.REDIS_DB,
                password=DequestConfig.REDIS_PASSWORD,
                ssl=DequestConfig.REDIS_SSL,
            )
        if strategy == "django":
            return DjangoCacheDriver()
        raise ValueError("Invalid cache provider")
