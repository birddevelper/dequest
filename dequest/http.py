import httpx
import requests

from dequest.enums import ConsumerType
from dequest.utils import get_logger

logger = get_logger()


def sync_request(
    method: str,
    url: str,
    headers: dict,
    json: dict,
    params: dict,
    data: dict,
    timeout: int,
    consume: ConsumerType,
):
    logger.info("Sending %s request to %s", method, url)
    response = requests.request(
        method.upper(),
        url,
        headers=headers,
        json=json,
        params=params,
        data=data,
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
    timeout: int,
    consume: ConsumerType,
):
    logger.info("Sending %s request to %s", method, url)
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method.upper(),
            url,
            headers=headers,
            json=json,
            params=params,
            data=data,
            timeout=timeout,
        )
        response.raise_for_status()
    return response.json() if consume == ConsumerType.JSON else response.text
