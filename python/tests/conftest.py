"""Shared fixtures and configuration for elkjs Python tests."""

import os
import sys

import pytest

# Ensure the Python package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from elkjs import ELK


@pytest.fixture(scope="session")
def elk():
    """Provide a shared ELK instance for the entire test session."""
    instance = ELK()
    yield instance
    instance.terminate_worker()
