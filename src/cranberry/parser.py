"""
Cranberry argv parser (refactored: tree resolver architecture)
"""

from __future__ import annotations

import os
import sys
from typing import Any

from cranberry.context import ParseContext
from cranberry.errors import CranberryParseError, panic
from cranberry.fields import FieldSpec
from cranberry.registry import collect_fields
from cranberry.style import Style, resolve_style
from cranberry.help_ import render_help, render_version, _cmd_name


# ---------------------------------------------------------------------------
# Module-level state
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
# Coercion
# ---------------------------------------------------------------------------
def _coerce(raw: str, spec: FieldSpec, attr_name: str) -> Any:
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
# HELP
# ---------------------------------------------------------------------------
def _print_help_and_exit(
    *,
    app_name: str,
    command_name: str | None,
    global_fields: dict[str, FieldSpec],
    command_fields: dict[str, FieldSpec],
    subcommands: list[type],
    help_cfg: dict[str, Any],
    version_cfg: dict[str, Any],
    description: str | None = None,
    footer_msg: str | None,
    style: Style,
    parent_command: str | None,
) -> None:
    text = render_help(
        app_name=app_name,
        command_name=command_name,
        description=description,
        global_fields=global_fields,
        command_fields=command_fields,
        subcommands=subcommands,
        has_help_flag=help_cfg.get("flag", True),
        has_help_subcommand=help_cfg.get("subcommand", False),
        has_version_flag=version_cfg.get("flag", True),
        has_version_subcommand=version_cfg.get("subcommand", False),
        footer_msg=footer_msg,
        style=style,
        parent_command=parent_command,
    )
    sys.stdout.write(text)
    sys.exit(0)


# ---------------------------------------------------------------------------
# Command resolution (TREE PHASE)
# ---------------------------------------------------------------------------
def _resolve_command_path(
    argv: list[str],
    sub_map: dict[str, type],
) -> tuple[list[type], list[str]]:
    chain: list[type] = []
    i = 0

    while i < len(argv):
        token = argv[i]

        if token in sub_map:
            cmd_cls = sub_map[token]
            chain.append(cmd_cls)

            sub_meta = getattr(cmd_cls, "__cb_meta__", {})
            sub_map = {_cmd_name(s): s for s in sub_meta.get("subcommands", [])}

            i += 1
        else:
            break

    return chain, argv[i:]


# ---------------------------------------------------------------------------
# LEAF PARSER (NO RECURSION)
# ---------------------------------------------------------------------------
def _parse_leaf_command(
    argv: list[str],
    fields: dict[str, FieldSpec],
    *,
    leaf_cls: type,
    command_name: str,
    help_cfg: dict[str, Any],
    version_cfg: dict[str, Any],
    style: Style,
    global_fields: dict[str, FieldSpec],
    app_name: str,
    footer_msg: str | None,
    parent_command: str | None,
) -> dict[str, Any]:

    flag_map: dict[str, tuple[str, FieldSpec]] = {}

    for attr, spec in fields.items():
        if spec.kind == "arg":
            continue
        if spec.short:
            flag_map[spec.short] = (attr, spec)
        if spec.long:
            flag_map[spec.long] = (attr, spec)

    values: dict[str, Any] = {}
    positional = [(n, s) for n, s in fields.items() if s.kind == "arg"]
    pos_vals: dict[str, list[str]] = {n: [] for n, _ in positional}
    pos_i = 0

    # Determine if help flag / subcommand should be auto-added
    has_help_flag = help_cfg.get("flag", True)
    has_help_subcommand = help_cfg.get("subcommand", False)

    i = 0
    while i < len(argv):
        token = argv[i]

        if (
            has_help_flag
            and token in ("-h", "--help")
            or (has_help_subcommand and token == "help")
        ):
            _print_help_and_exit(
                app_name=app_name,
                command_name=command_name,
                global_fields=global_fields,
                command_fields=fields,
                subcommands=[],
                help_cfg=help_cfg,
                version_cfg=version_cfg,
                # Get the description from the subcommand command if available, otherwise use none.
                description=getattr(leaf_cls, "__cb_meta__", {}).get("description"),
                footer_msg=footer_msg,
                style=style,
                parent_command=parent_command,
            )

        # FLAGS
        if token in flag_map:
            attr, spec = flag_map[token]

            if spec.kind == "flag":
                values[attr] = True
                i += 1
                continue

            if i + 1 >= len(argv):
                raise CranberryParseError(f"{token!r} requires value")

            values[attr] = _coerce(argv[i + 1], spec, attr)
            i += 2
            continue

        # Combined short flags allowed for stackable boolean flags (e.g. -fs -> -f and -s) - only if all are valid flags.
        if token.startswith("-") and not token.startswith("--") and len(token) > 2:
            # Attempt to decompose into multiple short flags
            j = 1
            short_flags: list[str] = []
            ok = True
            while j < len(token):
                short = "-" + token[j]
                entry = flag_map.get(short)
                if (
                    entry is None
                    or entry[1].kind != "flag"
                    or entry[1].stackable is False
                ):
                    ok = False
                    break
                short_flags.append(short)
                j += 1
            if ok and short_flags:
                for short in short_flags:
                    attr, spec = flag_map[short]
                    values[attr] = True
                i += 1
                continue

        if token.startswith("-"):
            raise CranberryParseError(f"Unknown flag: {token!r}")

        # POSITIONAL
        if pos_i >= len(positional):
            raise CranberryParseError(f"Unexpected argument: {token!r}")

        attr, spec = positional[pos_i]
        pos_vals[attr].append(token)

        if spec.count == 1:
            pos_i += 1
        elif spec.count is not None and len(pos_vals[attr]) >= spec.count:
            pos_i += 1

        i += 1

    # resolve positional
    for attr, spec in positional:
        raw = pos_vals[attr]

        if spec.count == 1:
            values[attr] = raw[0] if raw else spec.default
        else:
            values[attr] = [_coerce(r, spec, attr) for r in raw]

    # defaults
    for attr, spec in fields.items():
        if spec.kind != "arg":
            values.setdefault(attr, spec.default)

    return values


# ---------------------------------------------------------------------------
# Instantiate
# ---------------------------------------------------------------------------
def _instantiate(cls: type, values: dict[str, Any]) -> Any:
    obj = object.__new__(cls)
    for k, v in values.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# PUBLIC API (NEW PIPELINE)
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> ParseContext:
    if _app_fn is None:
        panic("No app entry-point registered")

    if argv is None:
        argv = sys.argv[1:]

    meta = getattr(_app_fn, "__cb_meta__", {})
    app_name = meta.get("name", "app")
    subcommands = meta.get("subcommands", [])
    style = resolve_style(meta.get("style"))
    footer_msg = meta.get("footer_message")

    global_fields: dict[str, FieldSpec] = {}
    if _globals_cls:
        global_fields = collect_fields(_globals_cls)

    global_map: dict[str, tuple[str, FieldSpec]] = {}
    for n, s in global_fields.items():
        if s.short:
            global_map[s.short] = (n, s)
        if s.long:
            global_map[s.long] = (n, s)

    global_values: dict[str, Any] = {}
    stripped: list[str] = []

    i = 0
    while i < len(argv):
        t = argv[i]

        if t in global_map:
            attr, spec = global_map[t]

            if spec.kind == "flag":
                global_values[attr] = True
                i += 1
            else:
                global_values[attr] = _coerce(argv[i + 1], spec, attr)
                i += 2
            continue

        # Combined short flags for globals (e.g., -fF -> -f and -F) - only allowed for boolean flags
        if t.startswith("-") and not t.startswith("--") and len(t) > 2:
            j = 1
            short_flags = []
            ok = True
            while j < len(t):
                short = "-" + t[j]
                entry = global_map.get(short)
                if entry is None or entry[1].kind != "flag":
                    ok = False
                    break
                short_flags.append(short)
                j += 1
            if ok and short_flags:
                for short in short_flags:
                    attr, spec = global_map[short]
                    global_values[attr] = True
                i += 1
                continue

        stripped.append(t)
        i += 1

    for n, s in global_fields.items():
        global_values.setdefault(n, s.default)

    sub_map = {_cmd_name(s): s for s in subcommands}
    chain, leaf_argv = _resolve_command_path(stripped, sub_map)

    if not chain:
        if stripped and (
            (meta.get("help", {}).get("subcommand", False) and stripped[0] == "help")
            or (
                meta.get("help", {}).get("flag", True)
                and stripped[0] in ("-h", "--help")
            )
        ):
            _print_help_and_exit(
                app_name=app_name,
                command_name=None,
                global_fields=global_fields,
                command_fields={},
                subcommands=subcommands,
                help_cfg=meta.get("help", {}),
                version_cfg=meta.get("version", {}),
                description=meta.get("description"),
                footer_msg=footer_msg,
                style=style,
                parent_command=None,
            )

        if stripped and (
            (
                meta.get("version", {}).get("subcommand", False)
                and stripped[0] == "version"
            )
            or (
                meta.get("version", {}).get("flag", True)
                and stripped[0] in ("-V", "--version")
            )
            and len(stripped) == 1
        ):
            render_version(
                app_name=app_name,
                version_cfg=meta.get("version", {}),
                style=style,
            )

        if subcommands and stripped:
            raise CranberryParseError(f"Unknown command {stripped[0]!r}")
        return ParseContext(command=None, globals_=global_values)

    leaf_cls = chain[-1]
    fields = collect_fields(leaf_cls)

    values = _parse_leaf_command(
        leaf_argv,
        fields,
        leaf_cls=leaf_cls,
        command_name=_cmd_name(leaf_cls),
        help_cfg=meta.get("help", {}),
        version_cfg=meta.get("version", {}),
        style=style,
        global_fields=global_fields,
        app_name=app_name,
        footer_msg=footer_msg,
        parent_command=_cmd_name(chain[-2]) if len(chain) > 1 else None,
    )

    cmd_instance = _instantiate(leaf_cls, values)

    # attach chain upward
    current = cmd_instance
    for cls in reversed(chain[:-1]):
        inst = _instantiate(cls, {})
        inst.subcommand = current
        current = inst

    return ParseContext(command=current, globals_=global_values)
