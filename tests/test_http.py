import httpx
import pytest
import respx

from dequest.enums import ConsumerType
from dequest.http import async_request


@pytest.mark.asyncio
async def test_async_request_success():
    url = "https://api.example.com/data"
    mock_response = {"key": "value"}

    with respx.mock:
        respx.get(url).respond(200, json=mock_response)

        response = await async_request(
            method="GET",
            url=url,
            headers={"Authorization": "Bearer test_token"},
            json=None,
            params=None,
            data=None,
            timeout=5,
            consume=ConsumerType.JSON,
        )

    assert response == mock_response


@pytest.mark.asyncio
async def test_async_request_failure():
    url = "https://api.example.com/error"

    with respx.mock:
        respx.get(url).respond(500, json={"error": "Internal Server Error"})

        with pytest.raises(httpx.HTTPStatusError):
            await async_request(
                method="GET",
                url=url,
                headers={},
                json=None,
                params=None,
                data=None,
                timeout=5,
                consume=ConsumerType.JSON,
            )


@pytest.mark.asyncio
async def test_async_request_timeout():
    url = "https://api.example.com/slow"

    with respx.mock:
        respx.get(url).mock(side_effect=httpx.TimeoutException("Request timed out"))

        with pytest.raises(httpx.TimeoutException):
            await async_request(
                method="GET",
                url=url,
                headers={},
                json=None,
                params=None,
                data=None,
                timeout=1,
                consume=ConsumerType.JSON,
            )
