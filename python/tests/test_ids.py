"""Tests for ID handling – mirrors test/mocha/testIds.js."""

import pytest

from elkjs import ELK


def test_id_string(elk):
    """Should return no error if id is a string."""
    result = elk.layout({"id": "x"})
    assert result is not None


def test_id_integer(elk):
    """Should return no error if id is an integer."""
    result = elk.layout({"id": 2})
    assert result is not None


def test_id_missing(elk):
    """Should return an error if id is not present."""
    with pytest.raises(Exception):
        elk.layout({})


def test_id_float(elk):
    """Should return an error if id is a non-integral number."""
    with pytest.raises(Exception):
        elk.layout({"id": 1.2})


def test_id_list(elk):
    """Should return an error if id is an array."""
    with pytest.raises(Exception):
        elk.layout({"id": []})


def test_id_dict(elk):
    """Should return an error if id is an object."""
    with pytest.raises(Exception):
        elk.layout({"id": {}})


def test_id_bool(elk):
    """Should return an error if id is a boolean."""
    with pytest.raises(Exception):
        elk.layout({"id": True})
