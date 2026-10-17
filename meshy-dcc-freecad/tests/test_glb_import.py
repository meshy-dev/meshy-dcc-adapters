"""GLB import: the bridge gate everywhere, the host read-back on a real FreeCAD."""

import json
import os
import struct
from pathlib import Path

import pytest

from meshy_dcc_freecad.bridge import BridgeError, FreecadBridge


def write_glb(path: Path) -> Path:
    """A tetrahedron with 1 m edges along the axes, as a Meshy GLB stores it (metres)."""
    positions = b"".join(
        struct.pack("<3f", *p) for p in [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
    )
    indices = struct.pack("<12H", 0, 2, 1, 0, 1, 3, 0, 3, 2, 1, 2, 3)
    binary = positions + indices
    document = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(positions)},
            {"buffer": 0, "byteOffset": len(positions), "byteLength": len(indices)},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 4,
                "type": "VEC3",
                "min": [0, 0, 0],
                "max": [1, 1, 1],
            },
            {"bufferView": 1, "componentType": 5123, "count": 12, "type": "SCALAR"},
        ],
    }
    text = json.dumps(document).encode()
    text += b" " * (-len(text) % 4)
    body = struct.pack("<II", len(text), 0x4E4F534A) + text
    body += struct.pack("<II", len(binary), 0x004E4942) + binary
    path.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)
    return path


def test_the_gate_takes_glb_and_refuses_gltf(tmp_path, monkeypatch):
    bridge = FreecadBridge(allowed_roots=[tmp_path])
    calls = []
    monkeypatch.setattr(bridge, "_mutate_document", lambda *args: calls.append(args) or {})
    document = tmp_path / "scene.FCStd"
    document.write_bytes(b"x")
    bridge.import_geometry(str(document), str(write_glb(tmp_path / "model.glb")), "Model")
    assert calls[0][0] == "model.import_geometry"

    (tmp_path / "model.gltf").write_text("{}")
    with pytest.raises(BridgeError, match="Unsupported input extension"):
        bridge.import_geometry(str(document), str(tmp_path / "model.gltf"), "Other")


@pytest.mark.freecad
@pytest.mark.skipif(
    not os.environ.get("FREECAD_TEST_EXECUTABLE"), reason="FREECAD_TEST_EXECUTABLE is not set"
)
def test_real_glb_lands_as_a_mesh_in_millimetres(tmp_path):
    bridge = FreecadBridge(os.environ["FREECAD_TEST_EXECUTABLE"], allowed_roots=[tmp_path])
    document = tmp_path / "meshy.FCStd"
    bridge.create_document(str(document))

    result = bridge.import_geometry(str(document), str(write_glb(tmp_path / "tetra.glb")), "Tetra")

    assert "source.triangles" in result["verified"]
    inspected = bridge.inspect_document(str(document))
    (tetra,) = [item for item in inspected["objects"] if item["name"] == "Tetra"]
    assert tetra["type_id"] == "Mesh::Feature"
    assert tetra["mesh"]["facets"] == 4
    # Metres become millimetres, and glTF's Y-up becomes FreeCAD's Z-up: +Y goes to +Z.
    box = tetra["mesh"]["bounding_box"]
    assert box["min"] == pytest.approx([0.0, -1000.0, 0.0])
    assert box["max"] == pytest.approx([1000.0, 0.0, 1000.0])
