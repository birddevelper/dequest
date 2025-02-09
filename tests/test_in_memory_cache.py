import time

from dequest.cache.cache_drivers import InMemoryCacheDriver


def test_set_key():
    cache = InMemoryCacheDriver()

    cache.set_key("key", "value")

    assert cache.store["key"] == {"data": "value", "expires_at": None}


def test_set_key_with_expiration():
    cache = InMemoryCacheDriver()

    cache.set_key("key", "value", 10)

    assert cache.store["key"]["data"] == "value"
    assert cache.store["key"]["expires_at"] == int(time.time()) + 10


def test_get_key():
    cache = InMemoryCacheDriver()
    cache.set_key("key", "value")

    assert cache.get_key("key") == "value"


def test_expire_key():
    cache = InMemoryCacheDriver()
    cache.set_key("key", "value")

    cache.expire_key("key", 0)
    time.sleep(1)

    assert cache.get_key("key") is None
