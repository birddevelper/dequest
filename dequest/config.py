class DequestConfig:
    CACHE_PROVIDER = "in_memory"  # Options: "in_memory", "redis", "database"

    # Redis Settings
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None
    REDIS_SSL = False

    # Logging Settings
    LOG_LEVEL = "INFO"
