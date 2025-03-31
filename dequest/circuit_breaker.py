import time
from collections.abc import Callable
from enum import Enum
from typing import Any, Optional

from dequest.utils import get_logger

logger = get_logger()


class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"  # Allowing a single test request


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        fallback_function: Optional[Callable[[], Any]] = None,
    ):
        """
        :param failure_threshold: Number of consecutive failures before switching to OPEN state
        :param recovery_timeout: Time in seconds before allowing a test request after breaker is OPEN
        :param fallback_function: Function to execute when circuit breaker is OPEN (optional).
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.fallback_function = fallback_function
        self.failures = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

    def allow_request(self) -> bool:
        """Determines if a request is allowed based on the breaker state."""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN  # Allow a test request
                return True
            return False  # Still in OPEN state, block requests
        return True  # Requests allowed in CLOSED and HALF-OPEN state

    def record_failure(self):
        """Records a failure and potentially opens the circuit."""
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.last_failure_time = time.time()
            logger.warning("Circuit breaker OPEN: Too many failures!")

    def record_success(self):
        """Resets failure count and closes the circuit breaker."""
        self.failures = 0
        self.state = CircuitBreakerState.CLOSED

    def get_state(self) -> CircuitBreakerState:
        """Returns the current state of the circuit breaker."""
        return self.state
