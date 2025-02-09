import json
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Optional, TypeVar, Union

from requests.exceptions import RequestException, Timeout

from dequest.http import sync_request

from ..cache import get_cache
from ..config import DequestConfig
from ..exceptions import DequestError
from ..utils import generate_cache_key, map_to_dto

T = TypeVar("T")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

cache = get_cache()


def perform_request(
    url: str,
    method: Optional[str] = "GET",
    headers: Optional[dict] = None,
    json_body: Optional[dict] = None,
    params: Optional[dict] = None,
    data: Optional[dict] = None,
    timeout: Optional[int] = 60,
    enable_cache: Optional[bool] = False,
    cache_ttl: Optional[int] = None,
) -> dict:
    method = method.upper()

    if (enable_cache or cache_ttl) and method != "GET":
        raise ValueError(
            "Cache is only supported for GET requests.",
        )

    if enable_cache:
        cache_key = generate_cache_key(url, params)
        cached_response = cache.get_key(cache_key)
        if cached_response:
            logging.info(
                "Cache hit for %s (provider: %s)",
                url,
                DequestConfig.CACHE_PROVIDER,
            )
            return json.loads(cached_response)

    response = sync_request(method, url, headers, json_body, params, data, timeout)

    if enable_cache:
        cache.set_key(cache_key, json.dumps(response), cache_ttl)
        logging.info(
            "Cached response for %s in %s",
            url,
            DequestConfig.CACHE_PROVIDER,
        )

    return response


def sync_client(
    dto_class: Optional[type[T]] = None,
    method: str = "GET",
    timeout: int = 5,
    retries: int = 3,
    retry_delay: float = 2.0,
    auth_token: Optional[Union[str, Callable[[], str]]] = None,
    api_key: Optional[Union[str, Callable[[], str]]] = None,
    headers: Optional[Union[dict[str, str], Callable[[], dict[str, str]]]] = None,
    enable_cache: bool = False,
    cache_ttl: Optional[int] = None,
):
    """
    A decorator to make HTTP requests and map the response to a DTO class.
    Supports authentication (static and dynamic), retries, logging, query parameters, custom headers, and caching.

    :param dto_class: The DTO class to map the response data.
    :param method: HTTP method (GET, POST, PUT, DELETE).
    :param timeout: Request timeout in seconds.
    :param retries: Number of retries on failure.
    :param retry_delay: Delay in seconds between retries.
    :param auth_token: Optional Bearer Token (static string or function returning a string).
    :param api_key: Optional API key (static string or function returning a string).
    :param headers: Optional default headers (can be a dict or a function returning a dict).
    :param enable_cache: Whether to cache GET responses.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            result = func(*args, **kwargs)

            if not isinstance(result, dict):
                raise DequestError("Dequest client function must return a dictionary.")

            url = result["url"]
            json_body = result.get("json_body", None)
            params = result.get("params", None)
            data = result.get("data", None)

            if not isinstance(url, str):
                raise DequestError("The 'url' key must contain a valid URL string.")

            request_headers = headers() if callable(headers) else (headers or {})
            token_value = auth_token() if callable(auth_token) else auth_token
            api_key_value = api_key() if callable(api_key) else api_key

            if token_value:
                request_headers["Authorization"] = f"Bearer {token_value}"
            if api_key_value:
                request_headers["x-api-key"] = api_key_value

            for attempt in range(1, retries + 1):
                try:
                    response_data = perform_request(
                        url,
                        method,
                        request_headers,
                        json_body,
                        params,
                        data,
                        timeout,
                        enable_cache,
                        cache_ttl,
                    )

                    if not dto_class:
                        return response_data

                    return (
                        [map_to_dto(dto_class, item) for item in response_data]
                        if isinstance(response_data, list)
                        else map_to_dto(dto_class, response_data)
                    )

                except (RequestException, Timeout) as e:
                    logging.error("Dequest client error: %s", e)
                    if attempt < retries:
                        logging.info(
                            "Retrying in %s seconds... (Attempt %s/%s)",
                            retry_delay,
                            attempt,
                            retries,
                        )
                        time.sleep(retry_delay)
                    else:
                        raise DequestError(
                            f"Dequest client failed after {retries} attempts: {retries}",
                        ) from e

            return None

        return wrapper

    return decorator
