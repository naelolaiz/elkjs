"""Bug regression tests – mirrors test/mocha/test-bug-*.js."""

import copy

import pytest

from elkjs import ELK


# --- elkjs#63 ---

GRAPH_63 = {
    "id": "root",
    "properties": {
        "algorithm": "layered",
        "layering.strategy": "COFFMAN_GRAHAM",
    },
    "children": [
        {"id": "n1", "width": 30, "height": 30},
        {"id": "n2", "width": 30, "height": 30},
        {"id": "n3", "width": 30, "height": 30},
    ],
    "edges": [
        {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
        {"id": "e2", "sources": ["n1"], "targets": ["n3"]},
        # this selfloop yields a stack overflow for <= 0.4.1
        {"id": "e3", "sources": ["n1"], "targets": ["n1"]},
    ],
}


def test_bug_63_coffman_graham_selfloops(elk):
    """COFFMAN_GRAHAM layering should cope with selfloops."""
    result = elk.layout(copy.deepcopy(GRAPH_63))
    assert result is not None


# --- elkjs#8 ---

GRAPH_8 = {
    "id": "root",
    "children": [
        {
            "id": "A",
            "children": [
                {"id": "a1"},
                {"id": "a2"},
                {"id": "$generated_A_initial_0"},
            ],
            "edges": [{"id": "a1:0", "sources": ["a1"], "targets": ["A"]}],
        },
        {"id": "$generated_root_initial_0"},
    ],
}

GRAPH_8_PRIMITIVE = {
    "id": "root",
    "children": [
        {
            "id": "A",
            "children": [
                {"id": "a1"},
                {"id": "a2"},
                {"id": "$generated_A_initial_0"},
            ],
            "edges": [{"id": "a1:0", "source": "a1", "target": "A"}],
        },
        {"id": "$generated_root_initial_0"},
    ],
}


def test_bug_8_separate_children(elk):
    """Should raise error for simple bottom-up layout with SEPARATE_CHILDREN."""
    with pytest.raises(Exception, match="UnsupportedGraphException"):
        elk.layout(
            copy.deepcopy(GRAPH_8),
            layout_options={"hierarchyHandling": "SEPARATE_CHILDREN"},
        )


def test_bug_8_separate_children_primitive(elk):
    """Should raise error for bottom-up layout with SEPARATE_CHILDREN (primitive edge format)."""
    with pytest.raises(Exception, match="UnsupportedGraphException"):
        elk.layout(
            copy.deepcopy(GRAPH_8_PRIMITIVE),
            layout_options={"hierarchyHandling": "SEPARATE_CHILDREN"},
        )


def test_bug_8_hierarchical_layout(elk):
    """Should add edge sections for hierarchical layout."""
    result = elk.layout(
        copy.deepcopy(GRAPH_8),
        layout_options={"hierarchyHandling": "INCLUDE_CHILDREN"},
    )
    sections = result["children"][0]["edges"][0]["sections"]
    assert sections is not None
    assert len(sections) == 1
    assert "startPoint" in sections[0]
    assert "endPoint" in sections[0]


def test_bug_8_hierarchical_layout_primitive(elk):
    """Should add edge sections for hierarchical layout (primitive edge format)."""
    result = elk.layout(
        copy.deepcopy(GRAPH_8_PRIMITIVE),
        layout_options={"hierarchyHandling": "INCLUDE_CHILDREN"},
    )
    sections = result["children"][0]["edges"][0]["sections"]
    assert sections is not None
    assert len(sections) == 1
    assert "startPoint" in sections[0]
    assert "endPoint" in sections[0]


# --- klayjs#23 ---

GRAPH_KLAY_23 = {
    "id": "root",
    "layoutOptions": {
        "elk.algorithm": "layered",
        "elk.layered.crossingMinimization.strategy": "INTERACTIVE",
    },
    "children": [
        {"id": "n1", "width": 10, "height": 10},
        {"id": "n2", "width": 10, "height": 10},
    ],
    "edges": [
        {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
        {
            "id": "e2",
            "sources": ["n1"],
            "targets": ["n2"],
            "sections": [
                {
                    "id": "es2",
                    "startPoint": {"x": 0, "y": 0},
                    "bendPoints": [{"x": 20, "y": 0}],
                    "endPoint": {"x": 50, "y": 0},
                }
            ],
        },
    ],
}


def test_klay_23_unspecified_bendpoints(elk):
    """Should be fine with unspecified bendpoints."""
    result = elk.layout(copy.deepcopy(GRAPH_KLAY_23))
    assert result is not None


# --- klayjs#22 ---

GRAPH_KLAY_22 = {
    "id": "root",
    "children": [
        {
            "id": "n1",
            "width": 100,
            "height": 100,
            "labels": [{"id": "l1", "text": "Label1"}],
        },
        {
            "id": "n2",
            "width": 100,
            "height": 100,
            "labels": [
                {
                    "id": "l2",
                    "text": "Label2",
                    "layoutOptions": {
                        "elk.nodeLabels.placement": "INSIDE V_CENTER H_CENTER",
                    },
                }
            ],
        },
    ],
    "edges": [
        {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
    ],
}


def test_klay_22_label_placement(elk):
    """Should place labels according to set options."""
    graph = copy.deepcopy(GRAPH_KLAY_22)
    result = elk.layout(
        graph,
        layout_options={"elk.nodeLabels.placement": "OUTSIDE V_TOP H_CENTER"},
    )
    # OUTSIDE V_TOP H_CENTER
    assert result["children"][0]["labels"][0]["x"] == 50
    assert result["children"][0]["labels"][0]["y"] == -5
    # INSIDE V_CENTER H_CENTER
    assert result["children"][1]["labels"][0]["x"] == 50
    assert result["children"][1]["labels"][0]["y"] == 50
