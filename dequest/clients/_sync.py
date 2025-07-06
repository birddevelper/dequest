import inspect
import json
import time
from collections.abc import Callable, Iterator
from functools import wraps
from typing import TypeVar, Union

from dequest.cache import get_cache
from dequest.circuit_breaker import CircuitBreaker
from dequest.config import DequestConfig
from dequest.exceptions import CircuitBreakerOpenError, DequestError
from dequest.http import ConsumerType, sync_request
from dequest.utils import (
    extract_parameters,
    generate_cache_key,
    get_logger,
    get_next_delay,
    map_json_to_dto,
    map_xml_to_dto,
)

T = TypeVar("T")
logger = get_logger()
cache = get_cache()


def _perform_request(
    url: str,
    method: str,
    headers: dict | None,
    json_body: dict | None,
    params: dict | None,
    data: dict | None,
    timeout: int,
    enable_cache: bool,
    cache_ttl: int | None,
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

    response = sync_request(
        method,
        url,
        headers,
        json_body,
        params,
        data,
        timeout,
        consume,
    )
    logger.debug("Response for %s: %s", url, response)
    if enable_cache:
        cache.set_key(
            cache_key,
            json.dumps(response) if consume == ConsumerType.JSON else response,
            cache_ttl,
        )
        logger.info(
            "Cached response for %s in %s",
            url,
            DequestConfig.CACHE_PROVIDER,
        )

    return response


def sync_client(
    url: str,
    dto_class: type[T] | None = None,
    source_field: str | None = None,
    method: str = "GET",
    timeout: int = 30,
    retries: int = 0,
    retry_on_exceptions: tuple[Exception, ...] | None = None,
    retry_delay: Union[float, Callable[[], Iterator]] = 2.0,
    giveup: Callable[[Exception], bool] | None = None,
    auth_token: Union[str, Callable[[], str]] | None = None,
    api_key: Union[str, Callable[[], str]] | None = None,
    headers: Union[dict[str, str], Callable[[], dict[str, str]]] | None = None,
    enable_cache: bool = False,
    cache_ttl: int | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    consume: ConsumerType = ConsumerType.JSON,
):
    """
    A declarative decorator to make synchronous HTTP requests.
    Supports authentication (static and dynamic), retries, logging, query parameters, form parameters,
    timeout, circuit breaker, and caching.

    :param url: URL template with placeholders for path parameters.
    :param dto_class: DTO class to map response data.
    :param source_field: Source field to use for mapping response data. Leave None to map whole response.
    :param method: HTTP method (GET, POST, PUT, DELETE).
    :param timeout: Request timeout in seconds.
    :param retries: Number of retries on failure.
    :param retry_on_exceptions: Exceptions to retry on.
    :param retry_delay: Delay in seconds between retries. Can be a static value or a function returning iterator.
    :param giveup: Function to determine if a retry should be given up.
    :param auth_token: Optional Bearer Token (static string or function returning a string).
    :param api_key: Optional API key (static string or function returning a string).
    :param headers: Optional default headers (can be a dict or a function returning a dict).
    :param enable_cache: Whether to cache GET responses.
    :param cache_ttl: Cache expiration time in seconds.
    :param circuit_breaker: Instance of CircuitBreaker (optional).
    :param consume: The type of data to consume (JSON, XML, TEXT).
    """

    def decorator(func):
        signature = inspect.signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs) -> T | None:
            if consume == ConsumerType.TEXT and dto_class:
                raise DequestError("ConsumerType.TEXT cannot be used with dto_class.")

            path_params, query_params, form_params, json_body = extract_parameters(
                signature,
                args,
                kwargs,
            )
            formatted_url = url.format(**path_params)

            request_headers = headers() if callable(headers) else (headers or {})
            token_value = auth_token() if callable(auth_token) else auth_token
            api_key_value = api_key() if callable(api_key) else api_key
            _retry_delay = retry_delay() if callable(retry_delay) else retry_delay

            if token_value:
                request_headers["Authorization"] = f"Bearer {token_value}"
            if api_key_value:
                request_headers["x-api-key"] = api_key_value

            # Circuit breaker logic (only applies if an instance of CircuitBreaker is provided)
            if circuit_breaker and not circuit_breaker.allow_request():
                logger.warning("Circuit breaker blocking requests to %s", formatted_url)
                if circuit_breaker.fallback_function:
                    return circuit_breaker.fallback_function(*args, **kwargs)

                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Requests to {formatted_url} are blocked.",
                )

            for attempt in range(1, retries + 2):
                try:
                    response_data = _perform_request(
                        formatted_url,
                        method,
                        request_headers,
                        json_body,
                        query_params,
                        form_params,
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
                        map_json_to_dto(dto_class, response_data, source_field)
                        if consume == ConsumerType.JSON
                        else map_xml_to_dto(dto_class, response_data)
                    )

                except Exception as e:
                    _giveup = giveup(e) if giveup else False

                    if retry_on_exceptions and isinstance(e, retry_on_exceptions) and not _giveup:
                        logger.error("Dequest client error: %s", e)

                        if attempt < retries + 1:
                            delay = get_next_delay(_retry_delay)
                            logger.info(
                                "Retrying in %s seconds... (Attempt %s/%s)",
                                delay,
                                attempt,
                                retries,
                            )
                            time.sleep(delay)
                        else:
                            # Record single failure when all attempts fail
                            if circuit_breaker:
                                circuit_breaker.record_failure()
                            raise DequestError(
                                f"Dequest client failed after {retries} attempts: {e!s}",
                            ) from e
                    else:
                        if circuit_breaker:
                            circuit_breaker.record_failure()
                        raise DequestError(
                            f"Dequest client failed: {e!s}",
                        ) from e

            return None

        return wrapper

    return decorator
