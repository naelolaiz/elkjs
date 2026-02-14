"""ELK - Eclipse Layout Kernel for Python.

A Python port of elkjs providing automatic graph layout based on
the Eclipse Layout Kernel (ELK). Supports multiple layout algorithms
including layered (Sugiyama), stress, force, mrtree, radial, and more.
Specialized for data flow diagrams and ports.

This module communicates with the ELK layout engine via a Node.js
subprocess using the compiled GWT JavaScript worker.

Example usage::

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
"""

import json
import os
import shutil
import subprocess
import threading
from typing import Any, Dict, List, Optional, Union

from .typedefs import (
    ElkExtendedEdge,
    ElkLayoutAlgorithmDescription,
    ElkLayoutCategoryDescription,
    ElkLayoutOptionDescription,
    ElkNode,
)

DEFAULT_ALGORITHMS = [
    "layered",
    "stress",
    "mrtree",
    "radial",
    "force",
    "disco",
    "sporeOverlap",
    "sporeCompaction",
    "rectpacking",
]

# Locate the bridge script shipped with this package
_BRIDGE_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bridge.js")

# Default search paths for the elk-worker file, relative to the package
_DEFAULT_WORKER_SEARCH_PATHS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib", "elk-worker.min.js"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib", "elk-worker.js"),
]


def _find_default_worker_path() -> Optional[str]:
    """Find the default elk-worker.js file."""
    for p in _DEFAULT_WORKER_SEARCH_PATHS:
        resolved = os.path.normpath(p)
        if os.path.exists(resolved):
            return resolved
    return None


class ELK:
    """ELK layout engine.

    Provides automatic graph layout using the Eclipse Layout Kernel
    algorithms via a Node.js subprocess bridge.

    Parameters
    ----------
    default_layout_options : dict, optional
        Default layout options applied to every ``layout()`` call.
    algorithms : list of str, optional
        Algorithms to register with the engine.  Defaults to all
        built-in algorithms.
    worker_path : str, optional
        Path to the ``elk-worker.min.js`` (or ``elk-worker.js``) file.
        If not specified, the library searches in the default
        ``lib/`` directory of the repository.
    node_path : str, optional
        Path to the Node.js executable.  If not specified, ``node``
        is looked up on ``PATH``.
    """

    def __init__(
        self,
        default_layout_options: Optional[Dict[str, str]] = None,
        algorithms: Optional[List[str]] = None,
        worker_path: Optional[str] = None,
        node_path: Optional[str] = None,
    ) -> None:
        self.default_layout_options: Dict[str, str] = default_layout_options or {}
        self.initialized: bool = False

        # Resolve Node.js
        node = node_path or shutil.which("node")
        if node is None:
            raise RuntimeError(
                "Node.js is required but was not found on PATH.  "
                "Install Node.js or pass the 'node_path' argument."
            )

        # Resolve worker
        if worker_path is None:
            worker_path = _find_default_worker_path()
        if worker_path is None or not os.path.exists(worker_path):
            raise FileNotFoundError(
                "Cannot find elk-worker JavaScript file.  "
                "Either install the elkjs npm package or pass 'worker_path'."
            )

        # Start Node.js bridge subprocess
        self._process: Optional[subprocess.Popen] = subprocess.Popen(
            [node, _BRIDGE_SCRIPT, os.path.abspath(worker_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # line-buffered
        )

        # Internal state for message passing
        self._id: int = 0
        self._lock = threading.Lock()
        self._responses: Dict[int, dict] = {}
        self._response_events: Dict[int, threading.Event] = {}

        # Reader thread
        self._reader_thread = threading.Thread(target=self._read_responses, daemon=True)
        self._reader_thread.start()

        # Register algorithms
        algos = algorithms if algorithms is not None else DEFAULT_ALGORITHMS
        self._send_message({"cmd": "register", "algorithms": algos})
        self.initialized = True

    # ------------------------------------------------------------------
    # Internal communication
    # ------------------------------------------------------------------

    def _read_responses(self) -> None:
        """Background thread that reads JSON responses from the bridge."""
        assert self._process is not None
        assert self._process.stdout is not None
        while True:
            try:
                line = self._process.stdout.readline()
                if not line:
                    break
                data = json.loads(line.strip())
                msg_id = data.get("id")
                if msg_id is not None and msg_id in self._response_events:
                    self._responses[msg_id] = data
                    self._response_events[msg_id].set()
            except (json.JSONDecodeError, ValueError):
                continue

    def _send_message(self, msg: dict, timeout: float = 60) -> Any:
        """Send a command to the bridge and wait for the response."""
        if self._process is None or self._process.poll() is not None:
            raise RuntimeError("ELK worker process is not running.")

        with self._lock:
            msg_id = self._id
            self._id += 1

        msg["id"] = msg_id
        event = threading.Event()
        self._response_events[msg_id] = event

        assert self._process.stdin is not None
        self._process.stdin.write(json.dumps(msg) + "\n")
        self._process.stdin.flush()

        if not event.wait(timeout=timeout):
            raise TimeoutError(f"Timeout waiting for response to message {msg_id}")

        response = self._responses.pop(msg_id)
        del self._response_events[msg_id]

        if response.get("error"):
            error = response["error"]
            if isinstance(error, dict):
                msg_text = error.get("message", str(error))
            else:
                msg_text = str(error)
            raise Exception(msg_text)

        return response.get("data")

    # ------------------------------------------------------------------
    # Public API  (mirrors elkjs JavaScript API)
    # ------------------------------------------------------------------

    def layout(
        self,
        graph: Optional[Dict[str, Any]] = None,
        layout_options: Optional[Dict[str, str]] = None,
        logging: bool = False,
        measure_execution_time: bool = False,
    ) -> Dict[str, Any]:
        """Compute layout for the given graph.

        The graph dict is modified **in-place** with computed positions
        and the same dict is returned, matching the JavaScript API.

        Parameters
        ----------
        graph : dict
            An ELK graph (``ElkNode`` structure).
        layout_options : dict, optional
            Layout options for this particular call.  Falls back to
            ``default_layout_options`` if not specified.
        logging : bool
            Whether to include logging information in the result.
        measure_execution_time : bool
            Whether to measure execution time.

        Returns
        -------
        dict
            The input *graph* dict, updated with layout information.

        Raises
        ------
        ValueError
            If *graph* is ``None``.
        Exception
            If the layout engine reports an error.
        """
        if graph is None:
            raise ValueError("Missing mandatory parameter 'graph'.")

        opts = layout_options if layout_options is not None else self.default_layout_options

        result = self._send_message(
            {
                "cmd": "layout",
                "graph": graph,
                "layoutOptions": opts,
                "options": {
                    "logging": logging,
                    "measureExecutionTime": measure_execution_time,
                },
            }
        )

        # Update graph in-place (mirrors JS behaviour where the graph
        # object is mutated and then resolved via the Promise).
        if isinstance(result, dict):
            graph.clear()
            graph.update(result)

        return graph

    def known_layout_algorithms(self) -> List[ElkLayoutAlgorithmDescription]:
        """Return the list of known layout algorithms."""
        return self._send_message({"cmd": "algorithms"})

    def known_layout_options(self) -> List[ElkLayoutOptionDescription]:
        """Return the list of known layout options."""
        return self._send_message({"cmd": "options"})

    def known_layout_categories(self) -> List[ElkLayoutCategoryDescription]:
        """Return the list of known layout categories."""
        return self._send_message({"cmd": "categories"})

    def terminate_worker(self) -> None:
        """Terminate the underlying Node.js worker process."""
        if self._process is not None:
            try:
                if self._process.stdin:
                    self._process.stdin.close()
                self._process.terminate()
                self._process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                self._process.kill()
            finally:
                self._process = None

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "ELK":
        return self

    def __exit__(self, *args: Any) -> None:
        self.terminate_worker()

    def __del__(self) -> None:
        try:
            self.terminate_worker()
        except Exception:
            pass
