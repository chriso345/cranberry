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
