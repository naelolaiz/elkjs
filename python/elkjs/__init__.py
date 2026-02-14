"""elkjs – Eclipse Layout Kernel for Python.

A Python port of elkjs providing automatic graph layout.

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
