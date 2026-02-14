"""
Pure Python port of ELK.js API.

This module provides the ELK class — the main entry point for performing
automatic graph layout. It mirrors the API of the JavaScript ELK class
from elk-api.js, but runs entirely in pure Python with no JavaScript,
no subprocess, and no bridge.

Usage::

    from elkjs import ELK

    elk = ELK()
    graph = {
        "id": "root",
        "children": [
            {"id": "n1", "width": 30, "height": 30},
            {"id": "n2", "width": 30, "height": 30},
        ],
        "edges": [
            {"id": "e1", "sources": ["n1"], "targets": ["n2"]}
        ],
    }
    result = elk.layout(graph)
    # result is the same dict, now with x/y positions computed
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from . import elk_layout_engine


class ELK:
    """Pure Python ELK layout engine.

    This class mirrors the API of the JavaScript ELK class from elk-api.js
    but operates synchronously and entirely in Python.

    Args:
        default_layout_options: Default layout options applied to all graphs
            unless overridden.
        algorithms: List of algorithm names to register. By default all
            built-in algorithms are registered.
    """

    def __init__(
        self,
        default_layout_options: Optional[Dict[str, str]] = None,
        algorithms: Optional[List[str]] = None,
    ):
        if default_layout_options is None:
            default_layout_options = {}
        if algorithms is None:
            algorithms = [
                "layered",
                "stress",
                "mrtree",
                "radial",
                "force",
                "sporeOverlap",
                "sporeCompaction",
                "rectpacking",
            ]

        self.default_layout_options = default_layout_options
        self.algorithms = algorithms

    def layout(
        self,
        graph: dict,
        layout_options: Optional[Dict[str, str]] = None,
        logging: bool = False,
        measure_execution_time: bool = False,
    ) -> dict:
        """Compute layout for the given graph.

        The graph is modified in-place and also returned.

        Args:
            graph: An ELK graph as a plain Python dict. Must have an 'id' field.
            layout_options: Layout options that override default options.
                Per-element options on the graph itself take highest priority.
            logging: Whether to include logging information in the result.
            measure_execution_time: Whether to measure and include execution time.

        Returns:
            The same graph dict with computed positions (x, y) for all elements.

        Raises:
            ValueError: If the graph is missing or invalid.
        """
        if graph is None:
            raise ValueError("Missing mandatory parameter 'graph'.")

        # Merge with default options
        merged_options = dict(self.default_layout_options)
        if layout_options:
            merged_options.update(layout_options)

        options = {
            "logging": logging,
            "measureExecutionTime": measure_execution_time,
        }

        return elk_layout_engine.layout(graph, merged_options, options)

    def known_layout_algorithms(self) -> List[Dict[str, Any]]:
        """Return descriptions of known layout algorithms.

        Returns:
            List of algorithm description dicts with id, name, description, etc.
        """
        return list(elk_layout_engine.ALGORITHM_DESCRIPTIONS)

    def known_layout_options(self) -> List[Dict[str, Any]]:
        """Return descriptions of known layout options.

        Returns:
            List of option description dicts with id, name, type, targets, etc.
        """
        return list(elk_layout_engine.OPTION_DESCRIPTIONS)

    def known_layout_categories(self) -> List[Dict[str, Any]]:
        """Return descriptions of known layout categories.

        Returns:
            List of category description dicts with id, name, knownLayouters, etc.
        """
        return list(elk_layout_engine.CATEGORY_DESCRIPTIONS)
