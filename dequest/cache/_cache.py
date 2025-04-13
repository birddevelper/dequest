from dequest.cache.cache_driver_factory import CacheDriverFactory
from dequest.config import DequestConfig


class SingletonClass(type):
    _instance = None

    def __call__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


class Cache(metaclass=SingletonClass):
    def __init__(self):
        self.driver = CacheDriverFactory.create_driver(DequestConfig.CACHE_PROVIDER)

    def delete_key(self, key):
        return self.driver.delete_key(key)

    def set_key(self, key, value, expire=None):
        return self.driver.set_key(key, value, expire)

    def get_key(self, key):
        return self.driver.get_key(key)

    def clear(self):
        return self.driver.clear()
