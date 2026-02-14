"""Type definitions for ELK graph structures.

These mirror the TypeScript interfaces defined in elk-api.d.ts.
They are provided for documentation and optional type checking with mypy.
"""

from typing import Any, Dict, List, Optional, TypedDict, Union


class LayoutOptions(TypedDict, total=False):
    """Layout options as key-value string pairs."""
    pass  # Any string key to string value


class ElkPoint(TypedDict):
    """A 2D point."""
    x: float
    y: float


class ElkLabel(TypedDict, total=False):
    """A label for a graph element."""
    id: str
    text: str
    x: float
    y: float
    width: float
    height: float
    labels: List["ElkLabel"]
    layoutOptions: Dict[str, str]


class ElkPort(TypedDict, total=False):
    """A port on a node."""
    id: str  # required
    x: float
    y: float
    width: float
    height: float
    labels: List[ElkLabel]
    layoutOptions: Dict[str, str]


class ElkEdgeSection(TypedDict, total=False):
    """A section of an edge route."""
    id: str  # required
    startPoint: ElkPoint
    endPoint: ElkPoint
    bendPoints: List[ElkPoint]
    incomingShape: str
    outgoingShape: str
    incomingSections: List[str]
    outgoingSections: List[str]


class ElkExtendedEdge(TypedDict, total=False):
    """An edge connecting nodes via source/target lists."""
    id: str  # required
    sources: List[str]
    targets: List[str]
    sections: List[ElkEdgeSection]
    labels: List[ElkLabel]
    layoutOptions: Dict[str, str]
    container: str
    junctionPoints: List[ElkPoint]


class ElkPrimitiveEdge(TypedDict, total=False):
    """A simple edge with single source and target (deprecated format)."""
    id: str  # required
    source: str
    sourcePort: str
    target: str
    targetPort: str
    sourcePoint: ElkPoint
    targetPoint: ElkPoint
    bendPoints: List[ElkPoint]
    labels: List[ElkLabel]
    layoutOptions: Dict[str, str]
    container: str
    junctionPoints: List[ElkPoint]


class ElkNode(TypedDict, total=False):
    """A node in the ELK graph."""
    id: str  # required
    x: float
    y: float
    width: float
    height: float
    children: List["ElkNode"]
    ports: List[ElkPort]
    edges: List[Union[ElkExtendedEdge, ElkPrimitiveEdge]]
    labels: List[ElkLabel]
    layoutOptions: Dict[str, str]
    properties: Dict[str, str]


class ElkLayoutArguments(TypedDict, total=False):
    """Arguments for the layout method."""
    layoutOptions: Dict[str, str]
    logging: bool
    measureExecutionTime: bool


class ElkCommonDescription(TypedDict, total=False):
    """Common fields for descriptions."""
    id: str
    name: str
    description: str


class ElkLayoutAlgorithmDescription(ElkCommonDescription, total=False):
    """Description of a layout algorithm."""
    category: str
    knownOptions: List[str]
    supportedFeatures: List[str]


class ElkLayoutOptionDescription(ElkCommonDescription, total=False):
    """Description of a layout option."""
    group: str
    type: str
    targets: List[str]


class ElkLayoutCategoryDescription(ElkCommonDescription, total=False):
    """Description of a layout category."""
    knownLayouters: List[str]
