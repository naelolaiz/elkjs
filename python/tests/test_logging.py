"""Tests for logging – mirrors test/mocha/testLogging.js."""

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


def test_logs_if_requested(elk):
    """Should provide logs if requested to."""
    graph = copy.deepcopy(SIMPLE_GRAPH)
    result = elk.layout(
        graph,
        layout_options={"algorithm": "stress"},
        logging=True,
    )
    assert "logging" in result
    assert result["logging"] is not None
    assert "children" in result["logging"]
    assert "executionTime" not in result["logging"]


def test_no_logs_if_not_requested(elk):
    """Should not provide logs if not requested to."""
    graph = copy.deepcopy(SIMPLE_GRAPH)
    result = elk.layout(graph, logging=False)
    assert "logging" not in result


def test_execution_time_if_requested(elk):
    """Should provide execution times if requested to."""
    graph = copy.deepcopy(SIMPLE_GRAPH)
    result = elk.layout(
        graph,
        layout_options={"algorithm": "layered"},
        measure_execution_time=True,
    )
    assert "logging" in result
    assert result["logging"] is not None
    assert "executionTime" in result["logging"]


def test_no_execution_time_if_not_requested(elk):
    """Should not provide execution times if not requested to."""
    graph = copy.deepcopy(SIMPLE_GRAPH)
    result = elk.layout(graph, measure_execution_time=False)
    assert "logging" not in result


def test_no_logging_by_default(elk):
    """Should not provide logging information by default."""
    graph = copy.deepcopy(SIMPLE_GRAPH)
    result = elk.layout(graph)
    assert "logging" not in result


def test_clear_logging_from_previous_run(elk):
    """Should clear logging information from previous layout run."""
    graph = copy.deepcopy(SIMPLE_GRAPH)

    # First run with logging
    elk.layout(graph, logging=True)
    assert "logging" in graph

    # Second run without logging — logging should be cleared
    elk.layout(graph)
    assert "logging" not in graph
