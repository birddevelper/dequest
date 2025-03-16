from enum import StrEnum, auto


class ConsumerType(StrEnum):
    XML = auto()
    JSON = auto()


class CacheType(StrEnum):
    IN_MEMORY = auto()
    REDIS = auto()
