"""
Cranberry error types and panic helpers.
"""

from __future__ import annotations


class CranberryPanic(RuntimeError):
    """Raised for programmer errors (bad configuration, field clashes, …)."""


class CranberryParseError(ValueError):
    """Raised when argv cannot be parsed according to the schema."""


def panic(message: str) -> None:
    """Raise a :class:`CranberryPanic` unconditionally."""
    raise CranberryPanic(message)
