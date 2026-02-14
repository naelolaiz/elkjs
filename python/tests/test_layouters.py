"""Tests for layout algorithms – mirrors test/mocha/testLayouters.js."""

import copy

import pytest

from elkjs import ELK

GRAPH = {
    "id": "root",
    "children": [
        {"id": "n1", "x": 20, "y": 20, "width": 10, "height": 10},
        {"id": "n2", "x": 50, "y": 50, "width": 10, "height": 10},
    ],
    "edges": [{"id": "e1", "sources": ["n1"], "targets": ["n2"]}],
}

GRAPH_OVERLAPPING = {
    "id": "root",
    "children": [
        {"id": "n1", "x": 20, "y": 20, "width": 10, "height": 10},
        {"id": "n2", "x": 25, "y": 25, "width": 10, "height": 10},
    ],
    "edges": [{"id": "e1", "sources": ["n1"], "targets": ["n2"]}],
}


def test_spore_compaction(elk):
    """SPOrE Compaction."""
    graph = copy.deepcopy(GRAPH)
    result = elk.layout(
        graph,
        layout_options={
            "algorithm": "elk.sporeCompaction",
            "elk.spacing.nodeNode": 14,
            "elk.padding": "[left=2, top=2, right=2, bottom=2]",
        },
    )
    assert result["children"][0]["x"] == 2
    assert result["children"][0]["y"] == 2
    assert result["children"][1]["x"] == 26
    assert result["children"][1]["y"] == 26


def test_spore_overlap_removal(elk):
    """SPOrE Overlap Removal."""
    graph = copy.deepcopy(GRAPH_OVERLAPPING)
    result = elk.layout(
        graph,
        layout_options={
            "algorithm": "elk.sporeOverlap",
            "elk.spacing.nodeNode": 13,
            "elk.padding": "[left=3, top=3, right=3, bottom=3]",
        },
    )
    assert result["children"][0]["x"] == 3
    assert result["children"][0]["y"] == 3
    assert result["children"][1]["x"] == 26
    assert result["children"][1]["y"] == 26


def test_rectangle_packing(elk):
    """Rectangle Packing."""
    graph = copy.deepcopy(GRAPH_OVERLAPPING)
    result = elk.layout(
        graph,
        layout_options={"algorithm": "elk.rectpacking"},
    )
    assert result is not None
