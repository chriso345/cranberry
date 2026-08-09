"""
Cranberry enum support.
"""

from __future__ import annotations

from typing import Any

from cranberry.errors import panic


class CranberryEnum:
    """
    Base class injected into every class decorated with ``@cb.enum``.

    Instances are created by the parser via :meth:`from_value`.
    """

    # Populated by the decorator.
    _members: dict[str, str]
    _strict: bool
    _value: str

    def __init__(self, value: str) -> None:
        self._value = value

    # Construction
    @classmethod
    def from_value(cls, raw: str) -> CranberryEnum:
        """Coerce a raw string into an enum member."""
        for member_value in cls._members.values():
            if member_value == raw:
                instance = cls.__new__(cls)
                instance._value = member_value
                return instance

        if not cls._strict:
            instance = cls.__new__(cls)
            instance._value = raw
            return instance

        valid = ", ".join(cls._members.values())
        raise ValueError(
            f"Invalid value {raw!r} for {cls.__name__}. Valid values: {valid}"
        )

    # Dunder helpers
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value!r})"

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CranberryEnum):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)


def enum(*, strict: bool = True) -> Any:
    """
    Class decorator that turns a plain class into a Cranberry enum.

    Parameters
    ----------
    strict:
        When *True* (the default) only the explicitly declared values are
        accepted.  When *False* an ``__UNKNOWN__`` member is added for any
        value that does not match a declared member.
    """

    def decorator(cls: type) -> type:
        # Gather declared string members (skip dunder attrs).
        members: dict[str, str] = {}
        for attr, value in vars(cls).items():
            if attr.startswith("_"):
                continue
            if not isinstance(value, str):
                panic(
                    f"@cb.enum: all members of {cls.__name__!r} must be plain "
                    f"strings, but {attr!r} has value {value!r}."
                )
            members[attr] = value

        if not members:
            panic(f"@cb.enum: {cls.__name__!r} has no string members.")

        if not strict:
            members["__UNKNOWN__"] = "__UNKNOWN__"

        # Build a new class that inherits from CranberryEnum.
        new_cls = type(
            cls.__name__,
            (CranberryEnum,),
            {
                "_members": members,
                "_strict": strict,
                **{attr: val for attr, val in members.items()},
                "__module__": cls.__module__,
                "__qualname__": cls.__qualname__,
                "__doc__": cls.__doc__,
            },
        )
        return new_cls

    return decorator
