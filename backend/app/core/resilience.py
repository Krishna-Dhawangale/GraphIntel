import asyncio
import functools
import logging
from typing import Any, Callable, Tuple, Type

logger = logging.getLogger(__name__)


# Error Classification Hierarchy
class ResilientBaseException(Exception):
    """Base exception for resilience classification."""
    def __init__(self, message: str, is_retryable: bool = False, original_exception: Exception = None):
        super().__init__(message)
        self.message = message
        self.is_retryable = is_retryable
        self.original_exception = original_exception


class TransientError(ResilientBaseException):
    """Temporary failures like network glitches, 503 Service Unavailable, rate limits that can be retried."""
    def __init__(self, message: str, original_exception: Exception = None):
        super().__init__(message, is_retryable=True, original_exception=original_exception)


class PermanentError(ResilientBaseException):
    """Non-retryable business logic failures, bad inputs, 4xx responses."""
    def __init__(self, message: str, original_exception: Exception = None):
        super().__init__(message, is_retryable=False, original_exception=original_exception)


class ValidationError(PermanentError):
    """Validation failure on schemas or models."""
    pass


class AuthenticationError(PermanentError):
    """Authentication or token credential failure."""
    pass


class AuthorizationError(PermanentError):
    """Insufficient privileges / RBAC permission violation."""
    pass


class ProviderError(ResilientBaseException):
    """External provider errors (LLM API, embedding service, remote API)."""
    def __init__(self, message: str, is_retryable: bool = True, original_exception: Exception = None):
        super().__init__(message, is_retryable=is_retryable, original_exception=original_exception)


class InfrastructureError(ResilientBaseException):
    """Database, cache, vector store, or graph store infrastructure timeout or connection drop."""
    def __init__(self, message: str, is_retryable: bool = True, original_exception: Exception = None):
        super().__init__(message, is_retryable=is_retryable, original_exception=original_exception)


async def execute_with_retry(
    coro_func: Callable[..., Any],
    *args,
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    timeout: float = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        TransientError,
        ProviderError,
        InfrastructureError,
        asyncio.TimeoutError,
        ConnectionError,
    ),
    **kwargs,
) -> Any:
    """
    Executes an asynchronous function with exponential backoff retries and timeout.
    Permanent errors or unlisted exceptions fail immediately without retrying.
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            if timeout:
                return await asyncio.wait_for(coro_func(*args, **kwargs), timeout=timeout)
            else:
                return await coro_func(*args, **kwargs)
        except PermanentError as pe:
            # Permanent errors are never retried
            logger.debug(f"Permanent error encountered: {pe}. Not retrying.")
            raise
        except retryable_exceptions as e:
            last_exception = e
            if attempt == max_retries:
                logger.warning(f"Exceeded max retries ({max_retries}) for {coro_func.__name__}: {e}")
                raise
            logger.info(
                f"Attempt {attempt}/{max_retries} failed for {coro_func.__name__}: {e}. Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)
            delay *= backoff_factor
        except Exception as e:
            # Non-retryable general exception
            logger.error(f"Unretryable error in {coro_func.__name__}: {e}")
            raise

    if last_exception:
        raise last_exception


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    timeout: float = None,
):
    """Decorator version of execute_with_retry."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await execute_with_retry(
                func,
                *args,
                max_retries=max_retries,
                initial_delay=initial_delay,
                backoff_factor=backoff_factor,
                timeout=timeout,
                **kwargs,
            )
        return wrapper
    return decorator
