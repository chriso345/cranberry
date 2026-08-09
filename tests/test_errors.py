"""
Tests for cranberry.errors
"""

import pytest

from cranberry.errors import CranberryPanic, CranberryParseError, panic


class TestCranberryPanic:
    def test_is_runtime_error(self):
        assert issubclass(CranberryPanic, RuntimeError)

    def test_message_preserved(self):
        exc = CranberryPanic("bad config")
        assert "bad config" in str(exc)


class TestCranberryParseError:
    def test_is_value_error(self):
        assert issubclass(CranberryParseError, ValueError)

    def test_message_preserved(self):
        exc = CranberryParseError("bad arg")
        assert "bad arg" in str(exc)


class TestPanic:
    def test_panic_raises_cranberry_panic(self):
        with pytest.raises(CranberryPanic, match="something went wrong"):
            panic("something went wrong")

    def test_panic_type_is_cranberry_panic(self):
        with pytest.raises(CranberryPanic):
            panic("oops")
