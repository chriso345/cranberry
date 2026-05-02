"""
Tests for cranberry.enum
"""

import pytest
import cranberry as cb
from cranberry.errors import CranberryPanic


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@cb.enum(strict=True)
class Color:
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


@cb.enum(strict=False)
class Direction:
    NORTH = "north"
    SOUTH = "south"


# ---------------------------------------------------------------------------
# Decorator creates the class correctly
# ---------------------------------------------------------------------------
class TestEnumDecoratorStructure:
    def test_members_populated(self):
        assert Color._members == {"RED": "red", "GREEN": "green", "BLUE": "blue"}

    def test_class_attributes_set(self):
        assert Color.RED == "red"
        assert Color.GREEN == "green"
        assert Color.BLUE == "blue"

    def test_class_name_preserved(self):
        assert Color.__name__ == "Color"

    def test_strict_flag_true(self):
        assert Color._strict is True

    def test_strict_flag_false(self):
        assert Direction._strict is False

    def test_non_strict_adds_unknown_member(self):
        assert "__UNKNOWN__" in Direction._members

    def test_inherits_cranberry_enum(self):
        from cranberry.enum import CranberryEnum

        assert issubclass(Color, CranberryEnum)


# ---------------------------------------------------------------------------
# from_value - strict mode
# ---------------------------------------------------------------------------
class TestFromValueStrict:
    def test_valid_value_returns_instance(self):
        instance = Color.from_value("red")
        assert str(instance) == "red"

    def test_all_valid_values(self):
        for val in ("red", "green", "blue"):
            assert str(Color.from_value(val)) == val

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError, match="Invalid value"):
            Color.from_value("purple")

    def test_invalid_value_error_lists_valid(self):
        with pytest.raises(ValueError, match="red"):
            Color.from_value("purple")


# ---------------------------------------------------------------------------
# from_value - non-strict mode
# ---------------------------------------------------------------------------
class TestFromValueNonStrict:
    def test_known_value_works(self):
        assert str(Direction.from_value("north")) == "north"

    def test_unknown_value_accepted(self):
        instance = Direction.from_value("east")
        assert str(instance) == "east"

    def test_unknown_value_type(self):
        from cranberry.enum import CranberryEnum

        assert isinstance(Direction.from_value("east"), CranberryEnum)


# ---------------------------------------------------------------------------
# Dunder methods
# ---------------------------------------------------------------------------
class TestCranberryEnumDunders:
    def test_repr(self):
        c = Color.from_value("red")
        assert repr(c) == "Color('red')"

    def test_str(self):
        c = Color.from_value("green")
        assert str(c) == "green"

    def test_eq_enum_to_enum(self):
        a = Color.from_value("blue")
        b = Color.from_value("blue")
        assert a == b

    def test_neq_enum_to_enum(self):
        a = Color.from_value("red")
        b = Color.from_value("green")
        assert a != b

    def test_eq_enum_to_str(self):
        c = Color.from_value("red")
        assert c == "red"
        assert "red" == c  # noqa: SIM300 (intentional symmetry check)

    def test_neq_enum_to_str(self):
        c = Color.from_value("red")
        assert c != "blue"

    def test_eq_returns_not_implemented_for_other_types(self):
        c = Color.from_value("red")
        assert c.__eq__(42) is NotImplemented

    def test_hash_consistency(self):
        a = Color.from_value("red")
        b = Color.from_value("red")
        assert hash(a) == hash(b)

    def test_usable_as_dict_key(self):
        c = Color.from_value("blue")
        d = {c: "value"}
        assert d[Color.from_value("blue")] == "value"


# ---------------------------------------------------------------------------
# Decorator error conditions
# ---------------------------------------------------------------------------
class TestEnumDecoratorErrors:
    def test_no_members_panics(self):
        with pytest.raises(CranberryPanic, match="no string members"):

            @cb.enum(strict=True)
            class Empty:
                pass

    def test_non_string_member_panics(self):
        with pytest.raises(CranberryPanic, match="must be plain strings"):

            @cb.enum(strict=True)
            class Bad:
                VALUE = 42
