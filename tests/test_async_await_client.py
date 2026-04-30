import asyncio
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from dequest import (
    CircuitBreaker,
    ConsumerType,
    FormParameter,
    JsonBody,
    QueryParameter,
    async_await_client,
    get_cache,
)
from dequest.exceptions import DequestError
from dequest.utils import generate_cache_key


class MockDTO:
    key: str

    def __init__(self, key):
        self.key = key


@pytest.mark.asyncio
async def test_async_await_client_returns_response():
    url = "https://api.example.com/data"

    @async_await_client(url=url)
    async def fetch_data():
        pass

    with respx.mock:
        route = respx.get(url).respond(200, json={"key": "value"})

        result = await fetch_data()

    assert result == {"key": "value"}
    assert route.called


@pytest.mark.asyncio
async def test_async_await_client_with_dto_mapping():
    url = "https://api.example.com/data"

    @async_await_client(url=url, dto_class=MockDTO)
    async def fetch_data():
        pass

    with respx.mock:
        route = respx.get(url).respond(200, json={"key": "value"})

        result = await fetch_data()

    assert isinstance(result, MockDTO)
    assert result.key == "value"
    assert route.called


@pytest.mark.asyncio
async def test_async_await_client_with_query_params():
    url = "https://api.example.com/data"
    expected_response = {"user_id": 1, "username": "test_user"}

    @async_await_client(url=url)
    async def fetch_data(
        user_id: int = QueryParameter(),
        username: str = QueryParameter(),
    ):
        pass

    with respx.mock:
        route = respx.get(
            url,
            params={
                "user_id": str(expected_response["user_id"]),
                "username": expected_response["username"],
            },
        ).respond(200, json=expected_response)

        result = await fetch_data(
            expected_response["user_id"],
            expected_response["username"],
        )

    assert result == expected_response
    assert route.called


@pytest.mark.asyncio
async def test_async_await_client_with_json_body():
    url = "https://api.example.com/data"
    payload = {"my_key": "test_value", "my_key2": "test_value2"}
    expected_response = {"status": "ok"}

    @async_await_client(url=url, method="POST", consume=ConsumerType.JSON)
    async def fetch_data(
        my_key_1: str = JsonBody(alias="my_key"),
        my_key_2: str = JsonBody(alias="my_key2"),
    ):
        pass

    with respx.mock:
        route = respx.post(url, json=payload).respond(200, json=expected_response)

        result = await fetch_data(payload["my_key"], payload["my_key2"])

    assert result == expected_response
    assert route.called


@pytest.mark.asyncio
async def test_async_await_client_with_form_data():
    url = "https://api.example.com/data"
    expected_response = {"success": True}

    @async_await_client(url=url, method="POST")
    async def fetch_data(
        user_id: int = FormParameter(alias="user_id"),
        username: str = FormParameter(alias="username"),
    ):
        pass

    def handle_request(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        parsed = parse_qs(body)
        assert parsed == {"user_id": ["1"], "username": ["test_user"]}
        return httpx.Response(200, json=expected_response)

    with respx.mock:
        route = respx.post(url).mock(side_effect=handle_request)

        result = await fetch_data(1, "test_user")

    assert result == expected_response
    assert route.called


@pytest.mark.asyncio
async def test_async_await_client_with_cache_hit():
    url = "https://api.example.com/data"
    cache = get_cache()
    cache.clear()
    call_count = {"count": 0}

    @async_await_client(url=url, enable_cache=True)
    async def fetch_data():
        pass

    def handle_request(request: httpx.Request) -> httpx.Response:
        call_count["count"] += 1
        return httpx.Response(200, json={"key": "value"})

    with respx.mock:
        respx.get(url).mock(side_effect=handle_request)

        first_result = await fetch_data()
        second_result = await fetch_data()

    assert first_result == {"key": "value"}
    assert second_result == {"key": "value"}
    assert call_count["count"] == 1
    assert cache.get_key(generate_cache_key(url, {})) == '{"key": "value"}'


@pytest.mark.asyncio
async def test_async_await_client_retries_on_timeout():
    url = "https://api.example.com/data"
    call_count = {"count": 0}
    expected_call_count = 2

    @async_await_client(
        url=url,
        retries=1,
        retry_on_exceptions=(httpx.TimeoutException,),
        retry_delay=0,
    )
    async def fetch_data():
        pass

    def handle_request(request: httpx.Request) -> httpx.Response:
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise httpx.TimeoutException("Request timed out")
        return httpx.Response(200, json={"key": "value"})

    with respx.mock:
        respx.get(url).mock(side_effect=handle_request)

        result = await fetch_data()

    assert result == {"key": "value"}
    assert call_count["count"] == expected_call_count


@pytest.mark.asyncio
async def test_async_await_client_with_circuit_breaker_fallback():
    url = "https://api.example.com/data"
    fallback_called = asyncio.Event()

    async def fallback_function(*args, **kwargs):
        fallback_called.set()
        return {"fallback": True}

    circuit_breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=10,
        fallback_function=fallback_function,
    )
    circuit_breaker.record_failure()

    @async_await_client(url=url, circuit_breaker=circuit_breaker)
    async def fetch_data():
        pass

    with respx.mock:
        result = await fetch_data()

    await asyncio.wait_for(fallback_called.wait(), timeout=2)
    assert result == {"fallback": True}


@pytest.mark.asyncio
async def test_async_await_client_with_text_consumer_and_dto_raises():
    url = "https://api.example.com/data"

    @async_await_client(url=url, dto_class=MockDTO, consume=ConsumerType.TEXT)
    async def fetch_data():
        pass

    with pytest.raises(DequestError):
        await fetch_data()


@pytest.mark.asyncio
async def test_async_await_client_with_async_callback():
    url = "https://api.example.com/data"
    callback_called = asyncio.Event()

    async def callback(response):
        assert response == {"key": "value"}
        callback_called.set()

    @async_await_client(url=url, callback=callback)
    async def fetch_data():
        pass

    with respx.mock:
        respx.get(url).respond(200, json={"key": "value"})

        result = await fetch_data()

    await asyncio.wait_for(callback_called.wait(), timeout=2)
    assert result == {"key": "value"}
