from enum import StrEnum, auto

import httpx

from dequest.utils import get_logger

logger = get_logger()


class HttpMethod(StrEnum):
    GET = auto()
    POST = auto()
    PUT = auto()
    PATCH = auto()
    DELETE = auto()


class ConsumerType(StrEnum):
    XML = auto()
    JSON = auto()
    TEXT = auto()


def sync_request(
    method: str,
    url: str,
    headers: dict,
    json: dict,
    params: dict,
    data: dict,
    files: dict,
    timeout: int,
    consume: ConsumerType,
):
    logger.info("Sending %s request to %s", method, url)
    # Filter out None values from files dict
    filtered_files = {k: v for k, v in (files or {}).items() if v is not None}
    response = httpx.request(
        method.upper(),
        url,
        headers=headers,
        json=json,
        params=params,
        data=data,
        files=filtered_files if filtered_files else None,
        timeout=timeout,
    )
    response.raise_for_status()

    return response.json() if consume == ConsumerType.JSON else response.text


async def async_request(
    method: str,
    url: str,
    headers: dict,
    json: dict,
    params: dict,
    data: dict,
    files: dict,
    timeout: int,
    consume: ConsumerType,
):
    logger.info("Sending %s request to %s", method, url)
    # Filter out None values from files dict
    filtered_files = {k: v for k, v in (files or {}).items() if v is not None}
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method.upper(),
            url,
            headers=headers,
            json=json,
            params=params,
            data=data,
            files=filtered_files if filtered_files else None,
            timeout=timeout,
        )
        response.raise_for_status()
    return response.json() if consume == ConsumerType.JSON else response.text
