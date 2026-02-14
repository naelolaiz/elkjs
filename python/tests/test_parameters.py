"""Tests for parameter validation – mirrors test/mocha/testParameters.js."""

import pytest

from elkjs import ELK


def test_layout_rejected_if_graph_is_missing(elk):
    """layout() should raise if graph is None."""
    with pytest.raises(ValueError, match="Missing mandatory parameter"):
        elk.layout(None)


def test_layout_rejected_if_graph_is_not_passed(elk):
    """layout() should raise if graph is omitted."""
    with pytest.raises(ValueError, match="Missing mandatory parameter"):
        elk.layout()


def test_layout_succeeds_with_graph(elk):
    """layout() should succeed if a graph is specified."""
    result = elk.layout({"id": 2})
    assert result is not None
