"""
Tests for cranberry.fields
"""

import pytest

import cranberry as cb
from cranberry.fields import FieldSpec


class TestFieldSpecProperties:
    def test_dest_from_long(self):
        spec = cb.option("-o", "--output-file")
        assert spec.dest == "output_file"

    def test_dest_none_when_no_long(self):
        spec = cb.arg()
        assert spec.dest is None

    def test_metavar_from_long(self):
        spec = cb.option("-o", "--output-file")
        assert spec.metavar == "OUTPUT_FILE"

    def test_metavar_from_short_only(self):
        spec = FieldSpec(kind="option", short="-o")
        assert spec.metavar == "O"

    def test_metavar_fallback(self):
        spec = FieldSpec(kind="option")
        assert spec.metavar == "VALUE"

    def test_is_required_true(self):
        spec = cb.option("-o", "--opt")
        assert spec.is_required is True

    def test_is_required_false(self):
        spec = cb.option("-o", "--opt", default="x")
        assert spec.is_required is False


class TestOptionFactory:
    def test_kind(self):
        assert cb.option("-o", "--opt").kind == "option"

    def test_short_long(self):
        spec = cb.option("-o", "--output")
        assert spec.short == "-o"
        assert spec.long == "--output"

    def test_default(self):
        assert cb.option("-o", "--opt", default="x").default == "x"

    def test_help(self):
        assert cb.option("-o", "--opt", help="desc").help == "desc"

    def test_type(self):
        assert cb.option("-o", "--opt", type=int).type is int

    def test_validate_stored(self):
        v = (lambda x: x > 0, "must be positive")
        spec = cb.option("-o", "--opt", validate=v)
        assert spec.validate is v

    def test_none_short(self):
        spec = cb.option(None, "--opt")
        assert spec.short is None
        assert spec.long is not None

    def test_none_long(self):
        spec = cb.option("--opt", None)
        assert spec.short is not None
        assert spec.long is None


class TestFlagFactory:
    def test_kind(self):
        assert cb.flag("-f", "--flag").kind == "flag"

    def test_type_is_bool(self):
        assert cb.flag("-f", "--flag").type is bool

    def test_default_false(self):
        assert cb.flag("-f", "--flag").default is False

    def test_default_true(self):
        assert cb.flag("-f", "--flag", default=True).default is True

    def test_stackable_false(self):
        assert cb.flag("-f", "--flag").stackable is False

    def test_stackable_true(self):
        assert cb.flag("-f", "--flag", stackable=True).stackable is True

    def test_none_short(self):
        spec = cb.flag(None, "--flag")
        assert spec.short is None
        assert spec.long is not None

    def test_none_long(self):
        spec = cb.flag("--flag", None)
        assert spec.short is not None
        assert spec.long is None


class TestArgFactory:
    def test_kind(self):
        assert cb.arg().kind == "arg"

    def test_count_default_one(self):
        assert cb.arg().count == 1

    def test_count_none_means_unlimited(self):
        assert cb.arg(count=None).count is None

    def test_count_explicit(self):
        assert cb.arg(count=3).count == 3

    def test_enforce_count_default_false(self):
        assert cb.arg().enforce_count is False

    def test_enforce_count_true(self):
        assert cb.arg(enforce_count=True).enforce_count is True

    def test_type(self):
        assert cb.arg(type=int).type is int
        assert cb.arg(type=str).type is str


class TestFileFactory:
    def test_kind(self):
        assert cb.file("-f", "--file").kind == "file"

    def test_type_is_str(self):
        assert cb.file("-f", "--file").type is str

    def test_exists_default_false(self):
        assert cb.file("-f", "--file").exists is False

    def test_exists_true(self):
        assert cb.file("-f", "--file", exists=True).exists is True


class TestDirFactory:
    def test_kind(self):
        assert cb.dir("-d", "--dir").kind == "dir"

    def test_type_is_str(self):
        assert cb.dir("-d", "--dir").type is str

    def test_exists_true(self):
        assert cb.dir("-d", "--dir", exists=True).exists is True


class TestFieldsManualConstruction:
    def test_required_field_supplied(self):
        class Cmd(cb.Fields):
            name: str = cb.arg()

        cmd = Cmd(name="Ada")
        assert cmd.name == "Ada"

    def test_missing_required_field_panics(self):
        class Cmd(cb.Fields):
            name: str = cb.arg()

        with pytest.raises(cb.CranberryPanic):
            Cmd()

    def test_optional_field_defaults(self):
        class Cmd(cb.Fields):
            flag: bool = cb.flag("-f", "--flag")

        cmd = Cmd()
        assert cmd.flag is False

    def test_optional_field_overridden(self):
        class Cmd(cb.Fields):
            flag: bool = cb.flag("-f", "--flag")

        cmd = Cmd(flag=True)
        assert cmd.flag is True

    def test_unexpected_kwarg_panics(self):
        class Cmd(cb.Fields):
            name: str = cb.arg()

        with pytest.raises(cb.CranberryPanic):
            Cmd(name="Ada", bogus=1)

    def test_fields_merged_across_mixins(self):
        class Mixin(cb.Fields):
            shared: str = cb.option("-s", "--shared")

        class Cmd(Mixin):
            own: str = cb.arg()

        cmd = Cmd(shared="a", own="b")
        assert cmd.shared == "a"
        assert cmd.own == "b"

    def test_subcommand_defaults_to_none_without_any_declaration(self):
        class Child(cb.Fields):
            pass

        class Cmd(cb.Fields):
            name: str = cb.arg()

        cmd = Cmd(name="Ada")
        assert cmd.subcommand is None

    def test_subcommand_accepts_explicit_none_via_attribute(self):
        class Cmd(cb.Fields):
            name: str = cb.arg()

        cmd = Cmd(name="Ada")
        cmd.subcommand = None
        assert cmd.subcommand is None

    def test_subcommand_accepts_instance_via_attribute(self):
        class Child(cb.Fields):
            pass

        class Cmd(cb.Fields):
            name: str = cb.arg()

        child = Child()
        cmd = Cmd(name="Ada")
        cmd.subcommand = child
        assert cmd.subcommand is child

    def test_subcommand_is_not_a_constructor_keyword(self):
        class Child(cb.Fields):
            pass

        class Cmd(cb.Fields):
            name: str = cb.arg()

        with pytest.raises(cb.CranberryPanic):
            Cmd(name="Ada", subcommand=Child())
