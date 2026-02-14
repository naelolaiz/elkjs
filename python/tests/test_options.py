"""Tests for layout options – mirrors test/mocha/testOptions.js."""

import copy

import pytest

from elkjs import ELK


SIMPLE_GRAPH = {
    "id": "root",
    "layoutOptions": {"elk.direction": "RIGHT"},
    "children": [
        {"id": "n1", "width": 10, "height": 10},
        {"id": "n2", "width": 10, "height": 10},
    ],
    "edges": [
        {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
    ],
}


def test_respect_options(elk):
    """Should respect 'options'."""
    graph = copy.deepcopy(SIMPLE_GRAPH)
    result = elk.layout(
        graph,
        layout_options={
            "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": 11,
        },
    )
    # left-to-right layout: same y, different x
    assert result["children"][0]["y"] == result["children"][1]["y"]
    assert abs(result["children"][0]["x"] - result["children"][1]["x"]) == 10 + 11


def test_not_override_concrete_options(elk):
    """Should not override concrete layout options."""
    graph = copy.deepcopy(SIMPLE_GRAPH)
    result = elk.layout(
        graph,
        layout_options={"org.eclipse.elk.direction": "DOWN"},
    )
    assert result["layoutOptions"]["elk.direction"] == "RIGHT"
    assert abs(result["children"][0]["x"] - result["children"][1]["x"]) > 0
    assert result["children"][0]["y"] == result["children"][1]["y"]


def test_parse_elk_padding(elk):
    """Should correctly parse ElkPadding."""
    graph = {
        "id": "root",
        "layoutOptions": {"elk.padding": "[left=2, top=3, right=3, bottom=2]"},
        "children": [{"id": "n1", "width": 10, "height": 10}],
    }
    result = elk.layout(graph)
    assert result["children"][0]["x"] == 2
    assert result["children"][0]["y"] == 3
    assert result["width"] == 15
    assert result["height"] == 15


def test_parse_kvector(elk):
    """Should correctly parse KVector."""
    graph = {
        "id": "root",
        "children": [
            {
                "id": "n1",
                "width": 10,
                "height": 10,
                "layoutOptions": {"position": "(23, 43)"},
            }
        ],
    }
    result = elk.layout(graph, layout_options={"algorithm": "fixed"})
    assert result["children"][0]["x"] == 23
    assert result["children"][0]["y"] == 43


def test_parse_kvectorchain(elk):
    """Should correctly parse KVectorChain."""
    graph = {
        "id": "root",
        "children": [
            {"id": "n1", "width": 10, "height": 10},
            {"id": "n2", "width": 10, "height": 10},
        ],
        "edges": [
            {
                "id": "e1",
                "sources": ["n1"],
                "targets": ["n2"],
                "layoutOptions": {"bendPoints": "( {1,2}, {3,4} )"},
            }
        ],
    }
    result = elk.layout(graph, layout_options={"algorithm": "fixed"})
    assert result["edges"][0]["sections"][0]["startPoint"]["x"] == 1
    assert result["edges"][0]["sections"][0]["startPoint"]["y"] == 2
    assert result["edges"][0]["sections"][0]["endPoint"]["x"] == 3
    assert result["edges"][0]["sections"][0]["endPoint"]["y"] == 4


def test_invalid_layouter_id(elk):
    """Should raise an exception for an invalid layouter id."""
    graph = {
        "id": "root",
        "children": [{"id": "n1", "width": 10, "height": 10}],
        "layoutOptions": {"algorithm": "foo.bar.baz"},
    }
    with pytest.raises(Exception, match="UnsupportedConfigurationException"):
        elk.layout(graph)


def test_default_algorithm(elk):
    """Should default to elk.layered if no layouter has been specified."""
    graph = {
        "id": "root",
        "children": [{"id": "n1", "width": 10, "height": 10}],
        "layoutOptions": {},
    }
    # Should not raise
    result = elk.layout(graph)
    assert result is not None


def test_global_layout_options():
    """Should respect global (default) layout options."""
    elk = ELK(
        default_layout_options={
            "elk.layered.spacing.nodeNodeBetweenLayers": 33,
        }
    )
    try:
        graph = copy.deepcopy(SIMPLE_GRAPH)
        result = elk.layout(graph)
        # left-to-right layout: same y, different x
        assert result["children"][0]["y"] == result["children"][1]["y"]
        assert abs(result["children"][0]["x"] - result["children"][1]["x"]) == 10 + 33
    finally:
        elk.terminate_worker()
