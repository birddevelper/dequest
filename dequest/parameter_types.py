from typing import Generic, TypeVar

P = TypeVar("P")


class ParameterType(Generic[P]):
    """Base class for parameter type annotations."""

    def __init__(self, value: P):
        self.value = value


class PathParameter(ParameterType[P]):
    """Represents a URL path parameter."""


class QueryParameter(ParameterType[P]):
    """Represents a query parameter."""


class FormParameter(ParameterType[P]):
    """Represents a form-encoded request body parameter."""


class JsonBody(ParameterType[P]):
    """Represents a JSON request body."""
