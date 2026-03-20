"""Custom exceptions for VisionAudioForge SDK."""


class VAFError(Exception):
    """Base exception for VisionAudioForge SDK."""

    def __init__(self, message: str, status_code: int | None = None, detail: object = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class AuthenticationError(VAFError):
    """Raised on 401 Unauthorized responses."""

    def __init__(self, message: str = "Authentication failed", detail: object = None):
        super().__init__(message, status_code=401, detail=detail)


class PermissionDeniedError(VAFError):
    """Raised on 403 Forbidden responses."""

    def __init__(self, message: str = "Permission denied", detail: object = None):
        super().__init__(message, status_code=403, detail=detail)


class NotFoundError(VAFError):
    """Raised on 404 Not Found responses."""

    def __init__(self, message: str = "Resource not found", detail: object = None):
        super().__init__(message, status_code=404, detail=detail)


class ValidationError(VAFError):
    """Raised on 422 Unprocessable Entity responses."""

    def __init__(self, message: str = "Validation error", detail: object = None):
        super().__init__(message, status_code=422, detail=detail)


class RateLimitError(VAFError):
    """Raised on 429 Too Many Requests responses."""

    def __init__(self, message: str = "Rate limit exceeded", detail: object = None):
        super().__init__(message, status_code=429, detail=detail)


class ServerError(VAFError):
    """Raised on 500 Internal Server Error responses."""

    def __init__(self, message: str = "Internal server error", detail: object = None):
        super().__init__(message, status_code=500, detail=detail)
