"""
Cranberry help text renderer.
"""

from __future__ import annotations

from typing import Any

from cranberry.fields import FieldSpec
from cranberry.style import Style


# Minimum gap (in spaces) between the widest left column and the help text.
_COLUMN_GAP = 2


def _flag_label(spec: FieldSpec, style: Style) -> str:
    """Build the left column text for a named field (option / flag / file / dir)."""
    parts: list[str] = []
    if spec.short:
        parts.append(style.flag_short(spec.short))
    if spec.long:
        parts.append(style.flag_long(spec.long))

    label = ", ".join(parts)

    if spec.kind == "flag":
        return label

    if spec.kind == "file":
        label += f" {style.metavar('<FILE>')}"
    elif spec.kind == "dir":
        label += f" {style.metavar('<DIR>')}"
    else:
        label += f" {style.metavar(f'<{spec.metavar}>')}"

    return label


def _arg_label(attr_name: str, spec: FieldSpec, style: Style) -> str:
    """Build the left column text for a positional argument."""
    display = attr_name.upper()
    if spec.count is None or (isinstance(spec.count, int) and spec.count > 1):
        display = f"[{display}]..."
    else:
        display = f"[{display}]"

    # Enum hint in the label.
    from cranberry.enum import CranberryEnum

    if isinstance(spec.type, type) and issubclass(spec.type, CranberryEnum):
        members = " | ".join(spec.type._members.values())  # type: ignore[attr-defined]
        display += f" ( {members} )"

    return style.positional(display)


def _strip_ansi(text: str) -> str:
    """Return *text* with ANSI escape sequences removed (for width calculation)."""
    import re

    return re.sub(r"\033\[[0-9;]*m", "", text)


def _two_col(rows: list[tuple[str, str]], style: Style) -> str:
    """Format a two-column table with consistent alignment."""
    if not rows:
        return ""

    # Compute max width using stripped (plain) text so ANSI codes don't skew it.
    max_left = max(len(_strip_ansi(left)) for left, _ in rows)
    lines: list[str] = []
    for left, right in rows:
        plain_len = len(_strip_ansi(left))
        padding = " " * (max_left - plain_len + _COLUMN_GAP)
        help_str = style.help_text(right) if right else ""
        lines.append(f"  {left}{padding}{help_str}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def render_help(
    *,
    app_name: str,
    command_name: str | None,
    description: str | None,
    global_fields: dict[str, FieldSpec],
    command_fields: dict[str, FieldSpec],
    subcommands: list[type],
    has_help_flag: bool,
    has_help_subcommand: bool,
    has_version_flag: bool,
    has_version_subcommand: bool,
    footer_msg: str | None,
    style: Style,
    parent_command: str | None = None,
) -> str:
    """
    Build and return the complete help string.

    Parameters
    ----------
    app_name:
        The application name (from ``@cb.app``).
    command_name:
        The active subcommand name, or *None* for the top-level help.
    description:
        Free-text description for the app or subcommand.
    global_fields:
        Fields from the ``@cb.globals()`` class.
    command_fields:
        Fields belonging to the active command (merged from MRO).
    subcommands:
        List of registered subcommand *classes*.
    has_help_flag:
        Whether to show ``-h``/``--help`` in the flags section.
    has_help_subcommand:
        Whether to show ``help`` in the commands section.
    has_version_flag:
        Whether to show ``-V``/``--version`` in the flags section.
    has_version_subcommand:
        Whether to show ``version`` in the commands section.
    footer_msg:
        Optional trailing message.
    style:
        Active rendering style.
    parent_command:
        Parent command name, used to build the usage line for nested commands.
    """
    lines: list[str] = []

    # Description
    if description:
        lines.append(style.description(description))
        lines.append("")

    # Usage line
    usage_parts: list[str] = [style.app_name(app_name)]
    if parent_command:
        usage_parts.append(style.command_name(parent_command))
    if command_name:
        usage_parts.append(style.command_name(command_name))

    if global_fields or has_help_flag:
        usage_parts.append("[OPTIONS]")
    if subcommands:
        usage_parts.append("<COMMAND>")

    # Positional args in usage
    for attr_name, spec in command_fields.items():
        if spec.kind != "arg":
            continue
        display = attr_name.upper()
        if spec.count is None or (isinstance(spec.count, int) and spec.count > 1):
            display = f"[{display}]..."
        else:
            display = f"[{display}]"
        usage_parts.append(style.positional(display))

    lines.append(f"Usage: {' '.join(usage_parts)}")
    lines.append("")

    # Commands section
    if subcommands or has_help_subcommand or has_version_subcommand:
        lines.append(style.heading("Commands:"))
        cmd_rows: list[tuple[str, str]] = []
        # Sort alphabetically, but put "help" at the end.
        sorted_subs = sorted(subcommands, key=lambda c: _cmd_name(c))
        for sub in sorted_subs:
            sub_name = style.command_name(_cmd_name(sub))
            sub_desc = _meta_get(sub, "description", "")
            cmd_rows.append((sub_name, sub_desc))
        if has_help_subcommand:
            cmd_rows.append(
                (style.command_name("help"), "Display this help message and exit.")
            )
        if has_version_subcommand:
            cmd_rows.append(
                (
                    style.command_name("version"),
                    "Display version information and exit.",
                )
            )
        lines.append(_two_col(cmd_rows, style))
        lines.append("")

    # Flags / options section
    non_arg_fields = {k: v for k, v in command_fields.items() if v.kind != "arg"}

    if non_arg_fields or has_help_flag or has_version_flag:
        lines.append(style.heading("Flags:"))
        flag_rows: list[tuple[str, str]] = []
        for attr_name, spec in sorted(non_arg_fields.items()):
            flag_rows.append((_flag_label(spec, style), spec.help))
        if has_help_flag:
            flag_rows.append(
                (
                    f"{style.flag_short('-h')}, {style.flag_long('--help')}",
                    "Display this help message and exit.",
                )
            )
        if has_version_flag:
            flag_rows.append(
                (
                    f"{style.flag_short('-V')}, {style.flag_long('--version')}",
                    "Display version information and exit.",
                )
            )
        lines.append(_two_col(flag_rows, style))
        lines.append("")

    # Positional arguments section
    arg_fields = {k: v for k, v in command_fields.items() if v.kind == "arg"}
    if arg_fields:
        lines.append(style.heading("Arguments:"))
        arg_rows: list[tuple[str, str]] = [
            (_arg_label(name, spec, style), spec.help)
            for name, spec in arg_fields.items()
        ]
        lines.append(_two_col(arg_rows, style))
        lines.append("")

    # Global options section
    if global_fields:
        lines.append(style.heading("Global Options:"))
        g_rows: list[tuple[str, str]] = [
            (_flag_label(spec, style), spec.help) for spec in global_fields.values()
        ]
        lines.append(_two_col(g_rows, style))
        lines.append("")

    # Footer
    if footer_msg:
        lines.append(style.footer_message(footer_msg))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _cmd_name(cls: type) -> str:
    meta = getattr(cls, "__cb_meta__", {})
    return meta.get("name", cls.__name__.lower())


def _meta_get(obj: Any, key: str, default: Any = None) -> Any:
    return getattr(obj, "__cb_meta__", {}).get(key, default)
