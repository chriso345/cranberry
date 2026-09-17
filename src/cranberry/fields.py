"""
Cranberry field specification and factory functions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, dataclass_transform

_UNSET: Any = object()


@dataclass
class FieldSpec:
    """
    Describes a single CLI field.

    Attributes
    ----------
    kind:
        One of ``"arg"``, ``"option"``, ``"flag"``, ``"file"``, ``"dir"``.
    short:
        Short flag string, e.g. ``"-o"``.
    long:
        Long flag string, e.g. ``"--option"``.
    help:
        Human-readable description shown in the help output.
    default:
        Default value.
    type:
        Python type used to coerce the raw string value.  Inferred from the
        class annotation when ``None``.
    count:
        For ``"arg"`` fields only.  ``1`` means a single value, ``None`` means
        unlimited (``*``), any positive integer means exactly that many.
    enforce_count:
        When *True* the parser raises an error if fewer than ``count`` values
        are supplied (only meaningful when ``count > 1`` or ``count is None``).
    validate:
        An optional ``(predicate, error_message)`` pair.  The predicate
        receives the *coerced* value and must return ``True`` when valid.
    exists:
        For ``"file"`` / ``"dir"`` fields only.  When *True* the parser
        verifies that the path exists on disk.
    """

    kind: str  # "arg" | "option" | "flag" | "file" | "dir"
    short: str | None = None
    long: str | None = None
    help: str = ""
    default: Any = field(default_factory=lambda: None)
    stackable: bool = False  # for flags only
    type: Any = None  # filled in by registry from the class annotation
    required: bool = False  # True when the factory call omitted `default=`
    # arg-specific
    count: int | None = 1
    enforce_count: bool = False
    # validation
    validate: tuple[Callable[[Any], bool], str] | None = None
    exists: bool = False

    # Convenience helpers
    @property
    def is_required(self) -> bool:
        """Return *True* when no default has been supplied."""
        return self.required

    @property
    def dest(self) -> str | None:
        """
        Derive the Python attribute name from the long flag.

        Returns ``None`` for positional ``"arg"`` fields (the registry
        supplies the attribute name from the annotation key instead).
        """
        if self.long is None:
            return None
        return self.long.lstrip("-").replace("-", "_")

    @property
    def metavar(self) -> str:
        """Return an upper-cased display name for help text."""
        if self.long:
            return self.long.lstrip("-").upper().replace("-", "_")
        if self.short:
            return self.short.lstrip("-").upper()
        return "VALUE"


def option(
    short: str | None,
    long: str | None,
    *,
    help: str = "",
    default: Any = _UNSET,
    type: Any = None,
    validate: tuple[Callable[[Any], bool], str] | None = None,
) -> Any:
    """
    Declare a named option that accepts a value (``-o VALUE`` / ``--option VALUE``).

    Omit ``default`` to make the field required - both at the CLI (it's
    marked required in ``--help``) and when constructing the class
    manually (``cb.Fields.__init__`` raises if it's missing, and type
    checkers flag a missing-argument error).
    """
    return FieldSpec(
        kind="option",
        short=short,
        long=long,
        help=help,
        default=None if default is _UNSET else default,
        type=type,
        required=default is _UNSET,
        validate=validate,
    )


def flag(
    short: str | None,
    long: str | None,
    *,
    help: str = "",
    default: bool = False,
    stackable: bool = False,
) -> Any:
    """Declare a boolean flag that stores *True* when present (``-f`` / ``--flag``)."""
    return FieldSpec(
        kind="flag",
        short=short,
        long=long,
        help=help,
        default=default,
        stackable=stackable,
        type=bool,
    )


def arg(
    *,
    help: str = "",
    default: Any = _UNSET,
    type: Any = None,
    count: int | None = 1,
    enforce_count: bool = False,
    validate: tuple[Callable[[Any], bool], str] | None = None,
) -> Any:
    """Declare a positional argument. Omit ``default`` to make it required."""
    return FieldSpec(
        kind="arg",
        help=help,
        default=None if default is _UNSET else default,
        type=type,
        required=default is _UNSET,
        count=count,
        enforce_count=enforce_count,
        validate=validate,
    )


def file(
    short: str | None,
    long: str | None,
    *,
    help: str = "",
    default: Any = _UNSET,
    exists: bool = False,
    validate: tuple[Callable[[Any], bool], str] | None = None,
) -> Any:
    """
    Declare an option whose value must be a filesystem path to a file.

    Omit ``default`` to make the field required.
    """
    return FieldSpec(
        kind="file",
        short=short,
        long=long,
        help=help,
        default=None if default is _UNSET else default,
        type=str,
        required=default is _UNSET,
        exists=exists,
        validate=validate,
    )


def dir(
    short: str | None,
    long: str | None,
    *,
    help: str = "",
    default: Any = _UNSET,
    exists: bool = False,
    validate: tuple[Callable[[Any], bool], str] | None = None,
) -> Any:
    """
    Declare an option whose value must be a filesystem path to a directory.

    Omit ``default`` to make the field required.
    """
    return FieldSpec(
        kind="dir",
        short=short,
        long=long,
        help=help,
        default=None if default is _UNSET else default,
        type=str,
        required=default is _UNSET,
        exists=exists,
        validate=validate,
    )


@dataclass_transform(
    eq_default=False,
    kw_only_default=True,
    field_specifiers=(option, arg, file, dir),
)
class Fields:
    """
    Base class for any class that declares Cranberry fields.
    """

    subcommand: Any | None = None

    def __init__(self, **kwargs: Any) -> None:
        _init_from_fields(self, kwargs)


def _init_from_fields(instance: Any, kwargs: dict[str, Any]) -> None:
    from cranberry.errors import panic  # local import avoids a cycle
    from cranberry.registry import collect_fields  # local import avoids a cycle

    cls = type(instance)
    fields = collect_fields(cls)
    missing = []
    for name, spec in fields.items():
        if name in kwargs:
            setattr(instance, name, kwargs.pop(name))
        elif spec.required:
            missing.append(name)
        else:
            setattr(instance, name, spec.default)

    if missing:
        panic(
            f"{cls.__name__}() missing required argument(s): "
            + ", ".join(repr(m) for m in missing)
        )
    if kwargs:
        panic(
            f"{cls.__name__}() got unexpected keyword argument(s): "
            + ", ".join(repr(k) for k in kwargs)
        )
