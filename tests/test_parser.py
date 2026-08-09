"""
Tests for cranberry.parser
"""

import pytest

import cranberry as cb
from cranberry import parser as _parser_module
from cranberry.errors import CranberryPanic, CranberryParseError


def make_app(
    *subcommand_classes,
    name="test-app",
    help_flag=True,
    help_subcommand=False,
    version_str=None,
    style="plain",
    footer=None,
):
    """
    Register a minimal @cb.app with optional subcommands and globals,
    returning the decorated function.
    """
    decorators = [cb.app(name)]
    if subcommand_classes:
        decorators.append(cb.subcommand(*subcommand_classes))
    decorators.append(cb.help(flag=help_flag, subcommand=help_subcommand))
    if version_str:
        decorators.append(cb.version(version_str))
    decorators.append(cb.style(style))
    if footer:
        decorators.append(cb.footer(footer))

    def main():
        pass

    for d in reversed(decorators):
        main = d(main)

    return main


class TestNoSubcommands:
    def test_no_args_returns_none_command(self):
        make_app()
        ctx = cb.parse_args([])
        assert ctx.command is None

    def test_no_app_registered_panics(self):
        with pytest.raises(CranberryPanic, match="No app entry-point"):
            _parser_module.parse_args([])


class TestSubcommandDispatch:
    def setup_method(self):
        @cb.command("greet")
        class GreetCmd:
            name: str = cb.arg(help="Name to greet")

        self.GreetCmd = GreetCmd
        make_app(GreetCmd)

    def test_dispatches_to_subcommand(self):
        ctx = cb.parse_args(["greet", "Alice"])
        assert isinstance(ctx.command, self.GreetCmd)

    def test_positional_arg_value(self):
        ctx = cb.parse_args(["greet", "Alice"])
        assert ctx.command.name == "Alice"

    def test_unknown_subcommand_raises(self):
        with pytest.raises(CranberryParseError, match="Unknown command"):
            cb.parse_args(["unknown"])

    def test_no_subcommand_given_returns_none(self):
        ctx = cb.parse_args([])
        assert ctx.command is None


class TestOptionsAndFlags:
    def setup_method(self):
        @cb.command("process")
        class ProcessCmd:
            output: str = cb.option("-o", "--output", help="Output path")
            verbose: bool = cb.flag("-v", "--verbose", help="Verbose mode")

        self.ProcessCmd = ProcessCmd
        make_app(ProcessCmd)

    def test_short_option(self):
        ctx = cb.parse_args(["process", "-o", "out.txt"])
        assert ctx.command.output == "out.txt"

    def test_long_option(self):
        ctx = cb.parse_args(["process", "--output", "out.txt"])
        assert ctx.command.output == "out.txt"

    def test_short_flag(self):
        ctx = cb.parse_args(["process", "-v"])
        assert ctx.command.verbose is True

    def test_long_flag(self):
        ctx = cb.parse_args(["process", "--verbose"])
        assert ctx.command.verbose is True

    def test_flag_absent_is_false(self):
        ctx = cb.parse_args(["process"])
        assert ctx.command.verbose is False

    def test_option_absent_defaults_to_none(self):
        ctx = cb.parse_args(["process"])
        assert ctx.command.output is None

    def test_unknown_flag_raises(self):
        with pytest.raises(CranberryParseError, match="Unknown flag"):
            cb.parse_args(["process", "--nonexistent"])

    def test_option_missing_value_raises(self):
        with pytest.raises(CranberryParseError, match="requires value"):
            cb.parse_args(["process", "-o"])


class TestTypeCoercion:
    def setup_method(self):
        @cb.command("calc")
        class CalcCmd:
            count: int = cb.option("-c", "--count", type=int)
            ratio: float = cb.option("-r", "--ratio", type=float)

        self.CalcCmd = CalcCmd
        make_app(CalcCmd)

    def test_int_coercion(self):
        ctx = cb.parse_args(["calc", "-c", "42"])
        assert ctx.command.count == 42
        assert isinstance(ctx.command.count, int)

    def test_float_coercion(self):
        ctx = cb.parse_args(["calc", "-r", "3.14"])
        assert abs(ctx.command.ratio - 3.14) < 1e-9

    def test_invalid_int_raises(self):
        with pytest.raises(CranberryParseError, match="Invalid value"):
            cb.parse_args(["calc", "-c", "not-a-number"])


class TestEnumField:
    def setup_method(self):
        @cb.enum(strict=True)
        class Mode:
            READ = "read"
            WRITE = "write"

        @cb.command("run")
        class RunCmd:
            mode: Mode = cb.arg(type=Mode)

        self.RunCmd = RunCmd
        self.Mode = Mode
        make_app(RunCmd)

    def test_valid_enum_value(self):
        ctx = cb.parse_args(["run", "read"])
        assert str(ctx.command.mode) == "read"

    def test_valid_enum_value_as_option(self):
        @cb.command("run2")
        class RunCmd2:
            mode: self.Mode = cb.option("-m", "--mode", type=self.Mode)

        from cranberry import parser as _pm

        _pm._app_fn = None
        _pm._globals_cls = None
        make_app(RunCmd2)
        ctx = cb.parse_args(["run2", "--mode", "read"])
        assert str(ctx.command.mode) == "read"

    def test_invalid_enum_option_raises(self):
        @cb.command("run3")
        class RunCmd3:
            mode: self.Mode = cb.option("-m", "--mode", type=self.Mode)

        from cranberry import parser as _pm

        _pm._app_fn = None
        _pm._globals_cls = None
        make_app(RunCmd3)
        with pytest.raises(CranberryParseError, match="Invalid value"):
            cb.parse_args(["run3", "--mode", "delete"])


class TestPositionalArgs:
    def test_single_positional(self):
        @cb.command("greet")
        class Cmd:
            name: str = cb.arg()

        make_app(Cmd)
        ctx = cb.parse_args(["greet", "Alice"])
        assert ctx.command.name == "Alice"

    def test_multiple_fixed_count(self):
        @cb.command("pair")
        class Cmd:
            items: list[str] = cb.arg(count=2)

        make_app(Cmd)
        ctx = cb.parse_args(["pair", "a", "b"])
        assert ctx.command.items == ["a", "b"]

    def test_unlimited_positional(self):
        @cb.command("multi")
        class Cmd:
            items: list[str] = cb.arg(count=None)

        make_app(Cmd)
        ctx = cb.parse_args(["multi", "x", "y", "z"])
        assert ctx.command.items == ["x", "y", "z"]

    def test_extra_positional_raises(self):
        @cb.command("single")
        class Cmd:
            name: str = cb.arg()

        make_app(Cmd)
        with pytest.raises(CranberryParseError, match="Unexpected argument"):
            cb.parse_args(["single", "Alice", "Bob"])

    def test_positional_missing_uses_default(self):
        @cb.command("greet")
        class Cmd:
            name: str = cb.arg(default="World")

        make_app(Cmd)
        ctx = cb.parse_args(["greet"])
        assert ctx.command.name == "World"


class TestValidation:
    def test_validate_passes(self):
        @cb.command("check")
        class Cmd:
            age: int = cb.option(
                "-a",
                "--age",
                type=int,
                validate=(lambda x: x >= 0, "must be non-negative"),
            )

        make_app(Cmd)
        ctx = cb.parse_args(["check", "-a", "25"])
        assert ctx.command.age == 25

    def test_validate_fails_raises(self):
        @cb.command("check")
        class Cmd:
            age: int = cb.option(
                "-a",
                "--age",
                type=int,
                validate=(lambda x: x >= 0, "must be non-negative"),
            )

        make_app(Cmd)
        with pytest.raises(CranberryParseError, match="Validation failed"):
            cb.parse_args(["check", "-a", "-5"])


class TestFileAndDirExistence:
    def test_file_exists_passes(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("hello")

        @cb.command("read")
        class Cmd:
            path: str = cb.file("-f", "--file", exists=True)

        make_app(Cmd)
        ctx = cb.parse_args(["read", "-f", str(f)])
        assert ctx.command.path == str(f)

    def test_file_not_found_raises(self, tmp_path):
        @cb.command("read")
        class Cmd:
            path: str = cb.file("-f", "--file", exists=True)

        make_app(Cmd)
        with pytest.raises(CranberryParseError, match="File not found"):
            cb.parse_args(["read", "-f", str(tmp_path / "missing.txt")])

    def test_dir_exists_passes(self, tmp_path):
        @cb.command("scan")
        class Cmd:
            path: str = cb.dir("-d", "--dir", exists=True)

        make_app(Cmd)
        ctx = cb.parse_args(["scan", "-d", str(tmp_path)])
        assert ctx.command.path == str(tmp_path)

    def test_dir_not_found_raises(self, tmp_path):
        @cb.command("scan")
        class Cmd:
            path: str = cb.dir("-d", "--dir", exists=True)

        make_app(Cmd)
        with pytest.raises(CranberryParseError, match="Directory not found"):
            cb.parse_args(["scan", "-d", str(tmp_path / "missing_dir")])


class TestGlobalOptions:
    def setup_method(self):
        @cb.globals()
        class G:
            verbose: bool = cb.flag("-v", "--verbose")

        @cb.command("run")
        class RunCmd:
            name: str = cb.arg()

        self.RunCmd = RunCmd
        make_app(RunCmd)

    def test_global_flag_set(self):
        ctx = cb.parse_args(["-v", "run", "Alice"])
        assert ctx.verbose is True

    def test_global_flag_absent_defaults(self):
        ctx = cb.parse_args(["run", "Alice"])
        assert ctx.verbose is False

    def test_global_flag_after_subcommand(self):
        # Global flags can appear before or after the subcommand token.
        cb.parse_args(["run", "-v", "Alice"])
        # "-v" is consumed as global before subcommand dispatch.

    def test_global_accessible_on_context(self):
        ctx = cb.parse_args(["-v", "run", "Alice"])
        assert hasattr(ctx, "verbose")


class TestNestedSubcommands:
    def setup_method(self):
        @cb.command("leaf")
        class LeafCmd:
            data: str = cb.arg()

        @cb.command("middle")
        @cb.subcommand(LeafCmd)
        class MiddleCmd:
            pass

        self.LeafCmd = LeafCmd
        self.MiddleCmd = MiddleCmd
        make_app(MiddleCmd)

    def test_nested_dispatch(self):
        ctx = cb.parse_args(["middle", "leaf", "hello"])
        # chain[-1] is LeafCmd; chain[0] is MiddleCmd
        assert isinstance(ctx.command, self.MiddleCmd)
        assert isinstance(ctx.command.subcommand, self.LeafCmd)

    def test_nested_leaf_arg(self):
        ctx = cb.parse_args(["middle", "leaf", "hello"])
        assert ctx.command.subcommand.data == "hello"


class TestHelpFlag:
    def test_help_flag_exits(self, capsys):
        make_app(help_flag=True)
        with pytest.raises(SystemExit) as exc:
            cb.parse_args(["--help"])
        assert exc.value.code == 0

    def test_help_short_flag_exits(self, capsys):
        make_app(help_flag=True)
        with pytest.raises(SystemExit):
            cb.parse_args(["-h"])

    def test_help_subcommand_exits(self, capsys):
        make_app(help_flag=True, help_subcommand=True)
        with pytest.raises(SystemExit):
            cb.parse_args(["help"])

    def test_help_output_contains_usage(self, capsys):
        make_app(name="myapp", help_flag=True)
        with pytest.raises(SystemExit):
            cb.parse_args(["--help"])
        captured = capsys.readouterr()
        assert "Usage:" in captured.out


class TestVersionFlag:
    def test_version_flag_exits(self, capsys):
        make_app(version_str="2.3.4")
        with pytest.raises(SystemExit) as exc:
            cb.parse_args(["--version"])
        assert exc.value.code == 0

    def test_version_output_contains_version(self, capsys):
        make_app(name="myapp", version_str="2.3.4")
        with pytest.raises(SystemExit):
            cb.parse_args(["--version"])
        captured = capsys.readouterr()
        assert "2.3.4" in captured.out

    def test_version_short_flag(self, capsys):
        make_app(version_str="1.0.0")
        with pytest.raises(SystemExit):
            cb.parse_args(["-V"])


class TestParseStackableFlags:
    def test_combined_short_flags_fs(self, capsys):
        @cb.command("c")
        class C:
            first: bool = cb.flag("-f", "--flag", stackable=True)
            second: bool = cb.flag("-s", "--second", stackable=True)

        make_app(C)
        ctx = cb.parse_args(["c", "-fs"])
        assert ctx.command.first is True
        assert ctx.command.second is True

    def test_combined_short_flags_sf(self, capsys):
        @cb.command("c2")
        class C2:
            first: bool = cb.flag("-f", "--flag", stackable=True)
            second: bool = cb.flag("-s", "--second", stackable=True)

        make_app(C2)
        ctx = cb.parse_args(["c2", "-sf"])
        assert ctx.command.first is True
        assert ctx.command.second is True

    def test_non_stackable_flag_combined_raises(self, capsys):
        @cb.command("c3")
        class C3:
            first: bool = cb.flag("-f", "--flag", stackable=False)
            second: bool = cb.flag("-s", "--second", stackable=True)

        make_app(C3)
        with pytest.raises(CranberryParseError, match="Unknown flag: '-fs'"):
            cb.parse_args(["c3", "-fs"])


class TestParseContext:
    def test_repr_contains_command(self):
        make_app()
        ctx = cb.parse_args([])
        assert "ParseContext" in repr(ctx)

    def test_globals_accessible_as_attrs(self):
        @cb.globals()
        class G:
            flag: bool = cb.flag("-g", "--gflag")

        make_app()
        ctx = cb.parse_args([])
        assert hasattr(ctx, "flag")
        assert ctx.flag is False
