import asyncio

import pytest

from dequest.cache import get_cache
from dequest.circut_breaker import CircuitBreaker
from dequest.clients import async_client
from dequest.utils import generate_cache_key


class TestDTO:
    key: str

    def __init__(self, key):
        self.key = key


async def fake_succesful_async_request(method, url, headers, json, params, data, timeout, consume):
    return {"key": "value"}


@pytest.mark.asyncio
async def test_async_client_with_callback(monkeypatch):
    url = "https://api.example.com/data"
    expected_response = {"key": "value"}

    monkeypatch.setattr("dequest.clients._async.async_request", fake_succesful_async_request)
    callback_called = asyncio.Event()

    async def my_callback(response):
        assert response == expected_response
        callback_called.set()

    @async_client(callback=my_callback)
    def fetch_data():
        return {"url": url}

    fetch_data()

    await asyncio.wait_for(callback_called.wait(), timeout=2)


@pytest.mark.asyncio
async def test_async_client_with_circuit_breaker_fallback(monkeypatch):
    url = "https://api.example.com/data"
    fallback_called = asyncio.Event()

    async def fallback_function(*args, **kwargs):
        fallback_called.set()

    circuit_breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=10, fallback_function=fallback_function)
    circuit_breaker.record_failure()
    monkeypatch.setattr("dequest.clients._async.async_request", fake_succesful_async_request)
    callback_called = asyncio.Event()

    async def my_callback(response):
        callback_called.set()

    @async_client(callback=my_callback, circuit_breaker=circuit_breaker)
    def fetch_data():
        return {"url": url}

    fetch_data()

    await asyncio.wait_for(fallback_called.wait(), timeout=2)

    assert not callback_called.is_set()
    assert fallback_called.is_set()


@pytest.mark.asyncio
async def test_async_client_with_dto_mapping(monkeypatch):
    url = "https://api.example.com/data"
    monkeypatch.setattr("dequest.clients._async.async_request", fake_succesful_async_request)
    callback_called = asyncio.Event()

    async def my_callback(response):
        assert isinstance(response, TestDTO)
        assert response.key == "value"
        callback_called.set()

    @async_client(callback=my_callback, dto_class=TestDTO)
    def fetch_data():
        return {"url": url}

    fetch_data()

    await asyncio.wait_for(callback_called.wait(), timeout=2)


@pytest.mark.asyncio
async def test_async_client_with_cache_hit(monkeypatch):
    url = "https://api.example.com/data"
    monkeypatch.setattr("dequest.clients._async.async_request", fake_succesful_async_request)
    callback_called = asyncio.Event()
    cache = get_cache()
    cache.clear()
    expected_cache_key = generate_cache_key(url, None)

    async def my_callback(response):
        assert response == {"key": "value"}
        callback_called.set()

    @async_client(callback=my_callback, enable_cache=True)
    def fetch_data():
        return {"url": url}

    # First call, should not hit the cache
    fetch_data()

    await asyncio.wait_for(callback_called.wait(), timeout=2)

    callback_called.clear()

    # Now the cache should be set with the data, so the next call should hit the cache
    fetch_data()

    await asyncio.wait_for(callback_called.wait(), timeout=2)
    assert cache.get_key(expected_cache_key) == '{"key": "value"}'
