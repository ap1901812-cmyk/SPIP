class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ServiceUnavailableError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("SERVICE_UNAVAILABLE", message, 503)
