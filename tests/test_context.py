"""
Tests for cranberry.context
"""

from cranberry.context import ParseContext


class TestParseContext:
    def test_command_stored(self):
        ctx = ParseContext(command="cmd", globals_={})
        assert ctx.command == "cmd"

    def test_command_none(self):
        ctx = ParseContext(command=None, globals_={})
        assert ctx.command is None

    def test_globals_become_attributes(self):
        ctx = ParseContext(command=None, globals_={"flag": True, "count": 5})
        assert ctx.flag is True
        assert ctx.count == 5

    def test_empty_globals(self):
        ctx = ParseContext(command=None, globals_={})
        assert ctx.command is None

    def test_repr_contains_class_name(self):
        ctx = ParseContext(command=None, globals_={})
        assert "ParseContext" in repr(ctx)

    def test_repr_shows_command(self):
        ctx = ParseContext(command="my-cmd", globals_={})
        assert "my-cmd" in repr(ctx)

    def test_repr_shows_globals(self):
        ctx = ParseContext(command=None, globals_={"key": "val"})
        assert "key" in repr(ctx)

    def test_help_top_level_renders_usage_and_app_name(self):
        import cranberry as cb

        # Register a minimal app with a subcommand to ensure the help layout
        @cb.command("sub")
        class Sub:
            pass

        def main():
            pass

        # Apply decorators in a safe order
        main = cb.app("myapp")(main)
        main = cb.subcommand(Sub)(main)
        main = cb.help(flag=True)(main)
        main = cb.style("plain")(main)

        ctx = cb.parse_args([])
        out = ctx.help()
        assert "Usage:" in out
        assert "myapp" in out

    def test_help_for_subcommand_includes_parent_and_child(self):
        import cranberry as cb

        @cb.command("leaf")
        class Leaf:
            name: str = cb.arg()

        @cb.command("parent")
        @cb.subcommand(Leaf)
        class Parent:
            pass

        def main():
            pass

        main = cb.app("theapp")(main)
        main = cb.subcommand(Parent)(main)
        main = cb.help(flag=True)(main)
        main = cb.style("plain")(main)

        ctx = cb.parse_args(["parent", "leaf", "value"])
        out = ctx.help(ctx.command)
        assert "Usage:" in out
        assert "parent" in out
        assert "leaf" in out
