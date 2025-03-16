from enum import StrEnum, auto


class ConsumerType(StrEnum):
    XML = auto()
    JSON = auto()
    TEXT = auto()


class CacheType(StrEnum):
    IN_MEMORY = auto()
    REDIS = auto()


class HttpMethod(StrEnum):
    GET = auto()
    POST = auto()
    PUT = auto()
    PATCH = auto()
    DELETE = auto()
