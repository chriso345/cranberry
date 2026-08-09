"""
Cranberry decorator API.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from cranberry.errors import panic

F = TypeVar("F", bound=Callable[..., Any])
C = TypeVar("C", bound=type)


# Internal helper
def _meta(obj: Any) -> dict[str, Any]:
    """Return (and lazily create) the ``__cb_meta__`` dict on *obj*."""
    if not hasattr(obj, "__cb_meta__"):
        try:
            obj.__cb_meta__ = {}
        except AttributeError:
            panic(
                f"Cannot attach __cb_meta__ to {obj!r}. "
                "Make sure you are decorating a class or function."
            )
    return obj.__cb_meta__  # type: ignore[return-value]


# @cb.command
def command(name: str) -> Callable[[C], C]:
    """
    Mark a class as a named CLI subcommand.

    .. code-block:: python

        @cb.command("sub")
        class SubCommand:
            ...
    """

    def decorator(cls: C) -> C:
        m = _meta(cls)
        m["type"] = "command"
        m["name"] = name
        m.setdefault("subcommands", [])
        return cls

    return decorator


# @cb.subcommand
def subcommand(*subs: type) -> Callable[[Any], Any]:
    """
    Register one or more subcommand classes on a command or app entry-point.

    Can be repeated; subsequent calls append to the existing list.

    .. code-block:: python

        @cb.subcommand(SubCommand, AlternateCommand)
        def main(): ...
    """

    def decorator(target: Any) -> Any:
        m = _meta(target)
        m.setdefault("subcommands", []).extend(subs)
        return target

    return decorator


# @cb.description
def description(text: str) -> Callable[[Any], Any]:
    """Attach a description string to a command or the app entry-point."""

    def decorator(target: Any) -> Any:
        _meta(target)["description"] = text
        return target

    return decorator


# @cb.help
def help(
    *,
    flag: bool = True,
    subcommand: bool = False,
    message: str | None = None,
) -> Callable[[Any], Any]:
    """
    Configure the built-in help behaviour.

    Parameters
    ----------
    flag:
        When *True* (default) a ``-h``/``--help`` flag is auto-generated.
    subcommand:
        When *True* a ``help`` subcommand is also registered.
    message:
        Override the default help text with a custom string.
    """

    def decorator(target: Any) -> Any:
        _meta(target)["help"] = {
            "flag": flag,
            "subcommand": subcommand,
            "message": message,
        }
        return target

    return decorator


def no_help() -> Callable[[Any], Any]:
    """Disable all built-in help output."""

    def decorator(target: Any) -> Any:
        _meta(target)["help"] = {"flag": False, "subcommand": False, "message": None}
        return target

    return decorator


# @cb.version
def version(
    ver: str | bool = True,
    flag: bool = True,
    subcommand: bool = False,
) -> Callable[[Any], Any]:
    """
    Attach a version string (or auto-detect from package metadata).

    Parameters
    ----------
    ver:
        A literal version string such as ``"0.1.0"``, or *True* to read the
        version from :func:`importlib.metadata.version` using the app name.
    flag:
        When *True* (default) a ``-V``/``--version`` flag is auto-generated.
    subcommand:
        When *True* a ``version`` subcommand is also registered.
    """

    def decorator(target: Any) -> Any:
        _meta(target)["version"] = {"flag": flag, "subcommand": subcommand, "ver": ver}
        return target

    return decorator


# @cb.style
def style(value: str | type) -> Callable[[Any], Any]:
    """
    Choose a rendering style for help output.

    Parameters
    ----------
    value:
        ``"plain"``, ``"colorful"``, ``"fancy"``, or a custom
        :class:`~cranberry.style.Style` subclass.
    """

    def decorator(target: Any) -> Any:
        _meta(target)["style"] = value
        return target

    return decorator


# @cb.footer
def footer(text: str) -> Callable[[Any], Any]:
    """Attach a message printed after every help block."""

    def decorator(target: Any) -> Any:
        _meta(target)["footer_message"] = text
        return target

    return decorator


# @cb.app
def app(name: str) -> Callable[[F], F]:
    """
    Mark a function as the application entry-point and give the app a name.

    .. code-block:: python

        @cb.app("cranberry")
        def main(): ...
    """

    def decorator(fn: F) -> F:
        m = _meta(fn)
        m["type"] = "app"
        m["name"] = name
        m.setdefault("subcommands", [])
        return fn

    return decorator


# @cb.globals
def globals() -> Callable[[C], C]:
    """
    Mark a class as the global options/flags namespace.

    Its fields are flattened into :class:`~cranberry.context.ParseContext`
    so they are accessible as ``ctx.<field_name>``.

    .. code-block:: python

        @cb.globals()
        class CbGlobals:
            global_flag: bool = cb.flag("-g", "--global-flag", ...)
    """

    def decorator(cls: C) -> C:
        cls.__cb_globals__ = True  # type: ignore[attr-defined]
        return cls

    return decorator
