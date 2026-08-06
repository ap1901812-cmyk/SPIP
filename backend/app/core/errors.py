from typing import Any, Optional


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: Optional[Any] = None) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)



class ServiceUnavailableError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("SERVICE_UNAVAILABLE", message, 503)


class UnauthenticatedError(AppError):
    def __init__(
        self, message: str = "Authentication credentials were not provided or are invalid."
    ) -> None:
        super().__init__("UNAUTHENTICATED", message, 401)


class UnauthorizedError(AppError):
    def __init__(
        self, message: str = "Insufficient permissions to perform this action."
    ) -> None:
        super().__init__("FORBIDDEN", message, 403)


class RateLimitExceededError(AppError):
    def __init__(self, message: str = "Too many requests. Please try again later.") -> None:
        super().__init__("RATE_LIMIT_EXCEEDED", message, 429)


class BadRequestError(AppError):
    def __init__(self, message: str = "Invalid request parameters.") -> None:
        super().__init__("BAD_REQUEST", message, 400)
