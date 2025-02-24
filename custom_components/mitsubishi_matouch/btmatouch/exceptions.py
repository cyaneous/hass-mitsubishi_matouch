"""Exceptions for the btmatouch library."""

__all__ = [
    "MAException",
    "MAConnectionException",
    "MARequestException",
    "MAAlreadyAwaitingResponseException",
    "MATimeoutException",
    "MAStateException",
    "MAInternalException",
    "MAResponseException",
    "MAAuthException",
]


class MAException(Exception):
    """Base exception for the btmatouch library."""


class MAConnectionException(MAException):
    """Exception for connection errors."""


class MARequestException(MAException):
    """Exception for request errors."""


class MAAlreadyAwaitingResponseException(MAException):
    """Exception for requests that are already awaiting a response."""


class MATimeoutException(MAException):
    """Exception for timeouts."""


class MAStateException(MAException):
    """Exception for invalid states."""


class MAInternalException(MAException):
    """Exception for internal errors."""


class MAResponseException(MAException):
    """Exception for response errors."""

class MAAuthException(MAException):
    """Exception for auth errors."""
