import asyncio
import inspect
import json
from collections.abc import Callable, Iterator
from functools import wraps
from typing import TypeVar, Union

from dequest.cache import get_cache
from dequest.circuit_breaker import CircuitBreaker
from dequest.config import DequestConfig
from dequest.exceptions import DequestError
from dequest.http import ConsumerType, async_request
from dequest.utils import (
    AsyncLoopManager,
    extract_parameters,
    generate_cache_key,
    get_logger,
    get_next_delay,
)

from ._common import (
    _handle_circuit_breaker,
    _map_response,
    _prepare_headers,
    _resolve_optional_callable,
    _should_retry,
)

T = TypeVar("T")
logger = get_logger()
cache = get_cache()

background_tasks: set[asyncio.Task] = set()


async def _perform_request(
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
):
    method = method.upper()

    if (enable_cache or cache_ttl) and method != "GET":
        raise ValueError("Cache is only supported for GET requests.")

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

    response_data = await async_request(
        method,
        url,
        headers,
        json_body,
        params,
        data,
        timeout,
        consume,
    )

    if enable_cache:
        cache.set_key(
            cache_key,
            (json.dumps(response_data) if consume == ConsumerType.JSON else response_data),
            cache_ttl,
        )
        logger.info("Cached response for %s in %s", url, DequestConfig.CACHE_PROVIDER)

    return response_data


async def _execute_async_request(
    formatted_url: str,
    method: str,
    headers: dict[str, str],
    json_body: dict | None,
    query_params: dict | None,
    form_params: dict | None,
    timeout: int,
    enable_cache: bool,
    cache_ttl: int | None,
    consume: ConsumerType,
    dto_class: type[T] | None,
    source_field: str | None,
    retries: int,
    retry_on_exceptions: tuple[Exception, ...] | None,
    retry_delay: Union[float, Callable[[], Iterator]],
    giveup: Callable[[Exception], bool] | None,
    circuit_breaker: CircuitBreaker | None,
    callback: Callable[[Union[T, dict]], None] | None,
) -> T | dict:
    _retry_delay = _resolve_optional_callable(retry_delay)

    for attempt in range(1, retries + 2):
        try:
            response_data = await _perform_request(
                formatted_url,
                method,
                headers,
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

            result = _map_response(response_data, dto_class, source_field, consume)

            if callback:
                callback_result = callback(result)
                if asyncio.iscoroutine(callback_result):
                    await callback_result

            return result

        except Exception as error:
            if _should_retry(error, retry_on_exceptions, giveup) and attempt < retries + 1:
                logger.error("Dequest client error: %s", error)
                delay = get_next_delay(_retry_delay)
                logger.info(
                    "Retrying in %s seconds... (Attempt %s/%s)",
                    delay,
                    attempt,
                    retries,
                )
                await asyncio.sleep(delay)
                continue

            if circuit_breaker:
                circuit_breaker.record_failure()

            if _should_retry(error, retry_on_exceptions, giveup):
                raise DequestError(
                    f"Dequest client failed after {retries} attempts: {error!s}",
                ) from error

            raise DequestError(f"Dequest client failed: {error!s}") from error

    return None  # This line should never be reached


def async_client(
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
    callback: Callable[[Union[T, dict]], None] | None = None,
    consume: ConsumerType = ConsumerType.JSON,
):
    """
    A decorator to make asynchronous fire-and-forget HTTP requests without requiring the user to handle async execution.
    The decorated function should NOT be awaited. If awaiting is needed, use `async_await_client` instead.

    :param url: URL template with placeholders for path parameters.
    :param dto_class: The DTO class to map the response data.
    :param source_field: Source field to use for mapping response data. Leave None to map whole response.
    :param method: HTTP method (GET, POST, PUT, DELETE).
    :param timeout: Request timeout in seconds.
    :param retries: Number of retries on failure.
    :param retry_on_exceptions: Exceptions to retry on.
    :param retry_delay: Delay in seconds between retries. Can be a static value or a function returning iterator.
    :param giveup: Function to determine if the retry should be given up.
    :param auth_token: Optional Bearer Token (static string or function returning a string).
    :param api_key: Optional API key (static string or function returning a string).
    :param headers: Optional default headers (can be a dict or a function returning a dict).
    :param enable_cache: Whether to cache GET responses.
    :param cache_ttl: Cache expiration time in seconds.
    :param circuit_breaker: Instance of CircuitBreaker (optional).
    :param callback: Optional function to process the response when available.
    :param consume: Type of data to consume. ConsumerType.JSON, ConsumerType.XML or ConsumerType.TEXT
    """

    def decorator(func):
        signature = inspect.signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs) -> None:
            """
            Executes the decorated function asynchronously inside an event loop.
            The user does NOT need to `await` the function.
            """

            path_params, query_params, form_params, json_body = extract_parameters(
                signature,
                args,
                kwargs,
            )

            formatted_url = url.format(**path_params)

            request_headers = _prepare_headers(headers, auth_token, api_key)
            _retry_delay = _resolve_optional_callable(retry_delay)

            async def run_request():
                blocked, fallback_response = _handle_circuit_breaker(
                    circuit_breaker,
                    formatted_url,
                    args,
                    kwargs,
                    is_async=True,
                )
                if blocked:
                    if asyncio.iscoroutine(fallback_response):
                        task = asyncio.create_task(fallback_response)
                        background_tasks.add(task)
                        task.add_done_callback(background_tasks.discard)
                    return

                for attempt in range(1, retries + 2):  # 1st call + retries
                    try:
                        response_data = await _perform_request(
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

                        if dto_class:
                            dto_object = _map_response(
                                response_data,
                                dto_class,
                                source_field,
                                consume,
                            )
                            if callback:
                                task = asyncio.create_task(
                                    callback(dto_object),
                                )
                                background_tasks.add(task)
                                task.add_done_callback(background_tasks.discard)
                                return

                        if callback and response_data:
                            task = asyncio.create_task(callback(response_data))
                            background_tasks.add(task)
                            task.add_done_callback(background_tasks.discard)

                        return

                    except Exception as e:
                        if _should_retry(e, retry_on_exceptions, giveup):
                            logger.error("Dequest client error: %s", e)
                            if attempt < retries + 1:
                                delay = get_next_delay(_retry_delay)
                                logger.info(
                                    "Retrying in %s seconds... (Attempt %s/%s)",
                                    delay,
                                    attempt,
                                    retries,
                                )
                                await asyncio.sleep(delay)
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

            loop = AsyncLoopManager.get_event_loop()
            asyncio.run_coroutine_threadsafe(run_request(), loop)

        return wrapper

    return decorator


def async_await_client(
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
    callback: Callable[[Union[T, dict]], None] | None = None,
    consume: ConsumerType = ConsumerType.JSON,
):
    """
    A decorator to make asynchronous HTTP requests and return a result that can be awaited.
    The decorated function should be awaited inside an async function.

    :param url: URL template with placeholders for path parameters.
    :param dto_class: The DTO class to map the response data.
    :param source_field: Source field to use for mapping response data. Leave None to map whole response.
    :param method: HTTP method (GET, POST, PUT, DELETE).
    :param timeout: Request timeout in seconds.
    :param retries: Number of retries on failure.
    :param retry_on_exceptions: Exceptions to retry on.
    :param retry_delay: Delay in seconds between retries. Can be a static value or a function returning iterator.
    :param giveup: Function to determine if the retry should be given up.
    :param auth_token: Optional Bearer Token (static string or function returning a string).
    :param api_key: Optional API key (static string or function returning a string).
    :param headers: Optional default headers (can be a dict or a function returning a dict).
    :param enable_cache: Whether to cache GET responses.
    :param cache_ttl: Cache expiration time in seconds.
    :param circuit_breaker: Instance of CircuitBreaker (optional).
    :param callback: Optional function to process the response when available.
    :param consume: Type of data to consume. ConsumerType.JSON, ConsumerType.XML or ConsumerType.TEXT
    """

    def decorator(func):
        signature = inspect.signature(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if consume == ConsumerType.TEXT and dto_class:
                raise DequestError("ConsumerType.TEXT cannot be used with dto_class.")

            path_params, query_params, form_params, json_body = extract_parameters(
                signature,
                args,
                kwargs,
            )
            formatted_url = url.format(**path_params)
            request_headers = _prepare_headers(headers, auth_token, api_key)

            blocked, fallback_response = _handle_circuit_breaker(
                circuit_breaker,
                formatted_url,
                args,
                kwargs,
                is_async=True,
            )
            if blocked:
                if asyncio.iscoroutine(fallback_response):
                    return await fallback_response
                return fallback_response

            return await _execute_async_request(
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
                dto_class,
                source_field,
                retries,
                retry_on_exceptions,
                retry_delay,
                giveup,
                circuit_breaker,
                callback,
            )

        return wrapper

    return decorator
