"""
Tests for the elkjs pure Python port.

These tests are ported from the JavaScript mocha test suite
in test/mocha/ of the original elkjs repository.
"""

import copy
import math
import pytest
import sys
import os

# Add parent directory to path so we can import elkjs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from elkjs import ELK
from elkjs.elk_types import (
    ElkNode, ElkPort, ElkExtendedEdge, ElkLabel, ElkPoint,
    ElkEdgeSection, graph_to_dict, dict_to_graph,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def elk():
    return ELK()


@pytest.fixture
def simple_graph():
    return {
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


# ---------------------------------------------------------------------------
# Test: Parameters (ported from testParameters.js)
# ---------------------------------------------------------------------------

class TestParameters:
    """Tests from testParameters.js"""

    def test_should_raise_if_graph_is_missing(self, elk):
        with pytest.raises(ValueError, match="Missing mandatory parameter"):
            elk.layout(None)

    def test_should_succeed_if_graph_is_specified(self, elk):
        result = elk.layout({"id": 2})
        assert result is not None


# ---------------------------------------------------------------------------
# Test: IDs (ported from testIds.js)
# ---------------------------------------------------------------------------

class TestIds:
    """Tests from testIds.js"""

    def test_no_error_if_id_is_string(self, elk):
        result = elk.layout({"id": "x"})
        assert result is not None

    def test_no_error_if_id_is_integer(self, elk):
        result = elk.layout({"id": 2})
        assert result is not None

    def test_error_if_id_not_present(self, elk):
        with pytest.raises(ValueError):
            elk.layout({})

    def test_error_if_id_is_non_integral_number(self, elk):
        with pytest.raises(ValueError):
            elk.layout({"id": 1.2})

    def test_error_if_id_is_array(self, elk):
        with pytest.raises(ValueError):
            elk.layout({"id": []})

    def test_error_if_id_is_object(self, elk):
        with pytest.raises(ValueError):
            elk.layout({"id": {}})

    def test_error_if_id_is_boolean(self, elk):
        with pytest.raises(ValueError):
            elk.layout({"id": True})


# ---------------------------------------------------------------------------
# Test: Layout Options (ported from testOptions.js)
# ---------------------------------------------------------------------------

class TestLayoutOptions:
    """Tests from testOptions.js"""

    def test_should_respect_options(self, elk):
        graph = {
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
        result = elk.layout(graph, layout_options={
            "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": "11",
        })
        # left-to-right layout: same y, different x
        assert result["children"][0]["y"] == result["children"][1]["y"]
        assert abs(result["children"][0]["x"] - result["children"][1]["x"]) == 10 + 11

    def test_should_not_override_concrete_layout_options(self, elk):
        graph = {
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
        result = elk.layout(graph, layout_options={
            "org.eclipse.elk.direction": "DOWN",
        })
        # Per-element option should win: direction is still RIGHT
        assert result["layoutOptions"]["elk.direction"] == "RIGHT"
        assert abs(result["children"][0]["x"] - result["children"][1]["x"]) > 0
        assert result["children"][0]["y"] == result["children"][1]["y"]

    def test_should_correctly_parse_elk_padding(self, elk):
        graph = {
            "id": "root",
            "layoutOptions": {"elk.padding": "[left=2, top=3, right=3, bottom=2]"},
            "children": [{"id": "n1", "width": 10, "height": 10}],
        }
        result = elk.layout(graph)
        assert result["children"][0]["x"] == 2
        assert result["children"][0]["y"] == 3
        assert result["width"] == 15   # 2 + 10 + 3
        assert result["height"] == 15  # 3 + 10 + 2

    def test_should_correctly_parse_kvector(self, elk):
        graph = {
            "id": "root",
            "children": [
                {
                    "id": "n1", "width": 10, "height": 10,
                    "layoutOptions": {"position": "(23, 43)"},
                },
            ],
        }
        result = elk.layout(graph, layout_options={"algorithm": "fixed"})
        assert result["children"][0]["x"] == 23
        assert result["children"][0]["y"] == 43

    def test_should_correctly_parse_kvector_chain(self, elk):
        graph = {
            "id": "root",
            "children": [
                {"id": "n1", "width": 10, "height": 10},
                {"id": "n2", "width": 10, "height": 10},
            ],
            "edges": [{
                "id": "e1",
                "sources": ["n1"],
                "targets": ["n2"],
                "layoutOptions": {"bendPoints": "( {1,2}, {3,4} )"},
            }],
        }
        result = elk.layout(graph, layout_options={"algorithm": "fixed"})
        section = result["edges"][0]["sections"][0]
        assert section["startPoint"]["x"] == 1
        assert section["startPoint"]["y"] == 2
        assert section["endPoint"]["x"] == 3
        assert section["endPoint"]["y"] == 4

    def test_should_raise_for_invalid_layouter_id(self, elk):
        graph = {
            "id": "root",
            "children": [{"id": "n1", "width": 10, "height": 10}],
            "layoutOptions": {"algorithm": "foo.bar.baz"},
        }
        with pytest.raises(ValueError, match="UnsupportedConfigurationException"):
            elk.layout(graph)

    def test_should_default_to_layered(self, elk):
        graph = {
            "id": "root",
            "children": [{"id": "n1", "width": 10, "height": 10}],
            "layoutOptions": {},
        }
        # Should not raise
        result = elk.layout(graph)
        assert result is not None


# ---------------------------------------------------------------------------
# Test: Global Layout Options (ported from testOptions.js)
# ---------------------------------------------------------------------------

class TestGlobalLayoutOptions:
    """Tests for global layout options from testOptions.js"""

    def test_should_respect_global_layout_options(self):
        elk = ELK(default_layout_options={
            "elk.layered.spacing.nodeNodeBetweenLayers": "33",
        })
        graph = {
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
        result = elk.layout(graph)
        # left-to-right: same y, spacing of 10+33 in x
        assert result["children"][0]["y"] == result["children"][1]["y"]
        assert abs(result["children"][0]["x"] - result["children"][1]["x"]) == 10 + 33


# ---------------------------------------------------------------------------
# Test: Logging (ported from testLogging.js)
# ---------------------------------------------------------------------------

class TestLogging:
    """Tests from testLogging.js"""

    def test_should_provide_logs_if_requested(self, elk):
        graph = {
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
        result = elk.layout(graph, layout_options={"algorithm": "stress"},
                            logging=True)
        assert "logging" in result
        assert "children" in result["logging"]
        # execution times should NOT be included
        assert "executionTime" not in result["logging"]

    def test_should_not_provide_logs_if_not_requested(self, elk):
        graph = {
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
        result = elk.layout(graph, logging=False)
        assert "logging" not in result

    def test_should_provide_execution_times_if_requested(self, elk):
        graph = {
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
        result = elk.layout(graph, layout_options={"algorithm": "layered"},
                            measure_execution_time=True)
        assert "logging" in result
        assert "executionTime" in result["logging"]

    def test_should_not_provide_execution_times_if_not_requested(self, elk):
        graph = {
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
        result = elk.layout(graph, measure_execution_time=False)
        assert "logging" not in result

    def test_should_not_provide_logging_by_default(self, elk):
        graph = {
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
        result = elk.layout(graph)
        assert "logging" not in result

    def test_should_clear_logging_from_previous_run(self, elk):
        graph = {
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
        # First run with logging
        result = elk.layout(graph, logging=True)
        assert "logging" in result

        # Second run without logging (same graph object, in-place)
        result = elk.layout(graph)
        assert "logging" not in result


# ---------------------------------------------------------------------------
# Test: Layout Algorithms (ported from testLayouters.js)
# ---------------------------------------------------------------------------

class TestLayoutAlgorithms:
    """Tests from testLayouters.js"""

    def test_rectangle_packing(self, elk):
        graph = {
            "id": "root",
            "children": [
                {"id": "n1", "x": 25, "y": 25, "width": 10, "height": 10},
                {"id": "n2", "x": 50, "y": 50, "width": 10, "height": 10},
            ],
            "edges": [
                {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
            ],
        }
        result = elk.layout(graph, layout_options={"algorithm": "elk.rectpacking"})
        assert result is not None
        # Check that positions were assigned
        assert result["children"][0]["x"] is not None
        assert result["children"][0]["y"] is not None


# ---------------------------------------------------------------------------
# Test: Entry Points
# ---------------------------------------------------------------------------

class TestEntryPoints:
    """Tests from testEntryPoints.js — ensure basic layout works."""

    def test_basic_layout_succeeds(self, elk):
        graph = {
            "id": "root",
            "children": [
                {"id": "n1", "width": 30, "height": 30},
                {"id": "n2", "width": 30, "height": 30},
                {"id": "n3", "width": 30, "height": 30},
            ],
            "edges": [
                {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
                {"id": "e2", "sources": ["n1"], "targets": ["n3"]},
            ],
        }
        result = elk.layout(graph)
        assert result is not None
        assert "children" in result
        assert len(result["children"]) == 3
        for child in result["children"]:
            assert child.get("x") is not None
            assert child.get("y") is not None


# ---------------------------------------------------------------------------
# Test: Known Algorithms/Options/Categories
# ---------------------------------------------------------------------------

class TestMetadata:
    """Test that metadata queries work."""

    def test_known_layout_algorithms(self, elk):
        algos = elk.known_layout_algorithms()
        assert len(algos) > 0
        algo_ids = [a["id"] for a in algos]
        assert "org.eclipse.elk.layered" in algo_ids

    def test_known_layout_options(self, elk):
        opts = elk.known_layout_options()
        assert len(opts) > 0
        opt_ids = [o["id"] for o in opts]
        assert "org.eclipse.elk.direction" in opt_ids

    def test_known_layout_categories(self, elk):
        cats = elk.known_layout_categories()
        assert len(cats) > 0
        cat_ids = [c["id"] for c in cats]
        assert "org.eclipse.elk.algorithm.category.layered" in cat_ids


# ---------------------------------------------------------------------------
# Test: Data Types
# ---------------------------------------------------------------------------

class TestDataTypes:
    """Test the dataclass types and conversion utilities."""

    def test_elk_node_creation(self):
        node = ElkNode(
            id="root",
            children=[
                ElkNode(id="n1", width=30, height=30),
                ElkNode(id="n2", width=30, height=30),
            ],
            edges=[
                ElkExtendedEdge(id="e1", sources=["n1"], targets=["n2"]),
            ],
        )
        assert node.id == "root"
        assert len(node.children) == 2
        assert len(node.edges) == 1

    def test_graph_to_dict(self):
        node = ElkNode(
            id="root",
            children=[
                ElkNode(id="n1", width=30, height=30),
            ],
        )
        d = graph_to_dict(node)
        assert d["id"] == "root"
        assert len(d["children"]) == 1
        assert d["children"][0]["width"] == 30

    def test_dict_to_graph(self):
        d = {
            "id": "root",
            "children": [
                {"id": "n1", "width": 30, "height": 30},
            ],
            "edges": [
                {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
            ],
        }
        node = dict_to_graph(d)
        assert isinstance(node, ElkNode)
        assert node.id == "root"
        assert len(node.children) == 1
        assert node.children[0].id == "n1"
        assert len(node.edges) == 1

    def test_elk_point(self):
        p = ElkPoint(x=10, y=20)
        assert p.x == 10
        assert p.y == 20

    def test_roundtrip_conversion(self):
        original = {
            "id": "root",
            "width": 100,
            "height": 50,
            "children": [
                {
                    "id": "n1", "width": 30, "height": 30,
                    "ports": [{"id": "p1", "width": 5, "height": 5}],
                    "labels": [{"id": "l1", "text": "Node 1"}],
                },
            ],
            "edges": [
                {
                    "id": "e1",
                    "sources": ["n1"],
                    "targets": ["n2"],
                    "sections": [{
                        "id": "s1",
                        "startPoint": {"x": 0, "y": 0},
                        "endPoint": {"x": 100, "y": 100},
                        "bendPoints": [{"x": 50, "y": 50}],
                    }],
                },
            ],
        }
        node = dict_to_graph(original)
        result = graph_to_dict(node)
        assert result["id"] == "root"
        assert result["children"][0]["ports"][0]["id"] == "p1"
        assert result["edges"][0]["sections"][0]["startPoint"]["x"] == 0


# ---------------------------------------------------------------------------
# Test: Multiple layout algorithms
# ---------------------------------------------------------------------------

class TestAllAlgorithms:
    """Test that all registered algorithms can run without errors."""

    @pytest.mark.parametrize("algorithm", [
        "layered", "stress", "force", "mrtree", "radial",
        "sporeOverlap", "sporeCompaction", "rectpacking", "fixed",
    ])
    def test_algorithm_runs(self, elk, algorithm):
        graph = {
            "id": "root",
            "children": [
                {"id": "n1", "width": 20, "height": 20},
                {"id": "n2", "width": 20, "height": 20},
                {"id": "n3", "width": 20, "height": 20},
            ],
            "edges": [
                {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
                {"id": "e2", "sources": ["n2"], "targets": ["n3"]},
            ],
        }
        result = elk.layout(graph, layout_options={"algorithm": algorithm})
        assert result is not None
        for child in result["children"]:
            assert child.get("x") is not None
            assert child.get("y") is not None


# ---------------------------------------------------------------------------
# Test: Edge routing
# ---------------------------------------------------------------------------

class TestEdgeRouting:
    """Test that edges get sections with start/end points after layout."""

    def test_edges_have_sections(self, elk):
        graph = {
            "id": "root",
            "children": [
                {"id": "n1", "width": 30, "height": 30},
                {"id": "n2", "width": 30, "height": 30},
            ],
            "edges": [
                {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
            ],
        }
        result = elk.layout(graph)
        edge = result["edges"][0]
        assert "sections" in edge
        assert len(edge["sections"]) > 0
        section = edge["sections"][0]
        assert "startPoint" in section
        assert "endPoint" in section
        assert "x" in section["startPoint"]
        assert "y" in section["startPoint"]
        assert "x" in section["endPoint"]
        assert "y" in section["endPoint"]


# ---------------------------------------------------------------------------
# Test: Graph with no edges
# ---------------------------------------------------------------------------

class TestNoEdges:
    """Test layout of graphs without edges."""

    def test_layout_without_edges(self, elk):
        graph = {
            "id": "root",
            "children": [
                {"id": "n1", "width": 30, "height": 30},
                {"id": "n2", "width": 30, "height": 30},
            ],
        }
        result = elk.layout(graph)
        assert result is not None
        for child in result["children"]:
            assert child.get("x") is not None

    def test_layout_empty_graph(self, elk):
        graph = {"id": "root"}
        result = elk.layout(graph)
        assert result is not None


# ---------------------------------------------------------------------------
# Test: Direction options
# ---------------------------------------------------------------------------

class TestDirection:
    """Test different layout directions."""

    def test_right_direction(self, elk):
        graph = {
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
        result = elk.layout(graph)
        # n1 should be to the left of n2
        assert result["children"][0]["x"] < result["children"][1]["x"]

    def test_down_direction(self, elk):
        graph = {
            "id": "root",
            "layoutOptions": {"elk.direction": "DOWN"},
            "children": [
                {"id": "n1", "width": 10, "height": 10},
                {"id": "n2", "width": 10, "height": 10},
            ],
            "edges": [
                {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
            ],
        }
        result = elk.layout(graph)
        # n1 should be above n2
        assert result["children"][0]["y"] < result["children"][1]["y"]
