import logging


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

    @staticmethod
    def get_log_level() -> int:
        log_level = DequestConfig.LOG_LEVEL.upper()
        if log_level == "DEBUG":
            return logging.DEBUG
        if log_level == "INFO":
            return logging.INFO
        if log_level == "WARNING":
            return logging.WARNING
        if log_level == "ERROR":
            return logging.ERROR
        if log_level == "CRITICAL":
            return logging.CRITICAL
        raise ValueError(f"Invalid log level: {log_level}")
