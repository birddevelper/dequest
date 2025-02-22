class DequestError(Exception):
    pass


class CircuitBreakerOpenError(DequestError):
    """Raised when the circuit breaker is OPEN and requests are blocked."""
