import json
import time
from collections.abc import Callable
from functools import wraps
from typing import Optional, TypeVar, Union

from requests.exceptions import RequestException, Timeout

from dequest.cache import get_cache
from dequest.circut_breaker import CircuitBreaker
from dequest.config import DequestConfig
from dequest.enums import ConsumerType
from dequest.exceptions import CircuitBreakerOpenError, DequestError
from dequest.http import sync_request
from dequest.utils import generate_cache_key, get_logger, map_json_to_dto, map_xml_to_dto

T = TypeVar("T")
logger = get_logger()
cache = get_cache()


def _perform_request(
    url: str,
    method: str,
    headers: Optional[dict],
    json_body: Optional[dict],
    params: Optional[dict],
    data: Optional[dict],
    timeout: int,
    enable_cache: bool,
    cache_ttl: Optional[int],
    consume: ConsumerType,
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
            logger.info(
                "Cache hit for %s (provider: %s)",
                url,
                DequestConfig.CACHE_PROVIDER,
            )
            return json.loads(cached_response) if consume == ConsumerType.JSON else cached_response

    response = sync_request(method, url, headers, json_body, params, data, timeout, consume)
    logger.debug("Response for %s: %s", url, response)
    if enable_cache:
        cache.set_key(cache_key, json.dumps(response) if consume == ConsumerType.JSON else response, cache_ttl)
        logger.info(
            "Cached response for %s in %s",
            url,
            DequestConfig.CACHE_PROVIDER,
        )

    return response


def sync_client(
    dto_class: Optional[type[T]] = None,
    method: str = "GET",
    timeout: int = 30,
    retries: int = 1,
    retry_delay: float = 2.0,
    auth_token: Optional[Union[str, Callable[[], str]]] = None,
    api_key: Optional[Union[str, Callable[[], str]]] = None,
    headers: Optional[Union[dict[str, str], Callable[[], dict[str, str]]]] = None,
    enable_cache: bool = False,
    cache_ttl: Optional[int] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    consume: ConsumerType = ConsumerType.JSON,
):
    """
    A decorator to make synchronous HTTP requests and map the response to a DTO class.
    Supports authentication (static and dynamic), retries, logging, query parameters, custom headers,
    timeout, circuit breaker and caching.

    :param dto_class: The DTO class to map the response data.
    :param method: HTTP method (GET, POST, PUT, DELETE).
    :param timeout: Request timeout in seconds.
    :param retries: Number of retries on failure.
    :param retry_delay: Delay in seconds between retries.
    :param auth_token: Optional Bearer Token (static string or function returning a string).
    :param api_key: Optional API key (static string or function returning a string).
    :param headers: Optional default headers (can be a dict or a function returning a dict).
    :param enable_cache: Whether to cache GET responses.
    :param cache_ttl: Cache expiration time in seconds.
    :param circuit_breaker: Instance of CircuitBreaker (optional).
    :param consume: The type of data to consume. ConsumerType.JSON, ConsumerType.XML or ConsumerType.TEXT
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

            if consume == ConsumerType.TEXT and dto_class:
                raise DequestError("ConsumerType.TEXT cannot be used with dto_class.")

            request_headers = headers() if callable(headers) else (headers or {})
            token_value = auth_token() if callable(auth_token) else auth_token
            api_key_value = api_key() if callable(api_key) else api_key

            if token_value:
                request_headers["Authorization"] = f"Bearer {token_value}"
            if api_key_value:
                request_headers["x-api-key"] = api_key_value

            # Circuit breaker logic (only applies if an instance of CircuitBreaker is provided)
            if circuit_breaker and not circuit_breaker.allow_request():
                logger.warning("Circuit breaker blocking requests to %s", url)
                if circuit_breaker.fallback_function:
                    return circuit_breaker.fallback_function(*args, **kwargs)

                raise CircuitBreakerOpenError(f"Circuit breaker is OPEN. Requests to {url} are blocked.")

            for attempt in range(1, retries + 1):
                try:
                    response_data = _perform_request(
                        url,
                        method,
                        request_headers,
                        json_body,
                        params,
                        data,
                        timeout,
                        enable_cache,
                        cache_ttl,
                        consume,
                    )

                    if circuit_breaker:
                        circuit_breaker.record_success()

                    if not dto_class:
                        return response_data

                    return (
                        map_json_to_dto(dto_class, response_data)
                        if consume == ConsumerType.JSON
                        else map_xml_to_dto(dto_class, response_data)
                    )

                except (RequestException, Timeout) as e:
                    logger.error("Dequest client error: %s", e)
                    if attempt < retries:
                        logger.info(
                            "Retrying in %s seconds... (Attempt %s/%s)",
                            retry_delay,
                            attempt,
                            retries,
                        )
                        time.sleep(retry_delay)
                    else:
                        # Record single failure when all attempts fail
                        if circuit_breaker:
                            circuit_breaker.record_failure()
                        raise DequestError(
                            f"Dequest client failed after {retries} attempts: {retries}",
                        ) from e

            return None

        return wrapper

    return decorator
