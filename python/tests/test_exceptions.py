"""Tests for exception handling – mirrors test/mocha/testRaiseException.js."""

import pytest

from elkjs import ELK


GRAPH = {
    "id": "root",
    "properties": {"algorithm": "layered"},
    "children": [
        {"id": "n1", "width": 30, "height": 30, "layoutOptions": {"layerConstraint": "FIRST"}},
        {"id": "n2", "width": 30, "height": 30, "layoutOptions": {"layerConstraint": "FIRST"}},
        {"id": "n3", "width": 30, "height": 30, "layoutOptions": {"layerConstraint": "FIRST"}},
    ],
    "edges": [
        {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
        {"id": "e2", "sources": ["n2"], "targets": ["n3"]},
        {"id": "e3", "sources": ["n3"], "targets": ["n1"]},
    ],
}


def test_unsupported_configuration(elk):
    """Should report an unsupported configuration."""
    with pytest.raises(Exception, match="UnsupportedConfigurationException"):
        elk.layout(GRAPH)
