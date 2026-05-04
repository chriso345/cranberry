"""
Tests for cranberry.help_
"""

import pytest
from cranberry.help_ import (
    render_help,
    render_version,
    _cmd_name,
    _strip_ansi,
    _two_col,
)
from cranberry.style import PlainStyle
from cranberry.errors import CranberryParseError
import cranberry as cb


PLAIN = PlainStyle()


def make_help(**kwargs):
    """Call render_help with sensible defaults."""
    defaults = dict(
        app_name="testapp",
        command_name=None,
        description=None,
        global_fields={},
        command_fields={},
        subcommands=[],
        has_help_flag=True,
        has_help_subcommand=False,
        has_version_flag=False,
        has_version_subcommand=False,
        footer_msg=None,
        style=PLAIN,
        parent_command=None,
    )
    defaults.update(kwargs)
    return render_help(**defaults)


# ---------------------------------------------------------------------------
# Usage line
# ---------------------------------------------------------------------------
class TestUsageLine:
    def test_contains_usage(self):
        assert "Usage:" in make_help()

    def test_contains_app_name(self):
        assert "testapp" in make_help()

    def test_options_placeholder_when_help_flag(self):
        assert "[OPTIONS]" in make_help(has_help_flag=True)

    def test_options_placeholder_when_global_fields(self):
        gf = {"flag": cb.flag("-g", "--global")}
        assert "[OPTIONS]" in make_help(global_fields=gf, has_help_flag=False)

    def test_command_placeholder_when_subcommands(self):
        @cb.command("sub")
        class Sub:
            pass

        assert "<COMMAND>" in make_help(subcommands=[Sub])

    def test_parent_command_in_usage(self):
        assert "parent" in make_help(parent_command="parent", command_name="child")

    def test_subcommand_in_usage(self):
        assert "child" in make_help(command_name="child")

    def test_positional_in_usage(self):
        fields = {"name": cb.arg()}
        fields["name"].type = str
        assert "NAME" in make_help(command_fields=fields)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
class TestSections:
    def test_commands_section_present_when_subcommands(self):
        @cb.command("sub")
        class Sub:
            pass

        assert "Commands:" in make_help(subcommands=[Sub])

    def test_commands_section_absent_without_subcommands(self):
        result = make_help(
            subcommands=[], has_help_subcommand=False, has_version_subcommand=False
        )
        assert "Commands:" not in result

    def test_flags_section_present(self):
        assert "Flags:" in make_help(has_help_flag=True)

    def test_flags_section_absent_without_flags(self):
        result = make_help(has_help_flag=False, has_version_flag=False)
        assert "Flags:" not in result

    def test_arguments_section_present(self):
        fields = {"name": cb.arg()}
        fields["name"].type = str
        assert "Arguments:" in make_help(command_fields=fields)

    def test_global_options_section_present(self):
        gf = {"gflag": cb.flag("-g", "--global")}
        assert "Global Options:" in make_help(global_fields=gf)

    def test_footer_present(self):
        assert "Thanks!" in make_help(footer_msg="Thanks!")

    def test_description_present(self):
        assert "My description" in make_help(description="My description")

    def test_help_subcommand_listed(self):
        result = make_help(has_help_subcommand=True)
        assert "help" in result

    def test_version_subcommand_listed(self):
        result = make_help(has_version_subcommand=True)
        assert "version" in result

    def test_help_flag_listed(self):
        result = make_help(has_help_flag=True)
        assert "--help" in result

    def test_version_flag_listed(self):
        result = make_help(has_version_flag=True)
        assert "--version" in result

    def test_description_appears_before_sections(self):
        result = make_help(description="My description")

        # Description should appear in output
        assert "My description" in result

        # It should appear near the top (before Flags/Commands if present)
        desc_index = result.index("My description")

        if "Flags:" in result:
            assert desc_index < result.index("Flags:")

        if "Commands:" in result:
            assert desc_index < result.index("Commands:")

    def test_description_is_not_modified(self):
        result = make_help(description="Simple description text")
        assert "Simple description text" in result

    def test_description_with_full_help_layout(self):
        @cb.command("sub")
        class Sub:
            pass

        gf = {"flag": cb.flag("-g", "--global")}

        result = make_help(
            description="CLI tool description",
            global_fields=gf,
            subcommands=[Sub],
            footer_msg="Footer text",
        )

        # All major sections exist
        assert "CLI tool description" in result
        assert "Global Options:" in result
        assert "Commands:" in result
        assert "Footer text" in result

        # Description should appear early in the output
        assert result.index("CLI tool description") < result.index("Commands:")

# ---------------------------------------------------------------------------
# _strip_ansi
# ---------------------------------------------------------------------------
class TestStripAnsi:
    def test_strips_color_codes(self):
        ansi = "\033[38;2;255;0;0mred\033[0m"
        assert _strip_ansi(ansi) == "red"

    def test_plain_text_unchanged(self):
        assert _strip_ansi("hello") == "hello"


# ---------------------------------------------------------------------------
# _two_col
# ---------------------------------------------------------------------------
class TestTwoCol:
    def test_empty_rows(self):
        assert _two_col([], PLAIN) == ""

    def test_alignment(self):
        rows = [("short", "desc1"), ("a-much-longer-key", "desc2")]
        result = _two_col(rows, PLAIN)
        lines = result.splitlines()
        # Both lines should have their descriptions starting at the same column.
        col_short = lines[0].index("desc1")
        col_long = lines[1].index("desc2")
        assert col_short == col_long


# ---------------------------------------------------------------------------
# _cmd_name
# ---------------------------------------------------------------------------
class TestCmdName:
    def test_name_from_meta(self):
        @cb.command("my-command")
        class MyCommand:
            pass

        assert _cmd_name(MyCommand) == "my-command"

    def test_name_falls_back_to_lowercase_class_name(self):
        class SomeCommand:
            pass

        assert _cmd_name(SomeCommand) == "somecommand"


# ---------------------------------------------------------------------------
# render_version
# ---------------------------------------------------------------------------
class TestRenderVersion:
    def test_literal_version_output(self, capsys):
        with pytest.raises(SystemExit):
            render_version("myapp", {"ver": "1.2.3", "flag": True}, PLAIN)
        out = capsys.readouterr().out
        assert "1.2.3" in out
        assert "myapp" in out

    def test_exits_with_zero(self, capsys):
        with pytest.raises(SystemExit) as exc:
            render_version("myapp", {"ver": "1.0.0", "flag": True}, PLAIN)
        assert exc.value.code == 0

    def test_unknown_package_version(self, capsys):
        with pytest.raises(SystemExit):
            render_version(
                "nonexistent-package-xyz", {"ver": True, "flag": True}, PLAIN
            )
        out = capsys.readouterr().out
        assert "UNKNOWN" in out

    def test_invalid_version_cfg_raises(self):
        with pytest.raises(CranberryParseError, match="Invalid version"):
            render_version("myapp", {"ver": 99, "flag": True}, PLAIN)
