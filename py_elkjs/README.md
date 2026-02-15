# elkjs — Pure Python Port

A **pure Python** port of [ELK.js](https://github.com/kieler/elkjs) (Eclipse Layout Kernel for JavaScript).

This is **not** a wrapper, bridge, or Node.js subprocess call. All layout algorithms are implemented natively in Python — no JavaScript runtime required.

## Installation

```bash
cd py_elkjs
pip install .
```

## Quick Start

```python
from elkjs import ELK

elk = ELK()

graph = {
    "id": "root",
    "layoutOptions": {"elk.direction": "RIGHT"},
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

for child in result["children"]:
    print(f"{child['id']}: x={child['x']}, y={child['y']}")
```

## API

### `ELK(default_layout_options=None, algorithms=None)`

Create a new ELK layout engine.

- `default_layout_options`: dict of default layout options applied to all layouts
- `algorithms`: list of algorithm names to register (default: all built-in algorithms)

### `elk.layout(graph, layout_options=None, logging=False, measure_execution_time=False)`

Compute layout for a graph. The graph is modified in-place and returned.

- `graph`: dict with `id`, optional `children`, `edges`, `ports`, `labels`, `layoutOptions`
- `layout_options`: dict of layout options (overrides defaults, overridden by per-element options)
- `logging`: if True, include logging info in result
- `measure_execution_time`: if True, include execution time measurement

### `elk.known_layout_algorithms()`

Returns list of available layout algorithm descriptions.

### `elk.known_layout_options()`

Returns list of available layout option descriptions.

### `elk.known_layout_categories()`

Returns list of available layout category descriptions.

## Supported Algorithms

| Algorithm | Key | Description |
|-----------|-----|-------------|
| Layered | `layered` / `elk.layered` | Sugiyama-style layer-based layout |
| Stress | `stress` / `elk.stress` | Stress-minimizing force-directed layout |
| Force | `force` / `elk.force` | Fruchterman-Reingold force-directed layout |
| MrTree | `mrtree` / `elk.mrtree` | Tree layout algorithm |
| Radial | `radial` / `elk.radial` | Radial tree layout |
| SPOrE Overlap | `sporeOverlap` / `elk.sporeOverlap` | Overlap removal |
| SPOrE Compaction | `sporeCompaction` / `elk.sporeCompaction` | Graph compaction |
| Rectangle Packing | `rectpacking` / `elk.rectpacking` | Rectangle packing |
| Fixed | `fixed` / `elk.fixed` | Preserves given positions |

## Layout Options

| Option | Type | Description |
|--------|------|-------------|
| `elk.direction` | enum | Edge direction: `RIGHT`, `LEFT`, `DOWN`, `UP` |
| `elk.spacing.nodeNode` | float | Spacing between nodes within a layer |
| `elk.layered.spacing.nodeNodeBetweenLayers` | float | Spacing between layers |
| `elk.padding` | string | Graph padding: `[left=12, top=12, right=12, bottom=12]` |
| `algorithm` | string | Layout algorithm to use |

## Data Types

The package provides dataclass types for type-safe graph construction:

```python
from elkjs import ElkNode, ElkPort, ElkExtendedEdge, ElkLabel, ElkPoint

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
```

Use `elkjs.elk_types.graph_to_dict()` and `elkjs.elk_types.dict_to_graph()` to convert between dataclasses and dicts.

## Differences from JavaScript ELK.js

- **Synchronous API**: No Promises/workers — `layout()` returns immediately
- **Pure Python**: No JavaScript, no subprocess, no bridge
- **Simplified algorithms**: The layout algorithms are native Python implementations inspired by the original ELK algorithms. Results may differ slightly from the Java/JS version.
- **No GWT dependency**: The original ELK.js compiles Java to JavaScript via GWT. This port implements algorithms directly in Python.

## License

[Eclipse Public License 2.0](../LICENSE.md)
