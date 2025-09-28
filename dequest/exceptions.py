# Representation of httpx exceptions for dequest
# to prevent importing httpx directly to use in
# cases like retry_on_exceptions of retry
from httpx._exceptions import *  # noqa: F403


class DequestError(Exception):
    pass


class CircuitBreakerOpenError(DequestError):
    """Raised when the circuit breaker is OPEN and requests are blocked."""


class InvalidParameterValueError(DequestError):
    """Raised when a parameter value is invalid."""
