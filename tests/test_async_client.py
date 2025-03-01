import asyncio

import pytest

from dequest.circut_breaker import CircuitBreaker
from dequest.clients import async_client


class TestDTO:
    key: str

    def __init__(self, key):
        self.key = key


async def fake_succesful_async_request(method, url, headers, json, params, data, timeout):
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
