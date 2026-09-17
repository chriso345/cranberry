"""
Cranberry - a Python CLI framework.
"""

from __future__ import annotations

from typing import Any, TypeVar, overload

from cranberry import parser as _parser_module
from cranberry.context import ParseContext
from cranberry.decorators import (
    app as _app_decorator,
)
from cranberry.decorators import (
    command,
    description,
    footer,
    help,
    no_help,
    subcommand,
    version,
)
from cranberry.decorators import (
    globals as _globals_decorator,
)
from cranberry.decorators import (
    style as _style_decorator,
)
from cranberry.enum import CranberryEnum, enum
from cranberry.errors import CranberryPanic, CranberryParseError, panic
from cranberry.fields import (
    Fields,
    FieldSpec,
    arg,
    dir,
    file,
    flag,
    option,
)
from cranberry.style import Style

G = TypeVar("G")


def app(name: str):
    """
    Mark a function as the CLI entry-point.

    Also registers it with the internal parser so :func:`parse_args` can
    discover the app metadata without requiring an explicit reference.
    """

    def decorator(fn):
        fn = _app_decorator(name)(fn)
        _parser_module._register_app(fn)
        return fn

    return decorator


def style(value):
    """
    Choose the rendering style and store it on the entry-point.

    Delegates to :func:`cranberry.decorators.style` and also caches the
    resolved :class:`Style` instance on the parser module for use in
    pre-parse error messages.
    """
    return _style_decorator(value)


def globals():
    """
    Mark a class as the global options namespace and register it with the parser.
    """

    def decorator(cls):
        cls = _globals_decorator()(cls)
        _parser_module._register_globals(cls)
        return cls

    return decorator


@overload
def parse_args(argv: list[str] | None = None) -> ParseContext[Any]: ...
@overload
def parse_args(
    argv: list[str] | None = None, *, globals_cls: type[G]
) -> ParseContext[G]: ...
def parse_args(
    argv: list[str] | None = None, *, globals_cls: type[Any] | None = None
) -> ParseContext[Any]:
    """
    Parse *argv* (or :data:`sys.argv`) and return a :class:`ParseContext`.

    Must be called inside the function decorated with :func:`app`. Pass
    ``globals_cls=Globals`` (the same class decorated with :func:`globals`)
    so type checkers infer ``ctx.globals`` as ``Globals`` instead of
    ``Any``:

    .. code-block:: python

        ctx = cb.parse_args(globals_cls=Globals)
        reveal_type(ctx.globals)  # Globals
    """
    if globals_cls is not None:
        return _parser_module.parse_args(argv, globals_cls=globals_cls)
    return _parser_module.parse_args(argv)


__all__ = [  # noqa: RUF022
    # errors
    "CranberryPanic",
    "CranberryParseError",
    "panic",
    # fields
    "FieldSpec",
    "option",
    "flag",
    "arg",
    "file",
    "dir",
    "Fields",
    # enum
    "CranberryEnum",
    "enum",
    # style
    "Style",
    # context
    "ParseContext",
    # decorators
    "app",
    "command",
    "subcommand",
    "description",
    "help",
    "no_help",
    "version",
    "style",
    "footer",
    "globals",
    # runtime
    "parse_args",
]
