"""
Tests for cranberry.decorators
"""

import cranberry as cb
from cranberry import parser as _parser_module


class TestCommandDecorator:
    def test_sets_name(self):
        @cb.command("my-cmd")
        class MyCmd:
            pass

        assert MyCmd.__cb_meta__["name"] == "my-cmd"

    def test_sets_type(self):
        @cb.command("my-cmd")
        class MyCmd:
            pass

        assert MyCmd.__cb_meta__["type"] == "command"

    def test_initialises_subcommands_list(self):
        @cb.command("my-cmd")
        class MyCmd:
            pass

        assert MyCmd.__cb_meta__["subcommands"] == []


class TestSubcommandDecorator:
    def test_registers_single_subcommand(self):
        @cb.command("child")
        class ChildCmd:
            pass

        @cb.command("parent")
        @cb.subcommand(ChildCmd)
        class ParentCmd:
            pass

        assert ChildCmd in ParentCmd.__cb_meta__["subcommands"]

    def test_registers_multiple_subcommands(self):
        @cb.command("a")
        class A:
            pass

        @cb.command("b")
        class B:
            pass

        @cb.command("parent")
        @cb.subcommand(A, B)
        class Parent:
            pass

        assert A in Parent.__cb_meta__["subcommands"]
        assert B in Parent.__cb_meta__["subcommands"]

    def test_stacking_appends(self):
        @cb.command("a")
        class A:
            pass

        @cb.command("b")
        class B:
            pass

        @cb.command("parent")
        @cb.subcommand(A)
        @cb.subcommand(B)
        class Parent:
            pass

        assert A in Parent.__cb_meta__["subcommands"]
        assert B in Parent.__cb_meta__["subcommands"]


class TestDescriptionDecorator:
    def test_sets_description(self):
        @cb.command("cmd")
        @cb.description("A command description.")
        class Cmd:
            pass

        assert Cmd.__cb_meta__["description"] == "A command description."


class TestHelpDecorator:
    def test_default_flag_true(self):
        @cb.app("test-app")
        @cb.help()
        def main():
            pass

        assert main.__cb_meta__["help"]["flag"] is True

    def test_subcommand_false_by_default(self):
        @cb.app("test-app")
        @cb.help()
        def main():
            pass

        assert main.__cb_meta__["help"]["subcommand"] is False

    def test_subcommand_enabled(self):
        @cb.app("test-app")
        @cb.help(subcommand=True)
        def main():
            pass

        assert main.__cb_meta__["help"]["subcommand"] is True

    def test_no_help_disables_flag(self):
        @cb.app("test-app")
        @cb.no_help()
        def main():
            pass

        assert main.__cb_meta__["help"]["flag"] is False
        assert main.__cb_meta__["help"]["subcommand"] is False


class TestVersionDecorator:
    def test_literal_version(self):
        @cb.app("test-app")
        @cb.version("1.2.3")
        def main():
            pass

        assert main.__cb_meta__["version"]["ver"] == "1.2.3"

    def test_flag_true_by_default(self):
        @cb.app("test-app")
        @cb.version("1.0.0")
        def main():
            pass

        assert main.__cb_meta__["version"]["flag"] is True

    def test_subcommand_false_by_default(self):
        @cb.app("test-app")
        @cb.version("1.0.0")
        def main():
            pass

        assert main.__cb_meta__["version"]["subcommand"] is False


class TestStyleDecorator:
    def test_string_style_stored(self):
        @cb.app("test-app")
        @cb.style("colorful")
        def main():
            pass

        assert main.__cb_meta__["style"] == "colorful"


class TestFooterDecorator:
    def test_footer_stored(self):
        @cb.app("test-app")
        @cb.footer("Made with love.")
        def main():
            pass

        assert main.__cb_meta__["footer_message"] == "Made with love."


class TestAppDecorator:
    def test_registers_app_fn(self):
        @cb.app("my-app")
        def main():
            pass

        assert _parser_module._app_fn is main

    def test_sets_name(self):
        @cb.app("my-app")
        def main():
            pass

        assert main.__cb_meta__["name"] == "my-app"

    def test_sets_type(self):
        @cb.app("my-app")
        def main():
            pass

        assert main.__cb_meta__["type"] == "app"


class TestGlobalsDecorator:
    def test_registers_globals_cls(self):
        @cb.globals()
        class G:
            flag: bool = cb.flag("-g", "--global")

        assert _parser_module._globals_cls is G

    def test_sets_cb_globals_attr(self):
        @cb.globals()
        class G:
            flag: bool = cb.flag("-g", "--global")

        assert getattr(G, "__cb_globals__", False) is True
