"""Shared fixtures for epub-chinese-cleaner tests."""

import sys
import os
import tempfile

import pytest

# Make scripts/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from convert_horizontal import _make_test_epub


@pytest.fixture
def tmp_epub(tmp_path):
    """Factory fixture: call with kwargs to create a test epub, returns its path."""

    def _factory(writing_mode="vertical-rl", page_direction="rtl", filename="test.epub"):
        path = tmp_path / filename
        _make_test_epub(str(path), writing_mode=writing_mode, page_direction=page_direction)
        return str(path)

    return _factory
