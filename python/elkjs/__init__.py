"""elkjs – Eclipse Layout Kernel for Python.

A Python wrapper for elkjs providing automatic graph layout.
The layout computation is performed by the ELK JavaScript engine
via a Node.js subprocess bridge.

Usage::

    from elkjs import ELK

    elk = ELK()
    result = elk.layout({"id": "root", "children": [...]})
"""

from .elk import DEFAULT_ALGORITHMS, ELK
from .typedefs import (
    ElkExtendedEdge,
    ElkLabel,
    ElkLayoutAlgorithmDescription,
    ElkLayoutCategoryDescription,
    ElkLayoutOptionDescription,
    ElkNode,
    ElkPoint,
    ElkPort,
    ElkPrimitiveEdge,
)

__all__ = [
    "ELK",
    "DEFAULT_ALGORITHMS",
    "ElkExtendedEdge",
    "ElkLabel",
    "ElkLayoutAlgorithmDescription",
    "ElkLayoutCategoryDescription",
    "ElkLayoutOptionDescription",
    "ElkNode",
    "ElkPoint",
    "ElkPort",
    "ElkPrimitiveEdge",
]
