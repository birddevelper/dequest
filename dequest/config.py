from enum import StrEnum, auto


class DequestConfig:
    CACHE_PROVIDER = "in_memory"  # Options: "in_memory", "redis", "database"

    # Redis Settings
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None
    REDIS_SSL = False
    PROFILES = {}

    @classmethod
    def config(cls, **kwargs):
        for key, value in kwargs.items():
            setattr(cls, key.upper(), value)


class CacheType(StrEnum):
    IN_MEMORY = auto()
    REDIS = auto()
    DJANGO = auto()
