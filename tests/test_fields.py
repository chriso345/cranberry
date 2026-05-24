"""
Tests for cranberry.fields
"""

import cranberry as cb
from cranberry.fields import FieldSpec


# ---------------------------------------------------------------------------
# FieldSpec properties
# ---------------------------------------------------------------------------
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
        spec = cb.option("-o", "--opt", required=True)
        assert spec.is_required is True

    def test_is_required_false(self):
        spec = cb.option("-o", "--opt")
        assert spec.is_required is False


# ---------------------------------------------------------------------------
# option()
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# flag()
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# arg()
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# file()
# ---------------------------------------------------------------------------
class TestFileFactory:
    def test_kind(self):
        assert cb.file("-f", "--file").kind == "file"

    def test_type_is_str(self):
        assert cb.file("-f", "--file").type is str

    def test_exists_default_false(self):
        assert cb.file("-f", "--file").exists is False

    def test_exists_true(self):
        assert cb.file("-f", "--file", exists=True).exists is True


# ---------------------------------------------------------------------------
# dir()
# ---------------------------------------------------------------------------
class TestDirFactory:
    def test_kind(self):
        assert cb.dir("-d", "--dir").kind == "dir"

    def test_type_is_str(self):
        assert cb.dir("-d", "--dir").type is str

    def test_exists_true(self):
        assert cb.dir("-d", "--dir", exists=True).exists is True
