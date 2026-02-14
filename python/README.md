# elkjs – Python Port

A Python port of [elkjs](https://github.com/kieler/elkjs) providing automatic graph
layout based on the [Eclipse Layout Kernel (ELK)](https://www.eclipse.org/elk/).
Specialized for data flow diagrams and ports.

This package provides a **100% equivalent** API to the JavaScript version
by communicating with the ELK layout engine via a Node.js subprocess bridge.

## Requirements

- **Python 3.8+**
- **Node.js** (any recent LTS version)
- The `elkjs` npm package (the compiled JavaScript worker files)

## Installation

From the repository root:

```bash
# Install the npm package (provides the layout engine)
npm install

# Install the Python package in development mode
cd python
pip install -e ".[test]"
```

## Usage

```python
from elkjs import ELK

elk = ELK()

graph = {
    "id": "root",
    "layoutOptions": {"elk.algorithm": "layered"},
    "children": [
        {"id": "n1", "width": 30, "height": 30},
        {"id": "n2", "width": 30, "height": 30},
    ],
    "edges": [
        {"id": "e1", "sources": ["n1"], "targets": ["n2"]},
    ],
}

result = elk.layout(graph)
print(result)
# The graph dict is modified in-place and also returned.
```

### Constructor Options

| Parameter                | Type           | Default                  | Description                                      |
|--------------------------|----------------|--------------------------|--------------------------------------------------|
| `default_layout_options` | `dict`         | `{}`                     | Default options applied to every `layout()` call |
| `algorithms`             | `list[str]`    | All built-in algorithms  | Algorithms to register                           |
| `worker_path`            | `str` or `None`| Auto-detected            | Path to `elk-worker.min.js`                      |
| `node_path`              | `str` or `None`| Auto-detected from PATH  | Path to the `node` executable                    |

### Methods

| Method                       | Description                                   |
|------------------------------|-----------------------------------------------|
| `layout(graph, ...)`        | Compute layout for the graph (in-place)       |
| `known_layout_algorithms()` | List known layout algorithms                  |
| `known_layout_options()`    | List known layout options                     |
| `known_layout_categories()` | List known layout categories                  |
| `terminate_worker()`        | Terminate the Node.js worker process          |

### Context Manager

```python
with ELK() as elk:
    result = elk.layout(graph)
# Worker is automatically terminated
```

## Running Tests

```bash
cd python
pip install -e ".[test]"
pytest
```

## API Equivalence

This Python port mirrors the JavaScript API:

| JavaScript                  | Python                        |
|-----------------------------|-------------------------------|
| `new ELK(options)`          | `ELK(**options)`              |
| `elk.layout(graph, args)`  | `elk.layout(graph, **args)`  |
| `elk.knownLayoutAlgorithms()` | `elk.known_layout_algorithms()` |
| `elk.knownLayoutOptions()`    | `elk.known_layout_options()`    |
| `elk.knownLayoutCategories()` | `elk.known_layout_categories()` |
| `elk.terminateWorker()`       | `elk.terminate_worker()`        |

## License

EPL-2.0
