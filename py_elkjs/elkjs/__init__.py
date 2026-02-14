"""
elkjs - Pure Python port of ELK.js (Eclipse Layout Kernel for JavaScript).

Automatic graph layout based on Sugiyama's algorithm,
specialized for data flow diagrams and ports.
"""

from .elk_types import (
    ElkPoint,
    ElkLabel,
    ElkPort,
    ElkNode,
    ElkExtendedEdge,
    ElkPrimitiveEdge,
    ElkEdgeSection,
    LayoutOptions,
)
from .elk import ELK

__version__ = "0.11.0"
__all__ = [
    "ELK",
    "ElkPoint",
    "ElkLabel",
    "ElkPort",
    "ElkNode",
    "ElkExtendedEdge",
    "ElkPrimitiveEdge",
    "ElkEdgeSection",
    "LayoutOptions",
]
