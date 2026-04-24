import asyncio
import collections
import hashlib
import inspect
import json
import logging
import threading
from dataclasses import dataclass
from typing import Any, TypeVar, get_origin, get_type_hints
from xml.etree.ElementTree import Element

from defusedxml import ElementTree

from dequest.exceptions import InvalidParameterValueError
from dequest.parameter_types import (
    PARAMETER_UNSET,
    FormParameter,
    JsonBody,
    ParameterDefinition,
    PathParameter,
    QueryParameter,
)

T = TypeVar("T")  # Generic Type for DTO
PARAMETER_TYPES = (PathParameter, QueryParameter, FormParameter, JsonBody)


@dataclass(frozen=True)
class ResolvedParameter:
    parameter_type: type[ParameterDefinition] | None
    base_type: type | None
    alias: str | None
    value: Any


class AsyncLoopManager:
    """Ensures a single background event loop runs in a dedicated thread."""

    _background_loop: asyncio.AbstractEventLoop | None = None
    _lock = threading.Lock()

    @classmethod
    def get_event_loop(cls) -> asyncio.AbstractEventLoop:
        """Returns an event loop that runs forever in a background thread."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            with cls._lock:
                if cls._background_loop is None:
                    cls._background_loop = asyncio.new_event_loop()
                    thread = threading.Thread(
                        target=cls._background_loop.run_forever,
                        daemon=True,
                    )
                    thread.start()
                return cls._background_loop


def generate_cache_key(url: str, params: dict[str, Any] | None) -> str:
    """Generates a unique cache key using URL and query parameters."""
    cache_data = {"url": url, "params": params}
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_string.encode()).hexdigest()


def map_json_to_dto(
    dto_class: type[T],
    data: dict[str, Any],
    source_field: str | None = None,
) -> T:
    source_data = data[source_field] if source_field else data

    return (
        [_map_json_to_dto(dto_class, item) for item in source_data]
        if isinstance(source_data, list)
        else _map_json_to_dto(dto_class, source_data)
    )


def _map_json_to_dto(dto_class: type[T], data: dict[str, Any]) -> T:
    dto_fields = get_type_hints(dto_class).keys()  # Get type hints for all fields
    init_params = inspect.signature(dto_class).parameters  # Get __init__ parameters

    mapped_data = {}
    for key in dto_fields:
        if key in data:
            field_value = data[key]
            field_annotation = get_type_hints(dto_class)[key]

            # Check if the field is a nested DTO
            if isinstance(field_annotation, type) and hasattr(
                field_annotation,
                "__annotations__",
            ):
                mapped_data[key] = map_json_to_dto(field_annotation, field_value)
            else:
                mapped_data[key] = field_value

    # Filter out attributes that are not in the constructor parameters
    init_data = {k: v for k, v in mapped_data.items() if k in init_params}

    return dto_class(**init_data)


def get_logger() -> logging.Logger:
    logger = logging.getLogger("dequest")
    logger.addHandler(logging.NullHandler())

    return logger


def map_xml_to_dto(
    dto_class: type[T],
    xml_data: str,
    source_field: str | None = None,
) -> T | list[T]:
    root = ElementTree.fromstring(xml_data)

    # If source_field is provided, use the child element as the root
    source_root = root.find(source_field) if source_field else root

    if source_field and source_root is None:
        raise ValueError(f"Source field '{source_field}' not found in the XML element.")

    # If multiple elements exist, return a list
    if len(source_root) > 1 and all(child.tag == source_root[0].tag for child in source_root):
        return [_parse_element(dto_class, child) for child in source_root]

    return _parse_element(dto_class, source_root)


def _parse_element(dto_class: type[T], element: Element) -> T:
    dto_fields = get_type_hints(dto_class).keys()
    init_params = inspect.signature(dto_class).parameters

    mapped_data = {}
    for key in dto_fields:
        if key in element.attrib:
            mapped_data[key] = element.attrib[key]
        else:
            child = element.find(key)
            if child is not None:
                field_annotation = get_type_hints(dto_class)[key]

                # Check if the field is a nested DTO
                if isinstance(field_annotation, type) and hasattr(
                    field_annotation,
                    "__annotations__",
                ):
                    mapped_data[key] = _parse_element(field_annotation, child)
                else:
                    mapped_data[key] = child.text

    # Filter out attributes that are not in the constructor parameters
    init_data = {k: v for k, v in mapped_data.items() if k in init_params}

    return dto_class(**init_data)


def _get_parameter_definition(param: inspect.Parameter) -> ParameterDefinition | None:
    return param.default if isinstance(param.default, ParameterDefinition) else None


def _get_annotation_origin(annotation: Any) -> Any:
    return get_origin(annotation) or annotation


def _is_parameter_type(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, PARAMETER_TYPES)


def _resolve_parameter_type(
    annotation: Any,
    parameter_definition: ParameterDefinition | None,
) -> type[ParameterDefinition] | None:
    if parameter_definition is not None:
        return type(parameter_definition)

    origin = _get_annotation_origin(annotation)
    return origin if _is_parameter_type(origin) else None


def _resolve_parameter_value(
    param_name: str,
    param_value: Any,
    parameter_definition: ParameterDefinition | None,
) -> Any:
    if parameter_definition is None or param_value is not parameter_definition:
        return param_value

    if parameter_definition.default is PARAMETER_UNSET:
        raise TypeError(f"Missing required argument: '{param_name}'")

    return parameter_definition.default


def _resolve_annotation_base_type(annotation: Any) -> type | None:
    if annotation is inspect.Parameter.empty:
        return None
    if isinstance(annotation, type) and not _is_parameter_type(annotation):
        return annotation
    return getattr(annotation, "__base_type__", None)


def _resolve_alias(annotation: Any, parameter_definition: ParameterDefinition | None) -> str | None:
    if parameter_definition is not None and parameter_definition.alias is not None:
        return parameter_definition.alias
    return getattr(annotation, "__alias__", None)


def _resolve_parameter(
    param_name: str,
    param: inspect.Parameter,
    param_value: Any,
) -> ResolvedParameter | None:
    annotation = param.annotation
    parameter_definition = _get_parameter_definition(param)

    if annotation is inspect.Parameter.empty and parameter_definition is None:
        return None

    return ResolvedParameter(
        parameter_type=_resolve_parameter_type(annotation, parameter_definition),
        base_type=_resolve_annotation_base_type(annotation),
        alias=_resolve_alias(annotation, parameter_definition),
        value=_resolve_parameter_value(param_name, param_value, parameter_definition),
    )


def _convert_parameter_value(param_name: str, param_value: Any, base_type: type | None) -> Any:
    if param_value is None or base_type is None:
        return param_value

    try:
        return base_type(param_value)
    except (ValueError, TypeError):
        raise InvalidParameterValueError(
            f"Invalid value for {param_name}: Expected {base_type}, got {type(param_value)}",
        ) from None


def _build_parameter_buckets() -> dict[type[ParameterDefinition], dict[str, Any]]:
    return {
        PathParameter: {},
        QueryParameter: {},
        FormParameter: {},
        JsonBody: {},
    }


def _get_parameter_bucket(
    parameter_type: type[ParameterDefinition] | None,
    parameter_buckets: dict[type[ParameterDefinition], dict[str, Any]],
) -> dict[str, Any] | None:
    if parameter_type is None:
        return None

    for marker_type, bucket in parameter_buckets.items():
        if issubclass(parameter_type, marker_type):
            return bucket

    return None


def extract_parameters(signature: inspect.Signature, args: tuple, kwargs: dict):
    bound_args = signature.bind(*args, **kwargs)
    bound_args.apply_defaults()
    parameter_buckets = _build_parameter_buckets()

    for param_name, param in signature.parameters.items():
        resolved_parameter = _resolve_parameter(
            param_name,
            param,
            bound_args.arguments.get(param_name),
        )
        if resolved_parameter is None:
            continue

        parameter_bucket = _get_parameter_bucket(
            resolved_parameter.parameter_type,
            parameter_buckets,
        )
        if parameter_bucket is None:
            continue

        param_key = resolved_parameter.alias if resolved_parameter.alias is not None else param_name
        parameter_bucket[param_key] = _convert_parameter_value(
            param_name,
            resolved_parameter.value,
            resolved_parameter.base_type,
        )

    return (
        parameter_buckets[PathParameter],
        parameter_buckets[QueryParameter],
        parameter_buckets[FormParameter],
        parameter_buckets[JsonBody],
    )


def get_next_delay(retry_delay: float | collections.abc.Iterator | None) -> float:
    delay_iterator = retry_delay if isinstance(retry_delay, collections.abc.Iterator) else None
    if delay_iterator:
        return next(delay_iterator)
    return retry_delay
