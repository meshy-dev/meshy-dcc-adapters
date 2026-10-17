import base64
import io
import json
import struct
from array import array

import pytest
from PIL import Image

from meshy_dcc_roblox import meshy_import

QUAD = {
    "positions": [(0, 0, 0), (1, 0, 0), (1, 2, 0), (0, 2, 0)],
    "normals": [(0, 0, 1)] * 4,
    "uvs": [(0, 0), (1, 0), (1, 1), (0, 1)],
    "indices": [0, 1, 2, 0, 2, 3],
}


def make_glb(path, mesh=QUAD, node=None, image=None, extensions=()):
    """Write a one-primitive GLB; ``image`` is a PIL image used for every texture."""
    binary = bytearray()
    views, accessors = [], []

    def add(values, fmt, component, kind, count):
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(values) * 4})
        binary.extend(struct.pack(f"<{len(values)}{fmt}", *values))
        accessors.append({"bufferView": len(views) - 1, "componentType": component, "type": kind, "count": count})
        return len(accessors) - 1

    count = len(mesh["positions"])
    attributes = {
        "POSITION": add([c for p in mesh["positions"] for c in p], "f", 5126, "VEC3", count),
        "NORMAL": add([c for n in mesh["normals"] for c in n], "f", 5126, "VEC3", count),
        "TEXCOORD_0": add([c for uv in mesh["uvs"] for c in uv], "f", 5126, "VEC2", count),
    }
    primitive = {"attributes": attributes, "indices": add(mesh["indices"], "I", 5125, "SCALAR", len(mesh["indices"])), "material": 0}
    doc = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, **(node or {})}],
        "meshes": [{"primitives": [primitive]}],
        "materials": [{"pbrMetallicRoughness": {}, "doubleSided": True}],
        "extensionsUsed": list(extensions),
    }
    if image is not None:
        png = io.BytesIO()
        image.save(png, "PNG")
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(png.getvalue())})
        binary.extend(png.getvalue())
        doc["images"] = [{"bufferView": len(views) - 1, "mimeType": "image/png"}]
        doc["textures"] = [{"source": 0}]
        doc["materials"][0] = {
            "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicRoughnessTexture": {"index": 0}},
            "normalTexture": {"index": 0},
        }
    while len(binary) % 4:
        binary.append(0)
    doc["bufferViews"] = views
    doc["accessors"] = accessors
    doc["buffers"] = [{"byteLength": len(binary)}]
    text = json.dumps(doc).encode()
    text += b" " * (-len(text) % 4)
    body = struct.pack("<I4s", len(text), b"JSON") + text + struct.pack("<I4s", len(binary), b"BIN\0") + bytes(binary)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
    return path


def floats(payload, key):
    return array("f", base64.b64decode(payload["blobs"][key])).tolist()


def test_quad_becomes_one_centred_chunk_in_studs(tmp_path):
    payload = meshy_import.prepare(make_glb(tmp_path / "quad.glb"), scale=10)
    (chunk,) = payload["meta"]["chunks"]
    assert (chunk["vertex_count"], chunk["triangle_count"]) == (4, 2)
    assert chunk["center"] == [5, 10, 0]
    assert floats(payload, chunk["positions"])[:6] == [-5, -10, 0, 5, -10, 0]
    assert array("I", base64.b64decode(payload["blobs"][chunk["indices"]])).tolist() == [0, 1, 2, 0, 2, 3]
    assert floats(payload, chunk["uvs"]) == [0, 0, 1, 0, 1, 1, 0, 1]
    assert payload["meta"]["double_sided"] is True
    assert payload["source"]["size_studs"] == [10, 20, 0]


def test_node_transform_and_mirroring_are_applied(tmp_path):
    glb = make_glb(tmp_path / "moved.glb", node={"translation": [1, 0, 0], "scale": [-1, 1, 1]})
    payload = meshy_import.prepare(glb, scale=1, flip_v=True)
    (chunk,) = payload["meta"]["chunks"]
    assert chunk["center"] == [0.5, 1, 0]
    # A mirroring transform flips the winding (source triangle 0,1,2 becomes 0,2,1)
    # so faces still point outwards; local vertex 1 is source vertex 2 at (0, 2, 0).
    assert array("I", base64.b64decode(payload["blobs"][chunk["indices"]])).tolist() == [0, 1, 2, 0, 3, 1]
    assert floats(payload, chunk["positions"])[3:6] == [-0.5, 1, 0]
    assert floats(payload, chunk["normals"])[:3] == [0, 0, 1]
    assert floats(payload, chunk["uvs"])[:2] == [0, 1]


def test_large_meshes_split_within_editable_mesh_limits(tmp_path, monkeypatch):
    monkeypatch.setattr(meshy_import, "MAX_TRIANGLES", 1)
    payload = meshy_import.prepare(make_glb(tmp_path / "quad.glb"), scale=1)
    chunks = payload["meta"]["chunks"]
    assert [(c["vertex_count"], c["triangle_count"]) for c in chunks] == [(3, 1), (3, 1)]
    second = floats(payload, chunks[1]["positions"])
    centre = chunks[1]["center"]
    # Chunk 2 holds source vertices 0, 2, 3, re-indexed from zero.
    assert [second[i] + centre[i % 3] for i in range(9)] == [0, 0, 0, 1, 2, 0, 0, 2, 0]


def test_textures_become_rgba_maps_within_the_size_limit(tmp_path):
    image = Image.new("RGB", (64, 32), (10, 200, 30))
    payload = meshy_import.prepare(make_glb(tmp_path / "tex.glb", image=image), max_texture=16)
    textures = payload["meta"]["textures"]
    assert sorted(textures) == ["color", "metalness", "normal", "roughness"]
    assert (textures["color"]["width"], textures["color"]["height"]) == (16, 8)
    rough = base64.b64decode(payload["blobs"][textures["roughness"]["key"]])
    metal = base64.b64decode(payload["blobs"][textures["metalness"]["key"]])
    assert len(rough) == 16 * 8 * 4
    assert rough[:4] == bytes([200, 200, 200, 255])  # glTF roughness is green
    assert metal[:4] == bytes([30, 30, 30, 255])  # metalness is blue


def test_compressed_glb_is_refused(tmp_path):
    glb = make_glb(tmp_path / "draco.glb", extensions=["KHR_draco_mesh_compression"])
    with pytest.raises(ValueError, match="draco"):
        meshy_import.prepare(glb)


def test_send_stages_pieces_then_finishes_once(tmp_path, monkeypatch):
    monkeypatch.setattr(meshy_import, "PIECE_CHARS", 8)
    payload = meshy_import.prepare(make_glb(tmp_path / "quad.glb"))
    calls = []

    def call_host(method, params):
        calls.append((method, params))
        return {"path": "Workspace/Quad"} if method == "meshy.import_finish" else {}

    result = meshy_import.send(call_host, payload, {"name": "Quad", "parent": "Workspace", "publish": False})
    methods = [method for method, _ in calls]
    assert methods[0] == "meshy.import_begin" and methods[-1] == "meshy.import_finish"
    assert methods.count("meshy.import_finish") == 1
    staged = {}
    for method, params in calls:
        if method == "meshy.import_data":
            staged.setdefault(params["key"], []).append((params["index"], params["data"]))
    for key, pieces in staged.items():
        assert [index for index, _ in pieces] == list(range(1, len(pieces) + 1))
        assert "".join(data for _, data in pieces) == payload["blobs"][key]
    assert calls[-1][1]["meta"]["name"] == "Quad"
    assert result["path"] == "Workspace/Quad" and result["source"]["triangles"] == 2
