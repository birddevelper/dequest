from enum import StrEnum, auto


class CacheProvider(StrEnum):
    IN_MEMORY = auto()
    REDIS = auto()
    DJANGO = auto()


class DequestConfig:
    CACHE_PROVIDER = CacheProvider.IN_MEMORY

    # Redis Settings
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None
    REDIS_SSL = False

    @classmethod
    def config(cls, **kwargs):
        for key, value in kwargs.items():
            setattr(cls, key.upper(), value)
