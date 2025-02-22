import requests

from dequest.utils import get_logger

logger = get_logger()


def sync_request(method, url, headers, json, params, data, timeout):
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
    return response.json()
