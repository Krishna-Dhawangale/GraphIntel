from typing import Any, Optional

from fastapi import HTTPException, status


class GraphIntelException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = "INTERNAL_ERROR",
        extra: Optional[dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.extra = extra or {}


class BadRequestException(GraphIntelException):
    def __init__(
        self,
        detail: str = "Bad request",
        error_code: str = "BAD_REQUEST",
        extra: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code,
            extra=extra,
        )


class UnauthorizedException(GraphIntelException):
    def __init__(
        self,
        detail: str = "Could not validate credentials",
        error_code: str = "UNAUTHORIZED",
        extra: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code,
            extra=extra,
        )


class ForbiddenException(GraphIntelException):
    def __init__(
        self,
        detail: str = "Access forbidden",
        error_code: str = "FORBIDDEN",
        extra: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, detail=detail, error_code=error_code, extra=extra
        )


class NotFoundException(GraphIntelException):
    def __init__(
        self,
        detail: str = "Resource not found",
        error_code: str = "NOT_FOUND",
        extra: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, detail=detail, error_code=error_code, extra=extra
        )


class PayloadTooLargeException(GraphIntelException):
    def __init__(
        self,
        detail: str = "File size exceeds the allowed limit",
        error_code: str = "PAYLOAD_TOO_LARGE",
        extra: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=detail,
            error_code=error_code,
            extra=extra,
        )


class UnprocessableEntityException(GraphIntelException):
    def __init__(
        self,
        detail: str = "Unprocessable entity",
        error_code: str = "UNPROCESSABLE_ENTITY",
        extra: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code=error_code,
            extra=extra,
        )


class TooManyRequestsException(GraphIntelException):
    def __init__(
        self,
        detail: str = "Rate limit exceeded. Please try again later.",
        error_code: str = "RATE_LIMIT_EXCEEDED",
        extra: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code=error_code,
            extra=extra,
        )


class InternalServerErrorException(GraphIntelException):
    def __init__(
        self,
        detail: str = "An unexpected error occurred. Please contact support.",
        error_code: str = "INTERNAL_SERVER_ERROR",
        extra: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code,
            extra=extra,
        )
