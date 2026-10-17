"""Material Maker ``.ptex`` graphs: the node library, readback and typed edits.

A ``.ptex`` file is JSON: a top-level graph with ``nodes`` (``name``, ``type``,
``parameters``, ``node_position``) and ``connections`` (``from``/``from_port``
to ``to``/``to_port``). Node types name the ``.mmg`` definitions Material Maker
ships next to its executable (``<install>/nodes``), which also declare each
type's inputs, outputs, parameters and, for material nodes, export profiles.
Edits here touch only the top-level graph and never add embedded shader code.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

NODE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
# Node types Material Maker builds in rather than loading from a .mmg file.
BUILTIN_TYPES = {
    "image": {
        "shortdesc": "Image file (PNG, JPG, EXR, ...) used as a texture",
        "inputs": [],
        "outputs": [{"index": 0, "type": "rgba"}],
        "parameters": [
            {"name": "image", "type": "image_path", "default": ""},
            {"name": "fix_ar", "type": "boolean", "default": False},
            {"name": "clamp", "type": "boolean", "default": False},
        ],
    },
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".exr", ".webp", ".tga", ".bmp", ".hdr", ".dds"}
# Node types that reach outside the graph: the camera, or materialmaker.org.
FORBIDDEN_TYPES = {"webcam"}
FORBIDDEN_PREFIXES = ("website:",)


class GraphError(ValueError):
    """A graph edit or a node lookup was rejected."""


class NodeLibrary:
    """The ``.mmg`` node definitions of one Material Maker installation."""

    def __init__(self, nodes_dir: Optional[Path]) -> None:
        self.nodes_dir = nodes_dir if nodes_dir is not None and nodes_dir.is_dir() else None
        self._cache: dict[str, Optional[dict[str, Any]]] = {}

    def names(self) -> list[str]:
        if self.nodes_dir is None:
            return []
        return sorted(path.stem for path in self.nodes_dir.glob("*.mmg"))

    def addable(self, node_type: str) -> bool:
        return node_type in BUILTIN_TYPES or (
            self.nodes_dir is not None and (self.nodes_dir / (node_type + ".mmg")).is_file()
        )

    def raw(self, node_type: str) -> Optional[dict[str, Any]]:
        if node_type not in self._cache:
            data = None
            if self.nodes_dir is not None and NODE_NAME.match(node_type):
                path = self.nodes_dir / (node_type + ".mmg")
                if path.is_file():
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                    except (OSError, UnicodeError, json.JSONDecodeError):
                        data = None
            self._cache[node_type] = data if isinstance(data, dict) else None
        return self._cache[node_type]

    def describe(self, node_type: str) -> Optional[dict[str, Any]]:
        """Inputs, outputs and parameters of a node type, or None when unknown."""
        if node_type in BUILTIN_TYPES:
            return {"type": node_type, **copy.deepcopy(BUILTIN_TYPES[node_type])}
        data = self.raw(node_type)
        if data is None:
            return None
        model = data.get("shader_model")
        if isinstance(model, dict):
            parameters = [_parameter(p) for p in model.get("parameters", []) if isinstance(p, dict)]
            return {
                "type": node_type,
                "shortdesc": model.get("shortdesc") or model.get("name"),
                "inputs": [
                    {"index": i, "name": p.get("name"), "type": p.get("type")}
                    for i, p in enumerate(model.get("inputs", []))
                ],
                "outputs": [
                    {"index": i, "type": p.get("type"), "description": p.get("shortdesc")}
                    for i, p in enumerate(model.get("outputs", []))
                ],
                "parameters": parameters,
                "export_targets": sorted(model.get("exports", {})) or None,
            }
        # A node built as a graph: its ports and controls are its ios and remote nodes.
        nodes = {n.get("name"): n for n in data.get("nodes", []) if isinstance(n, dict)}

        def ports(name: str) -> list[dict[str, Any]]:
            node = nodes.get(name) or {}
            return [
                {"index": i, "name": p.get("name"), "type": p.get("type")}
                for i, p in enumerate(node.get("ports", []))
            ]

        values = data.get("parameters") if isinstance(data.get("parameters"), dict) else {}
        widgets = (nodes.get("gen_parameters") or {}).get("widgets", [])
        return {
            "type": node_type,
            "shortdesc": data.get("shortdesc") or data.get("label"),
            "inputs": ports("gen_inputs"),
            "outputs": ports("gen_outputs"),
            "parameters": [
                {
                    "name": w.get("name"),
                    "label": w.get("label") or w.get("shortdesc"),
                    "default": values.get(w.get("name")),
                }
                for w in widgets
                if isinstance(w, dict) and w.get("name")
            ],
            "export_targets": None,
        }

    def export_profiles(self, node: Mapping[str, Any]) -> Optional[dict[str, Any]]:
        """The export profiles of a material node (inline or from its type), if any."""
        model = node.get("shader_model")
        if not isinstance(model, dict):
            data = self.raw(str(node.get("type", "")))
            model = data.get("shader_model") if data else None
        if isinstance(model, dict) and isinstance(model.get("exports"), dict):
            return model["exports"]
        return None


def _parameter(p: Mapping[str, Any]) -> dict[str, Any]:
    item = {key: p[key] for key in ("name", "type", "default", "min", "max") if key in p}
    label = p.get("shortdesc") or p.get("label")
    if label:
        item["label"] = label
    if p.get("type") == "enum":
        item["values"] = [v.get("name") for v in p.get("values", []) if isinstance(v, dict)]
    return item


def walk_nodes(graph: Mapping[str, Any]):
    """Every node of a graph and of the graphs nested in it."""
    stack = [graph]
    while stack:
        current = stack.pop()
        for node in current.get("nodes", []) if isinstance(current.get("nodes"), list) else []:
            if isinstance(node, dict):
                yield node
                if isinstance(node.get("nodes"), list):
                    stack.append(node)


def security_errors(graph: Mapping[str, Any]) -> list[str]:
    """Nodes Material Maker would let reach the camera, the network or other folders."""
    errors = []
    for node in walk_nodes(graph):
        node_type = str(node.get("type", ""))
        if node_type in FORBIDDEN_TYPES or node_type.startswith(FORBIDDEN_PREFIXES):
            errors.append("Node %s has type %s, which this adapter does not run" % (node.get("name"), node_type))
        if node_type == "export":
            suffix = str((node.get("parameters") or {}).get("suffix", ""))
            if "/" in suffix or "\\" in suffix or ".." in suffix:
                errors.append("Export node %s writes outside the export directory" % node.get("name"))
    return errors


def summary(graph: Mapping[str, Any], node: Optional[str] = None) -> dict[str, Any]:
    """Readback of the top-level graph: nodes with parameters, and connections."""
    nodes = [n for n in graph.get("nodes", []) if isinstance(n, dict)]
    if node is not None:
        nodes = [n for n in nodes if n.get("name") == node]
        if not nodes:
            raise GraphError("No node named %s" % node)
    return {
        "nodes": [
            {
                "name": n.get("name"),
                "type": n.get("type"),
                "parameters": n.get("parameters", {}),
                **({"subgraph_nodes": len(n["nodes"])} if isinstance(n.get("nodes"), list) else {}),
            }
            for n in nodes
        ],
        "connections": [
            c
            for c in graph.get("connections", [])
            if node is None or node in (c.get("from"), c.get("to"))
        ],
    }


def blank_material(name: str) -> dict[str, Any]:
    """A graph holding only Material Maker's standard material output node."""
    return {
        "connections": [],
        "label": "Graph",
        "name": name,
        "node_position": {"x": 0, "y": 0},
        "nodes": [
            {
                "name": "Material",
                "type": "material",
                "node_position": {"x": 0, "y": 0},
                "parameters": {},
                "export_paths": {},
            }
        ],
        "parameters": {},
        "type": "graph",
    }


class GraphEditor:
    """Apply typed operations to a copy of a top-level graph."""

    def __init__(self, graph: dict[str, Any], library: NodeLibrary, project_root: Path) -> None:
        self.graph = copy.deepcopy(graph)
        if not isinstance(self.graph.get("nodes"), list) or not isinstance(
            self.graph.get("connections"), list
        ):
            raise GraphError("Project has no top-level node graph")
        self.library = library
        self.project_root = project_root

    def _node(self, name: Any) -> dict[str, Any]:
        for node in self.graph["nodes"]:
            if isinstance(node, dict) and node.get("name") == name:
                return node
        raise GraphError("No node named %s" % name)

    def apply(self, operations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if not isinstance(operations, (list, tuple)) or not operations:
            raise GraphError("operations must be a non-empty list")
        if len(operations) > 200:
            raise GraphError("At most 200 operations per call")
        for index, operation in enumerate(operations):
            if not isinstance(operation, Mapping):
                raise GraphError("Operation %d is not an object" % index)
            handler = {
                "add_node": self._add_node,
                "remove_node": self._remove_node,
                "set_parameters": self._set_parameters,
                "connect": self._connect,
                "disconnect": self._disconnect,
            }.get(operation.get("op"))
            if handler is None:
                raise GraphError(
                    "Operation %d: op must be add_node, remove_node, set_parameters, "
                    "connect or disconnect" % index
                )
            try:
                handler(operation)
            except GraphError as error:
                raise GraphError("Operation %d (%s): %s" % (index, operation.get("op"), error))
        return self.graph

    def _add_node(self, operation: Mapping[str, Any]) -> None:
        name, node_type = operation.get("name"), operation.get("type")
        if not isinstance(name, str) or not NODE_NAME.match(name):
            raise GraphError("name must be letters, digits and underscores, starting with a letter")
        if any(isinstance(n, dict) and n.get("name") == name for n in self.graph["nodes"]):
            raise GraphError("A node named %s already exists" % name)
        if not isinstance(node_type, str) or not self.library.addable(node_type):
            raise GraphError(
                "Unknown node type %r; list_node_types shows the types this Material Maker has"
                % node_type
            )
        position = operation.get("position")
        if position is None:
            xs = [n.get("node_position", {}).get("x", 0) for n in self.graph["nodes"] if isinstance(n, dict)]
            position = {"x": (min(xs) if xs else 0) - 300, "y": 0}
        if not (
            isinstance(position, Mapping)
            and all(isinstance(position.get(k), (int, float)) for k in ("x", "y"))
        ):
            raise GraphError("position must be {x, y}")
        node = {
            "name": name,
            "type": node_type,
            "node_position": {"x": position["x"], "y": position["y"]},
            "parameters": {},
        }
        self.graph["nodes"].append(node)
        self._set_parameters({"node": name, "parameters": operation.get("parameters") or {}})

    def _remove_node(self, operation: Mapping[str, Any]) -> None:
        node = self._node(operation.get("node"))
        self.graph["nodes"].remove(node)
        name = node["name"]
        self.graph["connections"] = [
            c for c in self.graph["connections"] if name not in (c.get("from"), c.get("to"))
        ]

    def _set_parameters(self, operation: Mapping[str, Any]) -> None:
        node = self._node(operation.get("node"))
        values = operation.get("parameters")
        if not isinstance(values, Mapping):
            raise GraphError("parameters must be an object")
        described = self.library.describe(str(node.get("type")))
        definitions = (
            {p["name"]: p for p in described["parameters"] if p.get("name")} if described else None
        )
        parameters = node.setdefault("parameters", {})
        for key, value in values.items():
            if definitions is not None and key not in definitions:
                raise GraphError(
                    "%s has no parameter %s; it has %s"
                    % (node.get("type"), key, ", ".join(sorted(definitions)) or "none")
                )
            definition = (definitions or {}).get(key, {})
            parameters[key] = self._value(definition, key, value)

    def _value(self, definition: Mapping[str, Any], key: str, value: Any) -> Any:
        kind = definition.get("type")
        if kind == "image_path":
            if not isinstance(value, str) or not value:
                raise GraphError("%s must be an image file path" % key)
            path = Path(value).expanduser()
            path = (path if path.is_absolute() else self.project_root / path).resolve()
            if path.suffix.lower() not in IMAGE_SUFFIXES or not path.is_file():
                raise GraphError("%s must name an existing image file" % key)
            if not _inside(path, self.project_root):
                raise GraphError("%s must be inside the project folder" % key)
            # Material Maker resolves relative paths against its own install folder.
            return str(path)
        if kind == "color":
            if isinstance(value, Mapping) and all(
                isinstance(value.get(c), (int, float)) for c in ("r", "g", "b")
            ):
                return {
                    "r": value["r"],
                    "g": value["g"],
                    "b": value["b"],
                    "a": value.get("a", 1),
                    "type": "Color",
                }
            raise GraphError("%s must be a color {r, g, b, a} with 0-1 components" % key)
        if kind == "boolean":
            if not isinstance(value, bool):
                raise GraphError("%s must be true or false" % key)
            return value
        if kind in ("float", "size", "enum"):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise GraphError("%s must be a number" % key)
            if kind == "enum":
                options = definition.get("values") or []
                if not isinstance(value, int) or not 0 <= value < len(options):
                    raise GraphError("%s must be an index into %s" % (key, options))
            return value
        if isinstance(value, (Mapping, list)):
            if "shader_model" in json.dumps(value):
                raise GraphError("%s cannot carry shader code" % key)
            return copy.deepcopy(value)
        if isinstance(value, (str, int, float, bool)):
            return value
        raise GraphError("%s has an unsupported value" % key)

    def _ports(self, node: Mapping[str, Any], side: str) -> Optional[int]:
        described = self.library.describe(str(node.get("type")))
        return None if described is None else len(described[side])

    def _connect(self, operation: Mapping[str, Any]) -> None:
        source, target = self._node(operation.get("from")), self._node(operation.get("to"))
        from_port, to_port = operation.get("from_port", 0), operation.get("to_port")
        for label, port, node, side in (
            ("from_port", from_port, source, "outputs"),
            ("to_port", to_port, target, "inputs"),
        ):
            if isinstance(port, bool) or not isinstance(port, int) or port < 0:
                raise GraphError("%s must be a port index" % label)
            count = self._ports(node, side)
            if count is not None and port >= count:
                raise GraphError("%s %d: %s has %d %s" % (label, port, node["name"], count, side))
        # One source per input: the new connection replaces the old one.
        self._disconnect({"to": target["name"], "to_port": to_port})
        self.graph["connections"].append(
            {"from": source["name"], "from_port": from_port, "to": target["name"], "to_port": to_port}
        )

    def _disconnect(self, operation: Mapping[str, Any]) -> None:
        target, port = operation.get("to"), operation.get("to_port")
        self.graph["connections"] = [
            c
            for c in self.graph["connections"]
            if not (c.get("to") == target and c.get("to_port") == port)
        ]


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
