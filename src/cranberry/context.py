"""
Cranberry parse context.
"""

from __future__ import annotations

from typing import Any


class ParseContext:
    """
    The result of a successful ``cb.parse_args()`` call.

    Attributes are set dynamically:

    * ``ctx.command`` - the instantiated command class (e.g. ``SubCommand``),
      or *None* when the user ran the app without a subcommand.
    * ``ctx.<global_field>`` - one attribute per global option / flag,
      accessible directly on the context.

    Command-specific fields live on the command instance itself:
    ``ctx.command.option``, ``ctx.command.nested_option``, etc.
    """

    def __init__(self, command: Any | None, globals_: dict[str, Any]) -> None:
        self.command: Any | None = command
        for key, value in globals_.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        attrs = {k: v for k, v in self.__dict__.items() if k != "command"}
        return f"ParseContext(command={self.command!r}, globals={attrs!r})"

    def help(self, command: Any | None = None) -> str:
        """
        Return the formatted and stylised help message for the current context.

        Works for the top-level app (no argument) and for a specific command
        (pass either a command class or an instantiated command). When an
        instantiated parent command that contains a subcommand is passed, the
        help for the contained subcommand is returned (this mirrors the common
        use-case of calling ctx.help(ctx.command) to get help for the active
        subcommand).
        """
        # Local imports to avoid circular import at module import time.
        from cranberry import parser as _parser_module
        from cranberry.errors import panic
        from cranberry.help_ import _cmd_name, render_help
        from cranberry.registry import collect_fields
        from cranberry.style import resolve_style

        if _parser_module._app_fn is None:
            panic("No app entry-point registered")

        app_meta = getattr(_parser_module._app_fn, "__cb_meta__", {})
        app_name = app_meta.get("name", "app")
        style = resolve_style(app_meta.get("style"))
        footer_msg = app_meta.get("footer_message")
        help_cfg = app_meta.get("help", {})
        version_cfg = app_meta.get("version", {})

        # Global fields (from @cb.globals)
        global_fields: dict[str, Any] = {}
        if _parser_module._globals_cls:
            global_fields = collect_fields(_parser_module._globals_cls)

        # Helper: find immediate parent command name for a target class
        def _find_parent_name(
            target: type, subs: list[type], parent_name: str | None = None
        ):
            for sub in subs:
                if sub is target:
                    return parent_name
                child_subs = getattr(sub, "__cb_meta__", {}).get("subcommands", [])
                res = _find_parent_name(target, child_subs, _cmd_name(sub))
                if res is not None:
                    return res
            return None

        # Top-level help
        if command is None:
            command_name = None
            command_fields: dict[str, Any] = {}
            subcommands = app_meta.get("subcommands", [])
            parent_command = None
            description = app_meta.get("description")

            return render_help(
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

        # If a command instance with a nested subcommand was passed, prefer the
        # nested subcommand (this supports calling ctx.help(ctx.command) where
        # ctx.command is a container with an active .subcommand).
        if (
            not isinstance(command, type)
            and hasattr(command, "subcommand")
            and command.subcommand is not None
        ):
            target_cls = type(command.subcommand)
            parent_command = _cmd_name(type(command))
        else:
            target_cls = command if isinstance(command, type) else type(command)
            parent_command = _find_parent_name(
                target_cls, app_meta.get("subcommands", [])
            )

        command_fields = collect_fields(target_cls)
        cmd_meta = getattr(target_cls, "__cb_meta__", {})
        subcommands = cmd_meta.get("subcommands", [])
        command_name = _cmd_name(target_cls)
        description = cmd_meta.get("description")

        return render_help(
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
