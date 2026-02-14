"""
Pure Python layout engine for ELK graphs.

Implements layout algorithms natively in Python, including:
- layered (Sugiyama-style layer-based layout)
- fixed (preserves given positions)

This is a pure Python port — no JavaScript, no subprocess, no bridge.
"""

from __future__ import annotations

import copy
import math
import re
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Default spacing constants (mirroring ELK defaults)
# ---------------------------------------------------------------------------
DEFAULT_NODE_NODE_SPACING = 20.0
DEFAULT_NODE_NODE_BETWEEN_LAYERS = 20.0
DEFAULT_EDGE_NODE_SPACING = 10.0
DEFAULT_BORDER_SPACING = 12.0
DEFAULT_PADDING_TOP = 12.0
DEFAULT_PADDING_BOTTOM = 12.0
DEFAULT_PADDING_LEFT = 12.0
DEFAULT_PADDING_RIGHT = 12.0
DEFAULT_NODE_WIDTH = 10.0
DEFAULT_NODE_HEIGHT = 10.0
DEFAULT_PORT_WIDTH = 0.0
DEFAULT_PORT_HEIGHT = 0.0


# ---------------------------------------------------------------------------
# Padding parser
# ---------------------------------------------------------------------------
def _parse_padding(padding_str: str) -> Dict[str, float]:
    """Parse ELK-style padding string: '[left=2, top=3, right=3, bottom=2]'."""
    result = {
        "left": DEFAULT_PADDING_LEFT,
        "top": DEFAULT_PADDING_TOP,
        "right": DEFAULT_PADDING_RIGHT,
        "bottom": DEFAULT_PADDING_BOTTOM,
    }
    if not padding_str:
        return result
    for match in re.finditer(r"(left|top|right|bottom)\s*=\s*([0-9.]+)", padding_str):
        result[match.group(1)] = float(match.group(2))
    return result


def _parse_kvector(s: str) -> Optional[Tuple[float, float]]:
    """Parse ELK KVector string: '(23, 43)'."""
    m = re.match(r"\(\s*([0-9.e+-]+)\s*,\s*([0-9.e+-]+)\s*\)", s.strip())
    if m:
        return float(m.group(1)), float(m.group(2))
    return None


def _parse_kvector_chain(s: str) -> Optional[List[Tuple[float, float]]]:
    """Parse ELK KVectorChain string: '( {1,2}, {3,4} )'."""
    points = []
    for m in re.finditer(r"\{\s*([0-9.e+-]+)\s*,\s*([0-9.e+-]+)\s*\}", s):
        points.append((float(m.group(1)), float(m.group(2))))
    return points if points else None


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def _get_option(graph: dict, key: str, layout_options: dict,
                default: Any = None) -> Any:
    """Resolve a layout option from the graph's own options or global options."""
    # Check graph-level options first
    opts = graph.get("layoutOptions") or {}
    # Try full key
    if key in opts:
        return opts[key]
    # Try short key (strip common prefixes)
    for prefix in ("org.eclipse.elk.", "elk.", ""):
        short = key
        if prefix and key.startswith(prefix):
            short = key[len(prefix):]
        if short in opts:
            return opts[short]

    # Then check global layout options
    if key in layout_options:
        return layout_options[key]
    for prefix in ("org.eclipse.elk.", "elk.", ""):
        short = key
        if prefix and key.startswith(prefix):
            short = key[len(prefix):]
        if short in layout_options:
            return layout_options[short]

    return default


def _resolve_algorithm(graph: dict, layout_options: dict) -> str:
    """Determine the layout algorithm to use."""
    algo = _get_option(graph, "algorithm", layout_options, "layered")
    if algo is None:
        return "layered"
    algo = str(algo)
    # Normalize algorithm names
    algo = algo.replace("org.eclipse.elk.", "elk.")
    if algo.startswith("elk."):
        algo = algo[4:]
    return algo


def _get_node_size(node: dict) -> Tuple[float, float]:
    """Get node width and height with defaults."""
    w = node.get("width")
    h = node.get("height")
    if w is None:
        w = DEFAULT_NODE_WIDTH
    if h is None:
        h = DEFAULT_NODE_HEIGHT
    return float(w), float(h)


def _build_node_map(graph: dict) -> Dict[str, dict]:
    """Build a map from node id to node dict for quick lookup."""
    node_map: Dict[str, dict] = {}
    for child in graph.get("children") or []:
        nid = child.get("id")
        if nid is not None:
            node_map[str(nid)] = child
    return node_map


# ---------------------------------------------------------------------------
# Layered layout algorithm (Sugiyama-style)
# ---------------------------------------------------------------------------

def _layered_layout(graph: dict, layout_options: dict,
                    options: dict) -> dict:
    """Perform a layered (Sugiyama) layout on the graph.

    Steps:
    1. Build adjacency from edges
    2. Remove cycles (reverse some edges)
    3. Assign layers (longest path layering)
    4. Assign positions within layers (barycenter ordering)
    5. Assign coordinates
    6. Route edges
    """
    children = graph.get("children") or []
    edges = graph.get("edges") or []

    if not children:
        _apply_padding(graph, layout_options)
        return graph

    # Determine direction
    direction = _get_option(graph, "elk.direction", layout_options, "RIGHT")
    if direction is None:
        direction = "RIGHT"
    direction = direction.upper()
    horizontal = direction in ("RIGHT", "LEFT")
    reversed_dir = direction in ("LEFT", "UP")

    # Get spacing options
    nn_spacing = float(_get_option(
        graph, "elk.spacing.nodeNode", layout_options, DEFAULT_NODE_NODE_SPACING))
    nn_between_layers = float(_get_option(
        graph,
        "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers",
        layout_options,
        _get_option(graph, "elk.layered.spacing.nodeNodeBetweenLayers",
                    layout_options, DEFAULT_NODE_NODE_BETWEEN_LAYERS)))

    # Parse padding
    padding_str = _get_option(graph, "elk.padding", layout_options, "")
    padding = _parse_padding(padding_str if padding_str else "")

    # Build node map
    node_map = _build_node_map(graph)
    node_ids = [str(c.get("id")) for c in children if c.get("id") is not None]

    if not node_ids:
        _apply_padding(graph, layout_options)
        return graph

    # Build adjacency lists
    adj: Dict[str, List[str]] = defaultdict(list)
    rev_adj: Dict[str, List[str]] = defaultdict(list)
    for edge in edges:
        sources = edge.get("sources") or []
        targets = edge.get("targets") or []
        for src in sources:
            for tgt in targets:
                s, t = str(src), str(tgt)
                if s in node_map and t in node_map:
                    adj[s].append(t)
                    rev_adj[t].append(s)

    # Layer assignment using longest-path algorithm
    layers = _assign_layers(node_ids, adj, rev_adj)

    if reversed_dir:
        max_layer = max(layers.values()) if layers else 0
        layers = {nid: max_layer - layer for nid, layer in layers.items()}

    # Group nodes by layer
    num_layers = (max(layers.values()) + 1) if layers else 1
    layer_groups: List[List[str]] = [[] for _ in range(num_layers)]
    for nid in node_ids:
        layer_groups[layers.get(nid, 0)].append(nid)

    # Order nodes within layers using barycenter heuristic
    _order_layers(layer_groups, adj, rev_adj, node_map)

    # Assign coordinates
    if horizontal:
        _assign_horizontal_coords(
            layer_groups, node_map, nn_spacing, nn_between_layers, padding)
    else:
        _assign_vertical_coords(
            layer_groups, node_map, nn_spacing, nn_between_layers, padding)

    # Route edges (create sections with start/end points)
    _route_edges(edges, node_map, horizontal)

    # Compute total graph size
    _compute_graph_size(graph, children, padding)

    # Handle child graphs recursively
    for child in children:
        if child.get("children"):
            child_algo = _resolve_algorithm(child, layout_options)
            _dispatch_layout(child, layout_options, options)

    return graph


def _assign_layers(node_ids: List[str],
                   adj: Dict[str, List[str]],
                   rev_adj: Dict[str, List[str]]) -> Dict[str, int]:
    """Assign layers using longest-path-from-sinks algorithm."""
    layers: Dict[str, int] = {}
    visited: Set[str] = set()

    # Find sinks (nodes with no outgoing edges to other nodes in graph)
    sinks = [nid for nid in node_ids if not adj.get(nid)]

    if not sinks:
        # All nodes have outgoing edges (cycle); pick arbitrary start
        sinks = [node_ids[0]]

    def dfs(node: str) -> int:
        if node in layers:
            return layers[node]
        if node in visited:
            return 0  # cycle detected
        visited.add(node)
        max_pred_layer = -1
        for pred in rev_adj.get(node, []):
            if pred in set(node_ids):
                pred_layer = dfs(pred)
                max_pred_layer = max(max_pred_layer, pred_layer)
        layers[node] = max_pred_layer + 1
        return layers[node]

    # Process from sources (nodes with no predecessors)
    sources = [nid for nid in node_ids if not rev_adj.get(nid)]
    if not sources:
        sources = node_ids[:]

    # BFS-based topological layering
    in_degree: Dict[str, int] = defaultdict(int)
    node_set = set(node_ids)
    for nid in node_ids:
        for tgt in adj.get(nid, []):
            if tgt in node_set:
                in_degree[tgt] += 1

    queue = deque()
    for nid in node_ids:
        if in_degree[nid] == 0:
            queue.append(nid)
            layers[nid] = 0

    while queue:
        node = queue.popleft()
        for tgt in adj.get(node, []):
            if tgt in node_set:
                candidate_layer = layers[node] + 1
                if tgt not in layers or candidate_layer > layers[tgt]:
                    layers[tgt] = candidate_layer
                in_degree[tgt] -= 1
                if in_degree[tgt] <= 0:
                    queue.append(tgt)

    # Handle any remaining unassigned nodes (cycles)
    for nid in node_ids:
        if nid not in layers:
            layers[nid] = 0

    return layers


def _order_layers(layer_groups: List[List[str]],
                  adj: Dict[str, List[str]],
                  rev_adj: Dict[str, List[str]],
                  node_map: Dict[str, dict]) -> None:
    """Order nodes within layers using barycenter heuristic."""
    # Build position map for current ordering
    for sweep in range(4):  # Multiple sweeps for better results
        # Forward sweep
        for i in range(1, len(layer_groups)):
            _order_layer_by_barycenter(
                layer_groups[i], layer_groups[i - 1], rev_adj, True)
        # Backward sweep
        for i in range(len(layer_groups) - 2, -1, -1):
            _order_layer_by_barycenter(
                layer_groups[i], layer_groups[i + 1], adj, False)


def _order_layer_by_barycenter(layer: List[str],
                               ref_layer: List[str],
                               connections: Dict[str, List[str]],
                               use_predecessors: bool) -> None:
    """Order a layer's nodes based on barycenter of connected nodes in reference layer."""
    ref_positions = {nid: i for i, nid in enumerate(ref_layer)}

    barycenters: Dict[str, float] = {}
    for nid in layer:
        connected = connections.get(nid, [])
        positions = [ref_positions[c] for c in connected if c in ref_positions]
        if positions:
            barycenters[nid] = sum(positions) / len(positions)
        else:
            barycenters[nid] = float('inf')

    # Sort by barycenter, preserving relative order for ties
    layer.sort(key=lambda nid: barycenters.get(nid, float('inf')))


def _assign_horizontal_coords(layer_groups: List[List[str]],
                               node_map: Dict[str, dict],
                               nn_spacing: float,
                               nn_between_layers: float,
                               padding: Dict[str, float]) -> None:
    """Assign x,y coordinates for horizontal (LEFT/RIGHT) layouts."""
    x_offset = padding["left"]

    for layer_idx, layer in enumerate(layer_groups):
        y_offset = padding["top"]
        max_width = 0.0

        for nid in layer:
            node = node_map[nid]
            w, h = _get_node_size(node)
            node["x"] = x_offset
            node["y"] = y_offset
            y_offset += h + nn_spacing
            max_width = max(max_width, w)

        x_offset += max_width + nn_between_layers


def _assign_vertical_coords(layer_groups: List[List[str]],
                              node_map: Dict[str, dict],
                              nn_spacing: float,
                              nn_between_layers: float,
                              padding: Dict[str, float]) -> None:
    """Assign x,y coordinates for vertical (UP/DOWN) layouts."""
    y_offset = padding["top"]

    for layer_idx, layer in enumerate(layer_groups):
        x_offset = padding["left"]
        max_height = 0.0

        for nid in layer:
            node = node_map[nid]
            w, h = _get_node_size(node)
            node["x"] = x_offset
            node["y"] = y_offset
            x_offset += w + nn_spacing
            max_height = max(max_height, h)

        y_offset += max_height + nn_between_layers


def _route_edges(edges: List[dict], node_map: Dict[str, dict],
                 horizontal: bool) -> None:
    """Create edge sections with start/end points."""
    for edge in edges:
        sources = edge.get("sources") or []
        targets = edge.get("targets") or []
        if not sources or not targets:
            continue

        src_id = str(sources[0])
        tgt_id = str(targets[0])

        src_node = node_map.get(src_id)
        tgt_node = node_map.get(tgt_id)
        if not src_node or not tgt_node:
            continue

        sw, sh = _get_node_size(src_node)
        tw, th = _get_node_size(tgt_node)

        src_x = float(src_node.get("x", 0))
        src_y = float(src_node.get("y", 0))
        tgt_x = float(tgt_node.get("x", 0))
        tgt_y = float(tgt_node.get("y", 0))

        if horizontal:
            start_point = {"x": src_x + sw, "y": src_y + sh / 2}
            end_point = {"x": tgt_x, "y": tgt_y + th / 2}
        else:
            start_point = {"x": src_x + sw / 2, "y": src_y + sh}
            end_point = {"x": tgt_x + tw / 2, "y": tgt_y}

        section = {
            "id": f"{edge.get('id', '')}_s0",
            "startPoint": start_point,
            "endPoint": end_point,
        }

        # Parse bendPoints from layout options if present
        edge_opts = edge.get("layoutOptions") or {}
        bp_str = edge_opts.get("bendPoints")
        if bp_str:
            parsed = _parse_kvector_chain(bp_str)
            if parsed:
                if len(parsed) >= 2:
                    section["startPoint"] = {"x": parsed[0][0], "y": parsed[0][1]}
                    section["endPoint"] = {"x": parsed[-1][0], "y": parsed[-1][1]}
                    if len(parsed) > 2:
                        section["bendPoints"] = [
                            {"x": p[0], "y": p[1]} for p in parsed[1:-1]
                        ]

        edge["sections"] = [section]


def _compute_graph_size(graph: dict, children: List[dict],
                        padding: Dict[str, float]) -> None:
    """Compute the overall graph dimensions based on children positions."""
    if not children:
        return

    max_x = 0.0
    max_y = 0.0
    for child in children:
        w, h = _get_node_size(child)
        cx = float(child.get("x", 0)) + w
        cy = float(child.get("y", 0)) + h
        max_x = max(max_x, cx)
        max_y = max(max_y, cy)

    graph["width"] = max_x + padding["right"]
    graph["height"] = max_y + padding["bottom"]


def _apply_padding(graph: dict, layout_options: dict) -> None:
    """Apply padding to an empty graph."""
    padding_str = _get_option(graph, "elk.padding", layout_options, "")
    padding = _parse_padding(padding_str if padding_str else "")
    graph["width"] = padding["left"] + padding["right"]
    graph["height"] = padding["top"] + padding["bottom"]


# ---------------------------------------------------------------------------
# Fixed layout algorithm
# ---------------------------------------------------------------------------

def _fixed_layout(graph: dict, layout_options: dict,
                  options: dict) -> dict:
    """Apply fixed layout: use positions specified in node layoutOptions."""
    children = graph.get("children") or []
    edges = graph.get("edges") or []

    for child in children:
        child_opts = child.get("layoutOptions") or {}
        pos_str = child_opts.get("position")
        if pos_str:
            parsed = _parse_kvector(pos_str)
            if parsed:
                child["x"] = parsed[0]
                child["y"] = parsed[1]
        # Ensure nodes have valid coordinates
        if child.get("x") is None:
            child["x"] = 0
        if child.get("y") is None:
            child["y"] = 0

    # Route edges
    node_map = _build_node_map(graph)
    _route_edges(edges, node_map, True)

    # Compute graph size
    padding_str = _get_option(graph, "elk.padding", layout_options, "")
    padding = _parse_padding(padding_str if padding_str else "")
    _compute_graph_size(graph, children, padding)

    return graph


# ---------------------------------------------------------------------------
# Stress layout algorithm (force-directed)
# ---------------------------------------------------------------------------

def _stress_layout(graph: dict, layout_options: dict,
                   options: dict) -> dict:
    """Perform stress-based (force-directed) layout."""
    children = graph.get("children") or []
    edges = graph.get("edges") or []

    if not children:
        _apply_padding(graph, layout_options)
        return graph

    nn_spacing = float(_get_option(
        graph, "elk.spacing.nodeNode", layout_options, DEFAULT_NODE_NODE_SPACING))

    padding_str = _get_option(graph, "elk.padding", layout_options, "")
    padding = _parse_padding(padding_str if padding_str else "")

    node_map = _build_node_map(graph)
    node_ids = [str(c.get("id")) for c in children if c.get("id") is not None]

    if not node_ids:
        _apply_padding(graph, layout_options)
        return graph

    # Build adjacency
    adj_set: Dict[str, Set[str]] = defaultdict(set)
    for edge in edges:
        for src in (edge.get("sources") or []):
            for tgt in (edge.get("targets") or []):
                s, t = str(src), str(tgt)
                if s in node_map and t in node_map:
                    adj_set[s].add(t)
                    adj_set[t].add(s)

    # Initialize positions in a circle
    n = len(node_ids)
    radius = nn_spacing * n / (2 * math.pi) if n > 1 else 0
    pos: Dict[str, List[float]] = {}
    for i, nid in enumerate(node_ids):
        angle = 2 * math.pi * i / n
        pos[nid] = [radius * math.cos(angle), radius * math.sin(angle)]

    # Compute shortest path distances (BFS)
    distances: Dict[str, Dict[str, int]] = {}
    for nid in node_ids:
        distances[nid] = _bfs_distances(nid, adj_set, set(node_ids))

    # Stress minimization iterations
    desired_edge_length = nn_spacing * 2
    for iteration in range(100):
        max_movement = 0.0
        for i_idx, nid_i in enumerate(node_ids):
            dx, dy = 0.0, 0.0
            weight_sum = 0.0

            for j_idx, nid_j in enumerate(node_ids):
                if i_idx == j_idx:
                    continue

                # Current distance
                diffx = pos[nid_i][0] - pos[nid_j][0]
                diffy = pos[nid_i][1] - pos[nid_j][1]
                current_dist = math.sqrt(diffx * diffx + diffy * diffy)

                if current_dist < 1e-6:
                    current_dist = 1e-6

                # Desired distance
                graph_dist = distances.get(nid_i, {}).get(nid_j, n)
                ideal_dist = graph_dist * desired_edge_length

                # Weight inversely proportional to squared graph distance
                w = 1.0 / (graph_dist * graph_dist) if graph_dist > 0 else 1.0

                # Stress force
                factor = w * (ideal_dist - current_dist) / current_dist
                dx += factor * diffx
                dy += factor * diffy
                weight_sum += w

            if weight_sum > 0:
                new_x = pos[nid_i][0] + dx / weight_sum
                new_y = pos[nid_i][1] + dy / weight_sum
                movement = math.sqrt(
                    (new_x - pos[nid_i][0]) ** 2 +
                    (new_y - pos[nid_i][1]) ** 2
                )
                max_movement = max(max_movement, movement)
                pos[nid_i] = [new_x, new_y]

        if max_movement < 0.1:
            break

    # Normalize positions to start from padding
    min_x = min(p[0] for p in pos.values())
    min_y = min(p[1] for p in pos.values())

    for nid in node_ids:
        node = node_map[nid]
        node["x"] = pos[nid][0] - min_x + padding["left"]
        node["y"] = pos[nid][1] - min_y + padding["top"]

    # Route edges and compute size
    _route_edges(edges, node_map, True)
    _compute_graph_size(graph, children, padding)

    return graph


def _bfs_distances(start: str, adj: Dict[str, Set[str]],
                   all_nodes: Set[str]) -> Dict[str, int]:
    """Compute shortest path distances from start using BFS."""
    dist: Dict[str, int] = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in adj.get(node, set()):
            if neighbor not in dist and neighbor in all_nodes:
                dist[neighbor] = dist[node] + 1
                queue.append(neighbor)
    # For disconnected nodes
    for nid in all_nodes:
        if nid not in dist:
            dist[nid] = len(all_nodes)
    return dist


# ---------------------------------------------------------------------------
# Force layout algorithm
# ---------------------------------------------------------------------------

def _force_layout(graph: dict, layout_options: dict,
                  options: dict) -> dict:
    """Simple force-directed layout (Fruchterman-Reingold style)."""
    children = graph.get("children") or []
    edges = graph.get("edges") or []

    if not children:
        _apply_padding(graph, layout_options)
        return graph

    nn_spacing = float(_get_option(
        graph, "elk.spacing.nodeNode", layout_options, DEFAULT_NODE_NODE_SPACING))

    padding_str = _get_option(graph, "elk.padding", layout_options, "")
    padding = _parse_padding(padding_str if padding_str else "")

    node_map = _build_node_map(graph)
    node_ids = [str(c.get("id")) for c in children if c.get("id") is not None]

    if not node_ids:
        _apply_padding(graph, layout_options)
        return graph

    n = len(node_ids)
    area = (nn_spacing * n) ** 2
    k = math.sqrt(area / max(n, 1))

    # Initialize positions
    pos: Dict[str, List[float]] = {}
    for i, nid in enumerate(node_ids):
        angle = 2 * math.pi * i / max(n, 1)
        r = k * 2
        pos[nid] = [r * math.cos(angle), r * math.sin(angle)]

    # Build edge set
    edge_pairs: List[Tuple[str, str]] = []
    for edge in edges:
        for src in (edge.get("sources") or []):
            for tgt in (edge.get("targets") or []):
                s, t = str(src), str(tgt)
                if s in node_map and t in node_map:
                    edge_pairs.append((s, t))

    temp = k * 2
    for iteration in range(50):
        # Repulsive forces
        disp: Dict[str, List[float]] = {nid: [0.0, 0.0] for nid in node_ids}

        for i in range(n):
            for j in range(i + 1, n):
                ni, nj = node_ids[i], node_ids[j]
                dx = pos[ni][0] - pos[nj][0]
                dy = pos[ni][1] - pos[nj][1]
                dist = max(math.sqrt(dx * dx + dy * dy), 0.01)
                force = k * k / dist
                fx = dx / dist * force
                fy = dy / dist * force
                disp[ni][0] += fx
                disp[ni][1] += fy
                disp[nj][0] -= fx
                disp[nj][1] -= fy

        # Attractive forces
        for src, tgt in edge_pairs:
            dx = pos[src][0] - pos[tgt][0]
            dy = pos[src][1] - pos[tgt][1]
            dist = max(math.sqrt(dx * dx + dy * dy), 0.01)
            force = dist * dist / k
            fx = dx / dist * force
            fy = dy / dist * force
            disp[src][0] -= fx
            disp[src][1] -= fy
            disp[tgt][0] += fx
            disp[tgt][1] += fy

        # Apply forces with temperature limiting
        for nid in node_ids:
            dx, dy = disp[nid]
            dist = max(math.sqrt(dx * dx + dy * dy), 0.01)
            capped = min(dist, temp)
            pos[nid][0] += dx / dist * capped
            pos[nid][1] += dy / dist * capped

        temp *= 0.95

    # Normalize positions
    min_x = min(p[0] for p in pos.values())
    min_y = min(p[1] for p in pos.values())

    for nid in node_ids:
        node = node_map[nid]
        node["x"] = pos[nid][0] - min_x + padding["left"]
        node["y"] = pos[nid][1] - min_y + padding["top"]

    _route_edges(edges, node_map, True)
    _compute_graph_size(graph, children, padding)

    return graph


# ---------------------------------------------------------------------------
# MrTree layout algorithm
# ---------------------------------------------------------------------------

def _mrtree_layout(graph: dict, layout_options: dict,
                   options: dict) -> dict:
    """Simple tree layout algorithm."""
    children = graph.get("children") or []
    edges = graph.get("edges") or []

    if not children:
        _apply_padding(graph, layout_options)
        return graph

    nn_spacing = float(_get_option(
        graph, "elk.spacing.nodeNode", layout_options, DEFAULT_NODE_NODE_SPACING))
    nn_between_layers = float(_get_option(
        graph, "elk.layered.spacing.nodeNodeBetweenLayers", layout_options,
        DEFAULT_NODE_NODE_BETWEEN_LAYERS))

    padding_str = _get_option(graph, "elk.padding", layout_options, "")
    padding = _parse_padding(padding_str if padding_str else "")

    node_map = _build_node_map(graph)
    node_ids = [str(c.get("id")) for c in children if c.get("id") is not None]

    if not node_ids:
        _apply_padding(graph, layout_options)
        return graph

    # Build adjacency
    child_map: Dict[str, List[str]] = defaultdict(list)
    parent_map: Dict[str, str] = {}
    for edge in edges:
        for src in (edge.get("sources") or []):
            for tgt in (edge.get("targets") or []):
                s, t = str(src), str(tgt)
                if s in node_map and t in node_map:
                    child_map[s].append(t)
                    parent_map[t] = s

    # Find roots
    roots = [nid for nid in node_ids if nid not in parent_map]
    if not roots:
        roots = [node_ids[0]]

    # BFS tree layout
    x_cursor = [padding["left"]]

    def layout_tree(node_id: str, depth: int) -> float:
        node = node_map[node_id]
        w, h = _get_node_size(node)
        node_children = child_map.get(node_id, [])

        y = padding["top"] + depth * (h + nn_between_layers)
        node["y"] = y

        if not node_children:
            node["x"] = x_cursor[0]
            x_cursor[0] += w + nn_spacing
            return node["x"] + w / 2

        child_centers = []
        for child_id in node_children:
            center = layout_tree(child_id, depth + 1)
            child_centers.append(center)

        center = sum(child_centers) / len(child_centers)
        node["x"] = center - w / 2
        return center

    for root in roots:
        layout_tree(root, 0)

    _route_edges(edges, node_map, False)
    _compute_graph_size(graph, children, padding)

    return graph


# ---------------------------------------------------------------------------
# Radial layout algorithm
# ---------------------------------------------------------------------------

def _radial_layout(graph: dict, layout_options: dict,
                   options: dict) -> dict:
    """Simple radial tree layout."""
    children = graph.get("children") or []
    edges = graph.get("edges") or []

    if not children:
        _apply_padding(graph, layout_options)
        return graph

    nn_spacing = float(_get_option(
        graph, "elk.spacing.nodeNode", layout_options, DEFAULT_NODE_NODE_SPACING))

    padding_str = _get_option(graph, "elk.padding", layout_options, "")
    padding = _parse_padding(padding_str if padding_str else "")

    node_map = _build_node_map(graph)
    node_ids = [str(c.get("id")) for c in children if c.get("id") is not None]

    if not node_ids:
        _apply_padding(graph, layout_options)
        return graph

    # Build adjacency
    adj: Dict[str, Set[str]] = defaultdict(set)
    for edge in edges:
        for src in (edge.get("sources") or []):
            for tgt in (edge.get("targets") or []):
                s, t = str(src), str(tgt)
                if s in node_map and t in node_map:
                    adj[s].add(t)
                    adj[t].add(s)

    root = node_ids[0]
    layer_spacing = nn_spacing * 3

    # BFS to get layers
    visited: Set[str] = {root}
    layers: List[List[str]] = [[root]]
    queue = list(adj.get(root, set()))

    while queue:
        next_layer = []
        for nid in queue:
            if nid not in visited:
                visited.add(nid)
                next_layer.append(nid)
        if next_layer:
            layers.append(next_layer)
            queue = []
            for nid in next_layer:
                queue.extend(adj.get(nid, set()))
        else:
            break

    # Add unvisited nodes
    for nid in node_ids:
        if nid not in visited:
            layers[-1].append(nid)
            visited.add(nid)

    # Assign radial positions
    center_x = padding["left"] + layer_spacing * len(layers)
    center_y = padding["top"] + layer_spacing * len(layers)

    for layer_idx, layer in enumerate(layers):
        radius = layer_spacing * layer_idx
        n = len(layer)
        for i, nid in enumerate(layer):
            angle = 2 * math.pi * i / max(n, 1)
            node = node_map[nid]
            w, h = _get_node_size(node)
            if layer_idx == 0:
                node["x"] = center_x - w / 2
                node["y"] = center_y - h / 2
            else:
                node["x"] = center_x + radius * math.cos(angle) - w / 2
                node["y"] = center_y + radius * math.sin(angle) - h / 2

    _route_edges(edges, node_map, True)
    _compute_graph_size(graph, children, padding)

    return graph


# ---------------------------------------------------------------------------
# SPOrE (Overlap Removal / Compaction) layout algorithms
# ---------------------------------------------------------------------------

def _spore_overlap_layout(graph: dict, layout_options: dict,
                          options: dict) -> dict:
    """Simple overlap removal layout."""
    children = graph.get("children") or []

    if not children:
        _apply_padding(graph, layout_options)
        return graph

    nn_spacing = float(_get_option(
        graph, "elk.spacing.nodeNode", layout_options, DEFAULT_NODE_NODE_SPACING))

    padding_str = _get_option(graph, "elk.padding", layout_options, "")
    padding = _parse_padding(padding_str if padding_str else "")

    node_map = _build_node_map(graph)

    # Sort children by their current position
    sorted_children = sorted(children,
                             key=lambda c: (c.get("y", 0), c.get("x", 0)))

    # Simple scan-line overlap removal
    placed: List[dict] = []
    for child in sorted_children:
        w, h = _get_node_size(child)
        cx = float(child.get("x", 0))
        cy = float(child.get("y", 0))

        # Check overlap with all placed nodes
        for other in placed:
            ow, oh = _get_node_size(other)
            ox = float(other.get("x", 0))
            oy = float(other.get("y", 0))

            # Check if overlapping
            if (cx < ox + ow + nn_spacing and cx + w + nn_spacing > ox and
                    cy < oy + oh + nn_spacing and cy + h + nn_spacing > oy):
                # Move this node to avoid overlap
                cx = ox + ow + nn_spacing
                cy = oy + oh + nn_spacing

        child["x"] = cx
        child["y"] = cy
        placed.append(child)

    # Apply padding offset
    min_x = min(float(c.get("x", 0)) for c in children)
    min_y = min(float(c.get("y", 0)) for c in children)
    for child in children:
        child["x"] = float(child.get("x", 0)) - min_x + padding["left"]
        child["y"] = float(child.get("y", 0)) - min_y + padding["top"]

    edges = graph.get("edges") or []
    _route_edges(edges, node_map, True)
    _compute_graph_size(graph, children, padding)

    return graph


def _spore_compaction_layout(graph: dict, layout_options: dict,
                             options: dict) -> dict:
    """Simple compaction layout — packs nodes tightly."""
    children = graph.get("children") or []

    if not children:
        _apply_padding(graph, layout_options)
        return graph

    nn_spacing = float(_get_option(
        graph, "elk.spacing.nodeNode", layout_options, DEFAULT_NODE_NODE_SPACING))

    padding_str = _get_option(graph, "elk.padding", layout_options, "")
    padding = _parse_padding(padding_str if padding_str else "")

    node_map = _build_node_map(graph)

    # Sort by original position (diagonal order)
    sorted_children = sorted(children,
                             key=lambda c: (c.get("x", 0) + c.get("y", 0)))

    # Compact placement
    for i, child in enumerate(sorted_children):
        w, h = _get_node_size(child)
        if i == 0:
            child["x"] = padding["left"]
            child["y"] = padding["top"]
        else:
            prev = sorted_children[i - 1]
            pw, ph = _get_node_size(prev)
            child["x"] = float(prev.get("x", 0)) + pw + nn_spacing
            child["y"] = float(prev.get("y", 0)) + ph + nn_spacing

    edges = graph.get("edges") or []
    _route_edges(edges, node_map, True)
    _compute_graph_size(graph, children, padding)

    return graph


# ---------------------------------------------------------------------------
# Rectangle packing layout algorithm
# ---------------------------------------------------------------------------

def _rectpacking_layout(graph: dict, layout_options: dict,
                        options: dict) -> dict:
    """Simple rectangle packing layout."""
    children = graph.get("children") or []

    if not children:
        _apply_padding(graph, layout_options)
        return graph

    nn_spacing = float(_get_option(
        graph, "elk.spacing.nodeNode", layout_options, DEFAULT_NODE_NODE_SPACING))

    padding_str = _get_option(graph, "elk.padding", layout_options, "")
    padding = _parse_padding(padding_str if padding_str else "")

    node_map = _build_node_map(graph)

    # Simple row-based packing
    total_area = sum(
        _get_node_size(c)[0] * _get_node_size(c)[1]
        for c in children
    )
    target_width = math.sqrt(total_area) * 1.5

    x = padding["left"]
    y = padding["top"]
    row_height = 0.0

    for child in children:
        w, h = _get_node_size(child)
        if x + w > target_width + padding["left"] and x > padding["left"]:
            x = padding["left"]
            y += row_height + nn_spacing
            row_height = 0.0

        child["x"] = x
        child["y"] = y
        x += w + nn_spacing
        row_height = max(row_height, h)

    edges = graph.get("edges") or []
    _route_edges(edges, node_map, True)
    _compute_graph_size(graph, children, padding)

    return graph


# ---------------------------------------------------------------------------
# Layout dispatcher
# ---------------------------------------------------------------------------

ALGORITHM_REGISTRY = {
    "layered": _layered_layout,
    "stress": _stress_layout,
    "force": _force_layout,
    "mrtree": _mrtree_layout,
    "radial": _radial_layout,
    "sporeOverlap": _spore_overlap_layout,
    "sporeCompaction": _spore_compaction_layout,
    "rectpacking": _rectpacking_layout,
    "fixed": _fixed_layout,
    # Aliases
    "elk.layered": _layered_layout,
    "elk.stress": _stress_layout,
    "elk.force": _force_layout,
    "elk.mrtree": _mrtree_layout,
    "elk.radial": _radial_layout,
    "elk.sporeOverlap": _spore_overlap_layout,
    "elk.sporeCompaction": _spore_compaction_layout,
    "elk.rectpacking": _rectpacking_layout,
    "elk.fixed": _fixed_layout,
    "org.eclipse.elk.layered": _layered_layout,
    "org.eclipse.elk.stress": _stress_layout,
    "org.eclipse.elk.force": _force_layout,
    "org.eclipse.elk.mrtree": _mrtree_layout,
    "org.eclipse.elk.radial": _radial_layout,
    "org.eclipse.elk.sporeOverlap": _spore_overlap_layout,
    "org.eclipse.elk.sporeCompaction": _spore_compaction_layout,
    "org.eclipse.elk.rectpacking": _rectpacking_layout,
    "org.eclipse.elk.fixed": _fixed_layout,
}


def _dispatch_layout(graph: dict, layout_options: dict,
                     options: dict) -> dict:
    """Dispatch to the appropriate layout algorithm."""
    algo = _resolve_algorithm(graph, layout_options)

    layout_fn = ALGORITHM_REGISTRY.get(algo)
    if layout_fn is None:
        raise ValueError(
            f"org.eclipse.elk.core.UnsupportedConfigurationException: "
            f"No layout algorithm registered for '{algo}'. "
            f"Available algorithms: {sorted(set(ALGORITHM_REGISTRY.keys()))}"
        )

    return layout_fn(graph, layout_options, options)


# ---------------------------------------------------------------------------
# Public layout function
# ---------------------------------------------------------------------------

def layout(graph: dict,
           layout_options: Optional[Dict[str, str]] = None,
           options: Optional[Dict[str, Any]] = None) -> dict:
    """Perform layout on a graph dict, modifying it in-place and returning it.

    Args:
        graph: The ELK graph as a plain Python dict.
        layout_options: Global layout options to apply (overridden by per-element options).
        options: Additional options (logging, measureExecutionTime).

    Returns:
        The same graph dict with positions computed.

    Raises:
        ValueError: If the graph is missing an 'id' field or an unknown algorithm is specified.
    """
    if layout_options is None:
        layout_options = {}
    if options is None:
        options = {}

    # Validate graph
    _validate_graph(graph)

    # Handle logging
    record_logs = options.get("logging", False)
    record_exec_time = options.get("measureExecutionTime", False)

    # Clean old logging
    if "logging" in graph:
        del graph["logging"]

    start_time = time.time() if record_exec_time else None

    # Apply global layout options (without overriding per-element options)
    _apply_global_options(graph, layout_options)

    # Dispatch layout
    _dispatch_layout(graph, layout_options, options)

    # Record logging if requested
    if record_logs or record_exec_time:
        logging_info: Dict[str, Any] = {"name": "Root"}
        if record_logs:
            algo = _resolve_algorithm(graph, layout_options)
            logging_info["logs"] = [f"Algorithm: {algo}"]
            logging_info["children"] = [{"name": f"Layout ({algo})"}]
        if record_exec_time and start_time is not None:
            logging_info["executionTime"] = time.time() - start_time
        graph["logging"] = logging_info

    return graph


def _validate_graph(graph: dict) -> None:
    """Validate the graph structure."""
    if not isinstance(graph, dict):
        raise ValueError("Graph must be a dictionary")

    graph_id = graph.get("id")

    if graph_id is None:
        raise ValueError("Graph element is missing mandatory 'id' property.")

    # id must be string or integer (matching JS behavior)
    if isinstance(graph_id, bool):
        raise ValueError(
            f"Invalid id type: boolean. Expected string or integer.")
    if isinstance(graph_id, float) and graph_id != int(graph_id):
        raise ValueError(
            f"Invalid id type: non-integral number. Expected string or integer.")
    if isinstance(graph_id, (list, dict)):
        raise ValueError(
            f"Invalid id type: {type(graph_id).__name__}. Expected string or integer.")


def _apply_global_options(graph: dict, layout_options: dict) -> None:
    """Apply global layout options to graph without overriding existing options."""
    # This mirrors the LayoutConfigurator.NO_OVERWRITE behavior from ELK
    # Global options are only used if not already set on the element
    pass  # Options are resolved at layout time via _get_option


# ---------------------------------------------------------------------------
# Algorithm metadata (for knownLayoutAlgorithms, etc.)
# ---------------------------------------------------------------------------

ALGORITHM_DESCRIPTIONS = [
    {
        "id": "org.eclipse.elk.layered",
        "name": "ELK Layered",
        "description": "Layer-based algorithm provided by ELK, implementing Sugiyama's approach.",
        "category": "org.eclipse.elk.algorithm.category.layered",
        "knownOptions": [
            "org.eclipse.elk.direction",
            "org.eclipse.elk.spacing.nodeNode",
            "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers",
            "org.eclipse.elk.padding",
        ],
        "supportedFeatures": ["MULTI_EDGES", "EDGE_LABELS", "PORTS", "COMPOUND"],
    },
    {
        "id": "org.eclipse.elk.stress",
        "name": "ELK Stress",
        "description": "Stress-minimizing force-directed layout.",
        "category": "org.eclipse.elk.algorithm.category.force",
        "knownOptions": [
            "org.eclipse.elk.spacing.nodeNode",
            "org.eclipse.elk.padding",
        ],
        "supportedFeatures": [],
    },
    {
        "id": "org.eclipse.elk.force",
        "name": "ELK Force",
        "description": "Force-directed layout using Fruchterman-Reingold.",
        "category": "org.eclipse.elk.algorithm.category.force",
        "knownOptions": [
            "org.eclipse.elk.spacing.nodeNode",
            "org.eclipse.elk.padding",
        ],
        "supportedFeatures": [],
    },
    {
        "id": "org.eclipse.elk.mrtree",
        "name": "ELK Mr. Tree",
        "description": "Tree layout algorithm.",
        "category": "org.eclipse.elk.algorithm.category.tree",
        "knownOptions": [
            "org.eclipse.elk.spacing.nodeNode",
            "org.eclipse.elk.padding",
        ],
        "supportedFeatures": [],
    },
    {
        "id": "org.eclipse.elk.radial",
        "name": "ELK Radial",
        "description": "Radial layout algorithm.",
        "category": "org.eclipse.elk.algorithm.category.tree",
        "knownOptions": [
            "org.eclipse.elk.spacing.nodeNode",
            "org.eclipse.elk.padding",
        ],
        "supportedFeatures": [],
    },
    {
        "id": "org.eclipse.elk.sporeOverlap",
        "name": "ELK SPOrE Overlap Removal",
        "description": "Overlap removal layout.",
        "category": "org.eclipse.elk.algorithm.category.other",
        "knownOptions": [
            "org.eclipse.elk.spacing.nodeNode",
            "org.eclipse.elk.padding",
        ],
        "supportedFeatures": [],
    },
    {
        "id": "org.eclipse.elk.sporeCompaction",
        "name": "ELK SPOrE Compaction",
        "description": "Compaction layout.",
        "category": "org.eclipse.elk.algorithm.category.other",
        "knownOptions": [
            "org.eclipse.elk.spacing.nodeNode",
            "org.eclipse.elk.padding",
        ],
        "supportedFeatures": [],
    },
    {
        "id": "org.eclipse.elk.rectpacking",
        "name": "ELK Rectangle Packing",
        "description": "Rectangle packing algorithm.",
        "category": "org.eclipse.elk.algorithm.category.other",
        "knownOptions": [
            "org.eclipse.elk.spacing.nodeNode",
            "org.eclipse.elk.padding",
        ],
        "supportedFeatures": [],
    },
    {
        "id": "org.eclipse.elk.fixed",
        "name": "ELK Fixed",
        "description": "Fixed layout preserving given positions.",
        "category": "org.eclipse.elk.algorithm.category.other",
        "knownOptions": ["org.eclipse.elk.padding"],
        "supportedFeatures": [],
    },
]

OPTION_DESCRIPTIONS = [
    {
        "id": "org.eclipse.elk.direction",
        "name": "Direction",
        "description": "Overall direction of edges: horizontal (RIGHT/LEFT) or vertical (DOWN/UP).",
        "group": "",
        "type": "enum",
        "targets": ["PARENTS"],
    },
    {
        "id": "org.eclipse.elk.spacing.nodeNode",
        "name": "Node Spacing",
        "description": "Spacing between nodes within a layer.",
        "group": "spacing",
        "type": "double",
        "targets": ["PARENTS"],
    },
    {
        "id": "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers",
        "name": "Node Spacing Between Layers",
        "description": "Spacing between layers (between nodes of adjacent layers).",
        "group": "spacing",
        "type": "double",
        "targets": ["PARENTS"],
    },
    {
        "id": "org.eclipse.elk.padding",
        "name": "Padding",
        "description": "Padding around the graph content.",
        "group": "",
        "type": "ElkPadding",
        "targets": ["PARENTS", "NODES"],
    },
    {
        "id": "org.eclipse.elk.algorithm",
        "name": "Layout Algorithm",
        "description": "Select a specific layout algorithm.",
        "group": "",
        "type": "string",
        "targets": ["PARENTS"],
    },
]

CATEGORY_DESCRIPTIONS = [
    {
        "id": "org.eclipse.elk.algorithm.category.layered",
        "name": "Layered",
        "description": "Algorithms following the layer-based approach by Sugiyama et al.",
        "knownLayouters": ["org.eclipse.elk.layered"],
    },
    {
        "id": "org.eclipse.elk.algorithm.category.force",
        "name": "Force",
        "description": "Force-based layout algorithms.",
        "knownLayouters": ["org.eclipse.elk.stress", "org.eclipse.elk.force"],
    },
    {
        "id": "org.eclipse.elk.algorithm.category.tree",
        "name": "Tree",
        "description": "Algorithms specialized for tree structures.",
        "knownLayouters": ["org.eclipse.elk.mrtree", "org.eclipse.elk.radial"],
    },
    {
        "id": "org.eclipse.elk.algorithm.category.other",
        "name": "Other",
        "description": "Other layout algorithms.",
        "knownLayouters": [
            "org.eclipse.elk.sporeOverlap",
            "org.eclipse.elk.sporeCompaction",
            "org.eclipse.elk.rectpacking",
            "org.eclipse.elk.fixed",
        ],
    },
]
