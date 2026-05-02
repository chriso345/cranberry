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
