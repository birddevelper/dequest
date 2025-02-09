import hashlib
import json
from typing import Any, Optional, TypeVar

T = TypeVar("T")  # Generic Type for DTO


def generate_cache_key(url: str, params: Optional[dict[str, Any]]) -> str:
    """Generates a unique cache key using URL and query parameters."""
    cache_data = {"url": url, "params": params}
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_string.encode()).hexdigest()


def map_to_dto(dto_class: type[T], data: dict[str, Any]) -> T:
    dto_fields = dto_class.__annotations__.keys()

    mapped_data = {}
    for key in dto_fields:
        if key in data:
            field_value = data[key]
            field_annotation = dto_class.__annotations__[key]

            # Check if the field is a nested DTO
            if isinstance(field_annotation, type) and hasattr(
                field_annotation,
                "__annotations__",
            ):
                mapped_data[key] = map_to_dto(field_annotation, field_value)
            else:
                mapped_data[key] = field_value

    return dto_class(**mapped_data)
