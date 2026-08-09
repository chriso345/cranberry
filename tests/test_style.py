"""
Tests for cranberry.style
"""

import pytest

from cranberry.errors import CranberryPanic
from cranberry.style import (
    ColorfulStyle,
    FancyStyle,
    PlainStyle,
    Style,
    bold,
    dim,
    fg,
    resolve_style,
)


class TestAnsiHelpers:
    def test_bold_wraps_text(self):
        result = bold("hello")
        assert "hello" in result
        assert "\033[" in result

    def test_dim_wraps_text(self):
        result = dim("hello")
        assert "hello" in result
        assert "\033[" in result

    def test_fg_wraps_text(self):
        result = fg(255, 0, 0, "red text")
        assert "red text" in result
        assert "255" in result


class TestPlainStyle:
    def setup_method(self):
        self.style = PlainStyle()

    def test_heading_passthrough(self):
        assert self.style.heading("Commands:") == "Commands:"

    def test_app_name_passthrough(self):
        assert self.style.app_name("myapp") == "myapp"

    def test_command_name_passthrough(self):
        assert self.style.command_name("sub") == "sub"

    def test_flag_short_passthrough(self):
        assert self.style.flag_short("-f") == "-f"

    def test_flag_long_passthrough(self):
        assert self.style.flag_long("--flag") == "--flag"

    def test_metavar_passthrough(self):
        assert self.style.metavar("<VALUE>") == "<VALUE>"

    def test_positional_passthrough(self):
        assert self.style.positional("[NAME]") == "[NAME]"

    def test_description_passthrough(self):
        assert self.style.description("desc") == "desc"

    def test_help_text_passthrough(self):
        assert self.style.help_text("help") == "help"

    def test_footer_message_passthrough(self):
        assert self.style.footer_message("footer") == "footer"

    def test_version_passthrough(self):
        assert self.style.version("1.0.0") == "1.0.0"


class TestColorfulStyle:
    def setup_method(self):
        self.style = ColorfulStyle()

    def test_heading_adds_bold(self):
        result = self.style.heading("Commands:")
        assert "\033[" in result
        assert "Commands:" in result

    def test_app_name_adds_color(self):
        result = self.style.app_name("myapp")
        assert "\033[" in result
        assert "myapp" in result

    def test_command_name_adds_color(self):
        result = self.style.command_name("sub")
        assert "\033[" in result

    def test_flag_short_adds_color(self):
        assert "\033[" in self.style.flag_short("-f")

    def test_flag_long_adds_color(self):
        assert "\033[" in self.style.flag_long("--flag")

    def test_metavar_adds_color(self):
        assert "\033[" in self.style.metavar("<VALUE>")

    def test_positional_adds_color(self):
        assert "\033[" in self.style.positional("[NAME]")

    def test_footer_message_adds_dim(self):
        assert "\033[" in self.style.footer_message("footer")

    def test_version_adds_color(self):
        assert "\033[" in self.style.version("1.0.0")

    def test_description_no_color(self):
        # description is plain in colorful style
        assert self.style.description("desc") == "desc"


class TestFancyStyle:
    def setup_method(self):
        self.style = FancyStyle()

    def test_heading_bold_underline(self):
        result = self.style.heading("Commands:")
        assert "\033[" in result
        assert "Commands:" in result

    def test_metavar_italic(self):
        result = self.style.metavar("<VALUE>")
        assert "\033[" in result

    def test_footer_italic(self):
        result = self.style.footer_message("footer")
        assert "\033[" in result


class TestResolveStyle:
    def test_none_returns_plain(self):
        assert isinstance(resolve_style(None), PlainStyle)

    def test_plain_string(self):
        assert isinstance(resolve_style("plain"), PlainStyle)

    def test_colorful_string(self):
        assert isinstance(resolve_style("colorful"), ColorfulStyle)

    def test_fancy_string(self):
        assert isinstance(resolve_style("fancy"), FancyStyle)

    def test_unknown_string_panics(self):
        with pytest.raises(CranberryPanic, match="Unknown style"):
            resolve_style("neon")

    def test_custom_style_class(self):
        class MyStyle(Style):
            pass

        result = resolve_style(MyStyle)
        assert isinstance(result, MyStyle)

    def test_invalid_type_panics(self):
        with pytest.raises(CranberryPanic):
            resolve_style(42)
