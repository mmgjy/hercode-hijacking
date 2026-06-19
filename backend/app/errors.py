"""Domain error codes and the application exception type.

Error codes are stable strings the frontend can branch on. They are surfaced in
API responses and persisted on source/scan records so partial failures are
inspectable.
"""
from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    INVALID_SOURCE_SET = "INVALID_SOURCE_SET"
    SOURCE_NOT_ALLOWED = "SOURCE_NOT_ALLOWED"
    SOURCE_TIMEOUT = "SOURCE_TIMEOUT"
    SOURCE_BLOCKED = "SOURCE_BLOCKED"
    CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
    HTTP_ERROR = "HTTP_ERROR"
    NO_SIGNALS_FOUND = "NO_SIGNALS_FOUND"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    NO_QUALIFYING_CLUSTERS = "NO_QUALIFYING_CLUSTERS"
    SWISS_SCAN_PARTIAL = "SWISS_SCAN_PARTIAL"
    NO_PRODUCTS_FOUND = "NO_PRODUCTS_FOUND"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RECOMMENDATION_INCOMPLETE = "RECOMMENDATION_INCOMPLETE"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class AppError(Exception):
    """Raised for expected, client-facing failures."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
            }
        }
