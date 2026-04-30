import asyncio
from collections.abc import Callable
from typing import TypeVar, Union

from dequest.cache import get_cache
from dequest.circuit_breaker import CircuitBreaker
from dequest.exceptions import CircuitBreakerOpenError
from dequest.http import ConsumerType
from dequest.utils import (
    get_logger,
    map_json_to_dto,
    map_xml_to_dto,
)

T = TypeVar("T")
logger = get_logger()
cache = get_cache()


def _resolve_optional_callable(value):
    return value() if callable(value) else value


def _prepare_headers(
    headers: Union[dict[str, str], Callable[[], dict[str, str]]] | None,
    auth_token: Union[str, Callable[[], str]] | None,
    api_key: Union[str, Callable[[], str]] | None,
) -> dict[str, str]:
    request_headers = _resolve_optional_callable(headers) or {}
    token_value = _resolve_optional_callable(auth_token)
    api_key_value = _resolve_optional_callable(api_key)

    if token_value:
        request_headers["Authorization"] = f"Bearer {token_value}"
    if api_key_value:
        request_headers["x-api-key"] = api_key_value

    return request_headers


def _should_retry(
    error: Exception,
    retry_on_exceptions: tuple[Exception, ...] | None,
    giveup: Callable[[Exception], bool] | None,
) -> bool:
    if retry_on_exceptions is None:
        return False

    should_retry = isinstance(error, retry_on_exceptions)
    if not should_retry:
        return False

    if giveup is None:
        return True

    return not giveup(error)


def _map_response(
    response_data: dict,
    dto_class: type[T] | None,
    source_field: str | None,
    consume: ConsumerType,
) -> T | dict:
    if dto_class is None:
        return response_data

    if consume == ConsumerType.JSON:
        return map_json_to_dto(dto_class, response_data, source_field)

    return map_xml_to_dto(dto_class, response_data)


def _handle_circuit_breaker(
    circuit_breaker: CircuitBreaker | None,
    formatted_url: str,
    args: tuple,
    kwargs: dict,
    is_async: bool = False,
):
    if circuit_breaker is None or circuit_breaker.allow_request():
        return False, None

    logger.warning("Circuit breaker blocking requests to %s", formatted_url)
    if circuit_breaker.fallback_function:
        result = circuit_breaker.fallback_function(*args, **kwargs)
        if is_async and asyncio.iscoroutine(result):
            return True, result
        return True, result

    raise CircuitBreakerOpenError(
        f"Circuit breaker is OPEN. Requests to {formatted_url} are blocked.",
    )
