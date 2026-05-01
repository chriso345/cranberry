"""
Cranberry - a Python CLI framework.
"""

from __future__ import annotations

from cranberry.errors import CranberryPanic, CranberryParseError, panic
from cranberry.fields import FieldSpec, option, flag, arg, file, dir
from cranberry.enum import CranberryEnum, enum
from cranberry.style import Style
from cranberry.context import ParseContext
from cranberry.decorators import (
    app as _app_decorator,
    command,
    subcommand,
    description,
    help,
    no_help,
    version,
    style as _style_decorator,
    footer,
    globals as _globals_decorator,
)
from cranberry import parser as _parser_module


# ---------------------------------------------------------------------------
# Wrap decorators that have side-effects (registering with the parser module).
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# parse_args - the one function users call at runtime
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> ParseContext:
    """
    Parse *argv* (or :data:`sys.argv`) and return a :class:`ParseContext`.

    Must be called inside the function decorated with :func:`app`.
    """
    return _parser_module.parse_args(argv)


__all__ = [
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
