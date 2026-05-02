"""
Tests for cranberry.registry
"""

import pytest
import cranberry as cb
from cranberry.errors import CranberryPanic
from cranberry.registry import extract_fields, collect_fields, check_global_clashes


# ---------------------------------------------------------------------------
# extract_fields
# ---------------------------------------------------------------------------
class TestExtractFields:
    def test_extracts_option(self):
        class Cmd:
            name: str = cb.option("-n", "--name")

        fields = extract_fields(Cmd)
        assert "name" in fields
        assert fields["name"].kind == "option"

    def test_extracts_flag(self):
        class Cmd:
            verbose: bool = cb.flag("-v", "--verbose")

        fields = extract_fields(Cmd)
        assert "verbose" in fields
        assert fields["verbose"].type is bool

    def test_ignores_non_fieldspec_attributes(self):
        class Cmd:
            name: str = cb.option("-n", "--name")
            value: str = "not a field"

        fields = extract_fields(Cmd)
        assert "name" in fields
        assert "value" not in fields

    def test_resolves_type_from_annotation(self):
        class Cmd:
            count: int = cb.option("-c", "--count")

        fields = extract_fields(Cmd)
        assert fields["count"].type is int

    def test_does_not_override_explicit_type(self):
        class Cmd:
            count: str = cb.option("-c", "--count", type=int)

        fields = extract_fields(Cmd)
        # Explicit type wins.
        assert fields["count"].type is int

    def test_list_annotation_unwrapped_for_arg(self):
        class Cmd:
            items: list[int] = cb.arg(count=None)

        fields = extract_fields(Cmd)
        assert fields["items"].type is int

    def test_does_not_include_inherited_fields(self):
        class Base:
            base_opt: str = cb.option("-b", "--base")

        class Child(Base):
            child_opt: str = cb.option("-c", "--child")

        # extract_fields only looks at own __dict__
        base_fields = extract_fields(Base)
        child_fields = extract_fields(Child)
        assert "base_opt" in base_fields
        assert "base_opt" not in child_fields
        assert "child_opt" in child_fields


# ---------------------------------------------------------------------------
# collect_fields - MRO merging
# ---------------------------------------------------------------------------
class TestCollectFields:
    def test_collects_own_fields(self):
        class Cmd:
            opt: str = cb.option("-o", "--opt")

        fields = collect_fields(Cmd)
        assert "opt" in fields

    def test_merges_base_class_fields(self):
        class Mixin:
            mixin_opt: str = cb.option("-m", "--mixin")

        class Cmd(Mixin):
            cmd_opt: str = cb.option("-c", "--cmd")

        fields = collect_fields(Cmd)
        assert "mixin_opt" in fields
        assert "cmd_opt" in fields

    def test_args_ordered_last(self):
        class Cmd:
            opt: str = cb.option("-o", "--opt")
            name: str = cb.arg()

        fields = collect_fields(Cmd)
        keys = list(fields.keys())
        assert keys.index("opt") < keys.index("name")

    def test_attribute_clash_panics(self):
        class Base:
            opt: str = cb.option("-b", "--base-opt")

        class Child(Base):
            opt: str = cb.option("-c", "--child-opt")

        with pytest.raises(CranberryPanic, match="Field clash"):
            collect_fields(Child)

    def test_flag_clash_panics(self):
        class Base:
            opt_a: str = cb.option("-o", "--opt-a")

        class Child(Base):
            opt_b: str = cb.option("-o", "--opt-b")

        with pytest.raises(CranberryPanic, match="Flag clash"):
            collect_fields(Child)

    def test_allow_clash_suppresses_panic(self):
        class Base:
            opt: str = cb.option("-b", "--base-opt")

        class Child(Base):
            opt: str = cb.option("-c", "--child-opt")

        # Should not raise.
        fields = collect_fields(Child, allow_clash=True)
        assert "opt" in fields


# ---------------------------------------------------------------------------
# check_global_clashes
# ---------------------------------------------------------------------------
class TestCheckGlobalClashes:
    def test_no_clash_passes(self):
        global_fields = {"gflag": cb.flag("-g", "--global")}
        cmd_fields = {"cflag": cb.flag("-c", "--cmd")}
        # Should not raise.
        check_global_clashes(
            global_fields, cmd_fields, global_cls_name="G", command_cls_name="C"
        )

    def test_attribute_clash_panics(self):
        global_fields = {"name": cb.option("-n", "--name")}
        cmd_fields = {"name": cb.option("-m", "--mod-name")}
        with pytest.raises(CranberryPanic, match="Global/command field clash"):
            check_global_clashes(
                global_fields, cmd_fields, global_cls_name="G", command_cls_name="C"
            )

    def test_flag_clash_panics(self):
        global_fields = {"gopt": cb.option("-x", "--xglobal")}
        cmd_fields = {"copt": cb.option("-x", "--xcmd")}
        with pytest.raises(CranberryPanic, match="Global/command flag clash"):
            check_global_clashes(
                global_fields, cmd_fields, global_cls_name="G", command_cls_name="C"
            )
