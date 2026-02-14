"""
Type definitions for ELK graph elements.

This is a pure Python port of the TypeScript type definitions
from elkjs (typings/elk-api.d.ts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# LayoutOptions is simply a dict of string -> string
LayoutOptions = Dict[str, str]


@dataclass
class ElkPoint:
    """A point with x and y coordinates."""

    x: float = 0.0
    y: float = 0.0


@dataclass
class ElkLabel:
    """A label attached to a graph element."""

    id: Optional[str] = None
    text: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    layoutOptions: Optional[LayoutOptions] = None
    labels: Optional[List["ElkLabel"]] = None


@dataclass
class ElkPort:
    """A port on a node."""

    id: str = ""
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    labels: Optional[List[ElkLabel]] = None
    layoutOptions: Optional[LayoutOptions] = None


@dataclass
class ElkEdgeSection:
    """A section of an edge with start/end points and optional bend points."""

    id: str = ""
    startPoint: Optional[ElkPoint] = None
    endPoint: Optional[ElkPoint] = None
    bendPoints: Optional[List[ElkPoint]] = None
    incomingShape: Optional[str] = None
    outgoingShape: Optional[str] = None
    incomingSections: Optional[List[str]] = None
    outgoingSections: Optional[List[str]] = None
    layoutOptions: Optional[LayoutOptions] = None
    labels: Optional[List[ElkLabel]] = None


@dataclass
class ElkExtendedEdge:
    """An edge using the extended edge format with sources/targets lists."""

    id: str = ""
    sources: Optional[List[str]] = None
    targets: Optional[List[str]] = None
    sections: Optional[List[ElkEdgeSection]] = None
    labels: Optional[List[ElkLabel]] = None
    layoutOptions: Optional[LayoutOptions] = None
    container: Optional[str] = None
    junctionPoints: Optional[List[ElkPoint]] = None


@dataclass
class ElkPrimitiveEdge:
    """An edge using the primitive (deprecated) edge format."""

    id: str = ""
    source: str = ""
    sourcePort: Optional[str] = None
    target: str = ""
    targetPort: Optional[str] = None
    sourcePoint: Optional[ElkPoint] = None
    targetPoint: Optional[ElkPoint] = None
    bendPoints: Optional[List[ElkPoint]] = None
    labels: Optional[List[ElkLabel]] = None
    layoutOptions: Optional[LayoutOptions] = None
    container: Optional[str] = None
    junctionPoints: Optional[List[ElkPoint]] = None


@dataclass
class ElkNode:
    """A node in the ELK graph. Can contain children, ports, and edges."""

    id: str = ""
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    children: Optional[List["ElkNode"]] = None
    ports: Optional[List[ElkPort]] = None
    edges: Optional[List[ElkExtendedEdge]] = None
    labels: Optional[List[ElkLabel]] = None
    layoutOptions: Optional[LayoutOptions] = None


def graph_to_dict(obj: Any) -> Any:
    """Convert an ELK dataclass graph to a plain dictionary.

    Recursively converts dataclass instances, filtering out None values.
    """
    if isinstance(obj, (ElkPoint, ElkLabel, ElkPort, ElkEdgeSection,
                        ElkExtendedEdge, ElkPrimitiveEdge, ElkNode)):
        result = {}
        for k, v in obj.__dict__.items():
            converted = graph_to_dict(v)
            if converted is not None:
                result[k] = converted
        return result
    elif isinstance(obj, list):
        return [graph_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: graph_to_dict(v) for k, v in obj.items() if v is not None}
    else:
        return obj


def dict_to_graph(data: dict) -> ElkNode:
    """Convert a plain dictionary to an ElkNode graph.

    Recursively constructs dataclass instances from dict data.
    """
    return _dict_to_node(data)


def _dict_to_node(d: dict) -> ElkNode:
    children = None
    if "children" in d and d["children"] is not None:
        children = [_dict_to_node(c) for c in d["children"]]

    ports = None
    if "ports" in d and d["ports"] is not None:
        ports = [_dict_to_port(p) for p in d["ports"]]

    edges = None
    if "edges" in d and d["edges"] is not None:
        edges = [_dict_to_edge(e) for e in d["edges"]]

    labels = None
    if "labels" in d and d["labels"] is not None:
        labels = [_dict_to_label(lb) for lb in d["labels"]]

    return ElkNode(
        id=d.get("id", ""),
        x=d.get("x"),
        y=d.get("y"),
        width=d.get("width"),
        height=d.get("height"),
        children=children,
        ports=ports,
        edges=edges,
        labels=labels,
        layoutOptions=d.get("layoutOptions"),
    )


def _dict_to_port(d: dict) -> ElkPort:
    labels = None
    if "labels" in d and d["labels"] is not None:
        labels = [_dict_to_label(lb) for lb in d["labels"]]

    return ElkPort(
        id=d.get("id", ""),
        x=d.get("x"),
        y=d.get("y"),
        width=d.get("width"),
        height=d.get("height"),
        labels=labels,
        layoutOptions=d.get("layoutOptions"),
    )


def _dict_to_edge(d: dict) -> ElkExtendedEdge:
    sections = None
    if "sections" in d and d["sections"] is not None:
        sections = [_dict_to_section(s) for s in d["sections"]]

    labels = None
    if "labels" in d and d["labels"] is not None:
        labels = [_dict_to_label(lb) for lb in d["labels"]]

    junction_points = None
    if "junctionPoints" in d and d["junctionPoints"] is not None:
        junction_points = [ElkPoint(x=p["x"], y=p["y"])
                           for p in d["junctionPoints"]]

    return ElkExtendedEdge(
        id=d.get("id", ""),
        sources=d.get("sources"),
        targets=d.get("targets"),
        sections=sections,
        labels=labels,
        layoutOptions=d.get("layoutOptions"),
        container=d.get("container"),
        junctionPoints=junction_points,
    )


def _dict_to_section(d: dict) -> ElkEdgeSection:
    start = None
    if "startPoint" in d and d["startPoint"] is not None:
        start = ElkPoint(x=d["startPoint"]["x"], y=d["startPoint"]["y"])

    end = None
    if "endPoint" in d and d["endPoint"] is not None:
        end = ElkPoint(x=d["endPoint"]["x"], y=d["endPoint"]["y"])

    bends = None
    if "bendPoints" in d and d["bendPoints"] is not None:
        bends = [ElkPoint(x=p["x"], y=p["y"]) for p in d["bendPoints"]]

    return ElkEdgeSection(
        id=d.get("id", ""),
        startPoint=start,
        endPoint=end,
        bendPoints=bends,
        incomingShape=d.get("incomingShape"),
        outgoingShape=d.get("outgoingShape"),
        incomingSections=d.get("incomingSections"),
        outgoingSections=d.get("outgoingSections"),
        layoutOptions=d.get("layoutOptions"),
    )


def _dict_to_label(d: dict) -> ElkLabel:
    return ElkLabel(
        id=d.get("id"),
        text=d.get("text"),
        x=d.get("x"),
        y=d.get("y"),
        width=d.get("width"),
        height=d.get("height"),
        layoutOptions=d.get("layoutOptions"),
    )
