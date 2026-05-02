"""
Cranberry rendering styles.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------
_RESET = "\033[0m"


def _ansi(code: str, text: str) -> str:
    return f"\033[{code}m{text}{_RESET}"


def bold(text: str) -> str:
    return _ansi("1", text)


def dim(text: str) -> str:
    return _ansi("2", text)


def fg(r: int, g: int, b: int, text: str) -> str:
    return f"\033[38;2;{r};{g};{b}m{text}{_RESET}"


# ---------------------------------------------------------------------------
# Base style
# ---------------------------------------------------------------------------
@dataclass
class Style:
    """
    Abstract style base class.

    Override any method to customise the appearance of a particular text role.
    All methods receive the plain text and must return a (possibly decorated)
    string.
    """

    # headings

    def heading(self, text: str) -> str:
        """Section headings such as "Commands:", "Flags:", …"""
        return text

    def app_name(self, text: str) -> str:
        """The application name in the usage line."""
        return text

    def command_name(self, text: str) -> str:
        """A subcommand name in the command list."""
        return text

    # flags / args

    def flag_short(self, text: str) -> str:
        """Short flag like ``-f``."""
        return text

    def flag_long(self, text: str) -> str:
        """Long flag like ``--flag``."""
        return text

    def metavar(self, text: str) -> str:
        """Metavar like ``<FILE>``."""
        return text

    def positional(self, text: str) -> str:
        """Positional argument display like ``[NAME]``."""
        return text

    # descriptions

    def description(self, text: str) -> str:
        """Application / command description."""
        return text

    def help_text(self, text: str) -> str:
        """Per-argument help string."""
        return text

    def footer_message(self, text: str) -> str:
        """The trailing footer message."""
        return text

    def version(self, text: str) -> str:
        """Version string output."""
        return text


# ---------------------------------------------------------------------------
# Plain style (no colour)
# ---------------------------------------------------------------------------
class PlainStyle(Style):
    """No ANSI codes; suitable for terminals without colour support."""

    pass  # inherits all no-op defaults


# ---------------------------------------------------------------------------
# Colorful style
# ---------------------------------------------------------------------------
class ColorfulStyle(Style):
    """Tasteful colour accents using ANSI 256/true-colour codes."""

    def heading(self, text: str) -> str:
        return bold(text)

    def app_name(self, text: str) -> str:
        return bold(fg(220, 80, 80, text))  # cranberry red

    def command_name(self, text: str) -> str:
        return fg(100, 180, 255, text)  # sky blue

    def flag_short(self, text: str) -> str:
        return fg(120, 220, 120, text)  # green

    def flag_long(self, text: str) -> str:
        return fg(120, 220, 120, text)

    def metavar(self, text: str) -> str:
        return fg(200, 160, 80, text)  # warm amber

    def positional(self, text: str) -> str:
        return fg(200, 160, 80, text)

    def description(self, text: str) -> str:
        return text

    def footer_message(self, text: str) -> str:
        return dim(text)

    def version(self, text: str) -> str:
        return fg(160, 160, 160, text)


# ---------------------------------------------------------------------------
# Fancy style
# ---------------------------------------------------------------------------
class FancyStyle(Style):
    """A richer palette with bolder headings."""

    def heading(self, text: str) -> str:
        return _ansi("1;4", text)  # bold + underline

    def app_name(self, text: str) -> str:
        return _ansi("1", fg(255, 100, 100, text))

    def command_name(self, text: str) -> str:
        return _ansi("1", fg(80, 200, 255, text))

    def flag_short(self, text: str) -> str:
        return fg(80, 240, 130, text)

    def flag_long(self, text: str) -> str:
        return _ansi("1", fg(80, 240, 130, text))

    def metavar(self, text: str) -> str:
        return _ansi("3", fg(255, 200, 80, text))  # italic + amber

    def positional(self, text: str) -> str:
        return _ansi("3", fg(255, 200, 80, text))

    def footer_message(self, text: str) -> str:
        return _ansi("3", text)  # italic

    def version(self, text: str) -> str:
        return fg(180, 180, 180, text)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
_BUILTIN_STYLES: dict[str, type[Style]] = {
    "plain": PlainStyle,
    "colorful": ColorfulStyle,
    "fancy": FancyStyle,
}


def resolve_style(value: str | type[Style] | None) -> Style:  # pyrefly: ignore[bad-return]
    """
    Convert the ``@cb.style(...)`` argument into a :class:`Style` instance.

    Parameters
    ----------
    value:
        A string key (``"plain"``, ``"colorful"``, ``"fancy"``), a
        :class:`Style` subclass, or *None* (falls back to ``PlainStyle``).
    """
    if value is None:
        return PlainStyle()
    if isinstance(value, str):
        cls = _BUILTIN_STYLES.get(value)
        if cls is None:
            from cranberry.errors import panic

            panic(
                f"Unknown style {value!r}. Choose one of: {', '.join(_BUILTIN_STYLES)}"
            )
        return cls()  # pyrefly: ignore[not-callable]
    if isinstance(value, type) and issubclass(value, Style):
        return value()
    from cranberry.errors import panic

    panic(f"@cb.style expects a string or a Style subclass, got {value!r}.")
