"""
Cranberry argv parser.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from cranberry.context import ParseContext
from cranberry.errors import CranberryParseError, panic
from cranberry.fields import FieldSpec
from cranberry.registry import collect_fields, check_global_clashes
from cranberry.style import Style, resolve_style
from cranberry.help_ import render_help, _cmd_name


# ---------------------------------------------------------------------------
# Module-level state - set by the @cb.app / @cb.globals decorators
# ---------------------------------------------------------------------------
_app_fn: Any = None
_globals_cls: type | None = None


def _register_app(fn: Any) -> None:
    global _app_fn
    _app_fn = fn


def _register_globals(cls: type) -> None:
    global _globals_cls
    _globals_cls = cls


# ---------------------------------------------------------------------------
# Coercion / validation helpers
# ---------------------------------------------------------------------------
def _coerce(raw: str, spec: FieldSpec, attr_name: str) -> Any:
    """Coerce *raw* string to *spec.type*, applying validation."""
    from cranberry.enum import CranberryEnum

    tp = spec.type or str

    try:
        if isinstance(tp, type) and issubclass(tp, CranberryEnum):
            value = tp.from_value(raw)
        elif tp is bool:
            value = raw.lower() not in ("0", "false", "no", "off")
        else:
            value = tp(raw)
    except (ValueError, TypeError) as exc:
        raise CranberryParseError(
            f"Invalid value {raw!r} for argument {attr_name!r}: {exc}"
        ) from exc

    if spec.validate:
        predicate, message = spec.validate
        if not predicate(value):
            raise CranberryParseError(f"Validation failed for {attr_name!r}: {message}")

    if spec.kind == "file" and spec.exists:
        if not os.path.isfile(str(value)):
            raise CranberryParseError(f"File not found for {attr_name!r}: {value!r}")

    if spec.kind == "dir" and spec.exists:
        if not os.path.isdir(str(value)):
            raise CranberryParseError(
                f"Directory not found for {attr_name!r}: {value!r}"
            )

    return value


# ---------------------------------------------------------------------------
# Named-flag / positional arg parser for a single command
# ---------------------------------------------------------------------------
def _parse_command_argv(
    argv: list[str],
    fields: dict[str, FieldSpec],
    *,
    command_name: str,
    subcommands: list[type],
    style: Style,
    help_cfg: dict[str, Any],
    global_fields: dict[str, FieldSpec],
    app_name: str,
    footer_msg: str | None,
    parent_command: str | None = None,
) -> tuple[dict[str, Any], list[str], type | None]:
    """
    Parse *argv* for a single command layer.

    Returns
    -------
    values:
        Resolved field values keyed by attribute name.
    remaining:
        Any argv tokens that were not consumed (passed to a child parser).
    matched_sub_cls:
        The subcommand class whose name was encountered, if any.
    """
    # Build lookup maps: flag string -> (attr_name, FieldSpec)
    flag_map: dict[str, tuple[str, FieldSpec]] = {}
    for attr_name, spec in fields.items():
        if spec.kind == "arg":
            continue
        if spec.short:
            flag_map[spec.short] = (attr_name, spec)
        if spec.long:
            flag_map[spec.long] = (attr_name, spec)

    # Sub-command name -> class
    sub_map: dict[str, type] = {_cmd_name(s): s for s in subcommands}
    has_help_sub = help_cfg.get("subcommand", False)
    has_help_flag = help_cfg.get("flag", True)

    values: dict[str, Any] = {}
    positional_specs = [(n, s) for n, s in fields.items() if s.kind == "arg"]
    positional_values: dict[str, list[str]] = {n: [] for n, _ in positional_specs}
    pos_index = 0  # which positional spec we are currently filling

    matched_sub_cls: type | None = None
    remaining: list[str] = []

    i = 0
    while i < len(argv):
        token = argv[i]

        # --help / -h
        if has_help_flag and token in ("-h", "--help"):
            _print_help_and_exit(
                app_name=app_name,
                command_name=command_name,
                global_fields=global_fields,
                command_fields=fields,
                subcommands=subcommands,
                help_cfg=help_cfg,
                footer_msg=footer_msg,
                style=style,
                parent_command=parent_command,
            )

        # help subcommand token
        if has_help_sub and token == "help" and pos_index == 0 and not values:
            _print_help_and_exit(
                app_name=app_name,
                command_name=command_name,
                global_fields=global_fields,
                command_fields=fields,
                subcommands=subcommands,
                help_cfg=help_cfg,
                footer_msg=footer_msg,
                style=style,
                parent_command=parent_command,
            )

        # subcommand dispatch
        if token in sub_map:
            matched_sub_cls = sub_map[token]
            remaining = argv[i + 1 :]
            break

        # named flag / option
        if token.startswith("-") and token in flag_map:
            attr_name, spec = flag_map[token]
            if spec.kind == "flag":
                values[attr_name] = True
                i += 1
            else:
                if i + 1 >= len(argv):
                    raise CranberryParseError(f"Flag {token!r} requires a value.")
                values[attr_name] = _coerce(argv[i + 1], spec, attr_name)
                i += 2
            continue

        # unknown flag
        if token.startswith("-"):
            raise CranberryParseError(f"Unknown flag: {token!r}")

        # positional
        if pos_index < len(positional_specs):
            attr_name, spec = positional_specs[pos_index]
            positional_values[attr_name].append(token)
            # Advance to the next spec unless this one is multi-value.
            if spec.count == 1:
                pos_index += 1
            elif spec.count is not None:
                if len(positional_values[attr_name]) >= spec.count:
                    pos_index += 1
            # count=None → unlimited, stay on this spec
        else:
            raise CranberryParseError(f"Unexpected positional argument: {token!r}")

        i += 1

    # Resolve positional specs
    for attr_name, spec in positional_specs:
        raw_list = positional_values[attr_name]

        if spec.count == 1:
            if not raw_list:
                if spec.is_required:
                    raise CranberryParseError(
                        f"Missing required positional argument: {attr_name!r}"
                    )
                values[attr_name] = spec.default
            else:
                values[attr_name] = _coerce(raw_list[0], spec, attr_name)
        else:
            # multi-value
            if spec.enforce_count and spec.count is not None:
                if len(raw_list) != spec.count:
                    raise CranberryParseError(
                        f"Argument {attr_name!r} expects exactly {spec.count} "
                        f"value(s), got {len(raw_list)}."
                    )
            if not raw_list and spec.is_required:
                raise CranberryParseError(
                    f"Missing required positional argument: {attr_name!r}"
                )
            values[attr_name] = [_coerce(r, spec, attr_name) for r in raw_list]

    # Apply defaults for missing named fields
    for attr_name, spec in fields.items():
        if spec.kind == "arg":
            continue
        if attr_name not in values:
            if spec.is_required:
                flag_str = spec.long or spec.short or attr_name
                raise CranberryParseError(f"Missing required option: {flag_str!r}")
            values[attr_name] = spec.default

    return values, remaining, matched_sub_cls


def _print_help_and_exit(
    *,
    app_name: str,
    command_name: str | None,
    global_fields: dict[str, FieldSpec],
    command_fields: dict[str, FieldSpec],
    subcommands: list[type],
    help_cfg: dict[str, Any],
    footer_msg: str | None,
    style: Style,
    parent_command: str | None,
) -> None:
    from cranberry.help_ import render_help

    text = render_help(
        app_name=app_name,
        command_name=command_name,
        description=None,  # filled in by caller if needed
        global_fields=global_fields,
        command_fields=command_fields,
        subcommands=subcommands,
        has_help_flag=help_cfg.get("flag", True),
        has_help_subcommand=help_cfg.get("subcommand", False),
        has_version_flag=False,  # version info is not relevant on subcommand help pages
        has_version_subcommand=False,
        footer_msg=footer_msg,
        style=style,
        parent_command=parent_command,
    )
    sys.stdout.write(text)
    sys.exit(0)


# ---------------------------------------------------------------------------
# Instantiate a command object from resolved field values
# ---------------------------------------------------------------------------
def _instantiate(cls: type, values: dict[str, Any]) -> Any:
    """
    Create an instance of *cls* and set all field values as attributes.

    We bypass ``__init__`` (which may not exist / expect arguments) and set
    attributes directly.
    """
    instance = object.__new__(cls)
    for attr, value in values.items():
        setattr(instance, attr, value)
    return instance


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> ParseContext:
    """
    Parse the command line and return a populated :class:`ParseContext`.

    This function reads the decorator metadata from the active app
    entry-point (set by ``@cb.app``) and the optional globals class
    (set by ``@cb.globals()``).

    Parameters
    ----------
    argv:
        Override the token list (defaults to ``sys.argv[1:]``).
    """
    if _app_fn is None:
        panic(
            "No app entry-point registered. "
            "Decorate your main function with @cb.app('name')."
        )

    if argv is None:
        argv = sys.argv[1:]

    app_meta: dict[str, Any] = getattr(_app_fn, "__cb_meta__", {})
    app_name: str = app_meta.get("name", "app")
    subcommands: list[type] = app_meta.get("subcommands", [])
    help_cfg: dict[str, Any] = app_meta.get("help", {"flag": True, "subcommand": False})
    version_cfg: dict[str, Any] = app_meta.get(
        "version", {"flag": True, "subcommand": False}
    )
    style: Style = resolve_style(app_meta.get("style"))
    footer_msg: str | None = app_meta.get("footer_message")
    app_description: str | None = app_meta.get("description")

    # Version flag
    app_version = app_meta.get("version")
    if app_version:
        version_flag = app_version.get("flag", True)
        version_sub = app_version.get("subcommand", False)
        ver = app_version.get("ver", True)
        if version_flag and "--version" in argv or "-V" in argv:
            if ver is True:
                try:
                    import importlib.metadata

                    ver = importlib.metadata.version(app_name)
                except Exception:
                    ver = "unknown"
            sys.stdout.write(f"{app_name} {style.version(ver)}\n")
            sys.exit(0)
        if version_sub and "version" in argv:
            if ver is True:
                try:
                    import importlib.metadata

                    ver = importlib.metadata.version(app_name)
                except Exception:
                    ver = "unknown"
            sys.stdout.write(f"{app_name} {style.version(ver)}\n")
            sys.exit(0)

    # Globals
    global_fields: dict[str, FieldSpec] = {}
    if _globals_cls is not None:
        global_fields = collect_fields(_globals_cls)

    # Clash detection across all subcommands
    for sub_cls in subcommands:
        sub_fields = collect_fields(sub_cls)
        if global_fields:
            check_global_clashes(
                global_fields,
                sub_fields,
                global_cls_name=_globals_cls.__name__,  # type: ignore[union-attr]
                command_cls_name=_cmd_name(sub_cls),
            )
        # Check nested subcommand clashes within the command.
        sub_meta = getattr(sub_cls, "__cb_meta__", {})
        for nested_cls in sub_meta.get("subcommands", []):
            nested_fields = collect_fields(nested_cls)
            check_global_clashes(
                sub_fields,
                nested_fields,
                global_cls_name=_cmd_name(sub_cls),
                command_cls_name=_cmd_name(nested_cls),
            )

    # Parse global flags (they can appear anywhere before the subcommand)
    # We do a greedy pre-pass to extract global tokens, leaving the rest for
    # the subcommand parser.
    global_flag_map: dict[str, tuple[str, FieldSpec]] = {}
    for attr_name, spec in global_fields.items():
        if spec.short:
            global_flag_map[spec.short] = (attr_name, spec)
        if spec.long:
            global_flag_map[spec.long] = (attr_name, spec)

    global_values: dict[str, Any] = {}
    stripped_argv: list[str] = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in global_flag_map:
            attr_name, spec = global_flag_map[token]
            if spec.kind == "flag":
                global_values[attr_name] = True
                i += 1
            else:
                if i + 1 >= len(argv):
                    raise CranberryParseError(
                        f"Global flag {token!r} requires a value."
                    )
                global_values[attr_name] = _coerce(argv[i + 1], spec, attr_name)
                i += 2
        else:
            stripped_argv.append(token)
            i += 1

    # Apply global defaults.
    for attr_name, spec in global_fields.items():
        if attr_name not in global_values:
            global_values[attr_name] = spec.default if not spec.is_required else None

    # Subcommand dispatch
    sub_map: dict[str, type] = {_cmd_name(s): s for s in subcommands}

    # Find the first token that matches a subcommand name.
    matched_sub_cls: type | None = None
    pre_sub_argv: list[str] = []
    footer_sub_argv: list[str] = []
    found = False
    for idx, token in enumerate(stripped_argv):
        if not found and token in sub_map:
            matched_sub_cls = sub_map[token]
            footer_sub_argv = stripped_argv[idx + 1 :]
            found = True
        elif not found:
            pre_sub_argv.append(token)

    # Top-level help / version before subcommand dispatch
    has_help_flag = help_cfg.get("flag", True)
    has_help_sub = help_cfg.get("subcommand", False)
    has_version_flag = version_cfg.get("flag", True)
    has_version_sub = version_cfg.get("subcommand", False)

    if matched_sub_cls is None and (
        has_help_flag
        and ("-h" in stripped_argv or "--help" in stripped_argv)
        or has_help_sub
        and "help" in stripped_argv
    ):
        text = render_help(
            app_name=app_name,
            command_name=None,
            description=app_description,
            global_fields=global_fields,
            command_fields={},
            subcommands=subcommands,
            has_help_flag=has_help_flag,
            has_help_subcommand=has_help_sub,
            has_version_flag=has_version_flag,
            has_version_subcommand=has_version_sub,
            footer_msg=footer_msg,
            style=style,
            parent_command=None,
        )
        sys.stdout.write(text)
        sys.exit(0)

    if matched_sub_cls is None:
        # No subcommand - top-level only (may be valid if no subcommands registered).
        if subcommands:
            valid = ", ".join(sorted(sub_map))
            if stripped_argv:
                raise CranberryParseError(
                    f"Unknown subcommand {stripped_argv[0]!r}. "
                    f"Valid subcommands: {valid}"
                )
        return ParseContext(command=None, globals_=global_values)

    # Parse the matched subcommand
    sub_fields = collect_fields(matched_sub_cls)
    sub_meta: dict[str, Any] = getattr(matched_sub_cls, "__cb_meta__", {})
    sub_description: str | None = sub_meta.get("description")
    nested_subcommands: list[type] = sub_meta.get("subcommands", [])

    # Merge pre-sub tokens back with post-sub (pre = flags before the subcommand name).
    full_sub_argv = pre_sub_argv + footer_sub_argv

    sub_help_cfg = help_cfg.copy()  # inherit app help config for subcommands

    sub_values, sub_remaining, nested_cls = _parse_command_argv(
        full_sub_argv,
        sub_fields,
        command_name=_cmd_name(matched_sub_cls),
        subcommands=nested_subcommands,
        style=style,
        help_cfg={
            **sub_help_cfg,
            # subcommand help show description from the sub
            "description": sub_description,
        },
        global_fields=global_fields,
        app_name=app_name,
        footer_msg=footer_msg,
        parent_command=None,
    )

    # Parse nested subcommand if present
    if nested_cls is not None:
        nested_fields = collect_fields(nested_cls)
        nested_values, _, __ = _parse_command_argv(
            sub_remaining,
            nested_fields,
            command_name=_cmd_name(nested_cls),
            subcommands=[],
            style=style,
            help_cfg=sub_help_cfg,
            global_fields=global_fields,
            app_name=app_name,
            footer_msg=footer_msg,
            parent_command=_cmd_name(matched_sub_cls),
        )
        nested_instance = _instantiate(nested_cls, nested_values)
        sub_values["subcommand"] = nested_instance
    else:
        sub_values.setdefault("subcommand", None)

    command_instance = _instantiate(matched_sub_cls, sub_values)
    return ParseContext(command=command_instance, globals_=global_values)
