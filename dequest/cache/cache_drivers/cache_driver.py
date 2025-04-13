from abc import ABC, abstractmethod


class CacheDriver(ABC):
    @abstractmethod
    def get_key(self, key):
        pass

    @abstractmethod
    def set_key(self, key, value, expire=None):
        pass

    @abstractmethod
    def delete_key(self, key):
        pass

    @abstractmethod
    def clear(self):
        pass
