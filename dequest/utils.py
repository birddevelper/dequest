import asyncio
import hashlib
import inspect
import json
import logging
import threading
from typing import Any, Optional, TypeVar, get_type_hints

T = TypeVar("T")  # Generic Type for DTO


class AsyncLoopManager:
    """Ensures a single background event loop runs in a dedicated thread."""

    _background_loop: Optional[asyncio.AbstractEventLoop] = None
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


def generate_cache_key(url: str, params: Optional[dict[str, Any]]) -> str:
    """Generates a unique cache key using URL and query parameters."""
    cache_data = {"url": url, "params": params}
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_string.encode()).hexdigest()


def map_to_dto(dto_class: type[T], data: dict[str, Any]) -> T:
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
                mapped_data[key] = map_to_dto(field_annotation, field_value)
            else:
                mapped_data[key] = field_value

    # Filter out attributes that are not in the constructor parameters
    init_data = {k: v for k, v in mapped_data.items() if k in init_params}

    return dto_class(**init_data)


def get_logger() -> logging.Logger:
    logger = logging.getLogger("dequest")
    logger.addHandler(logging.NullHandler())

    return logger
