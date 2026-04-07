class GatewayError(Exception):
    """Base error for gateway operations."""


class AuthError(GatewayError):
    """Raised for authentication failures."""


class ValidationError(GatewayError):
    """Raised for invalid user input."""


class NotFoundError(GatewayError):
    """Raised when a requested resource cannot be found."""


class ConflictError(GatewayError):
    """Raised when an operation conflicts with current data state."""
