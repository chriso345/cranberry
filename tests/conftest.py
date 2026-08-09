"""
Shared pytest fixtures for the Cranberry test suite.
"""

import pytest

from cranberry import parser as _parser_module


@pytest.fixture(autouse=True)
def reset_parser_state():
    """
    Reset the global parser state before every test so that @cb.app and
    @cb.globals registrations from one test don't bleed into the next.
    """
    _parser_module._app_fn = None
    _parser_module._globals_cls = None
    yield
    _parser_module._app_fn = None
    _parser_module._globals_cls = None
