from .cache_director import CacheDirector


def get_cache() -> CacheDirector:
    return CacheDirector()
