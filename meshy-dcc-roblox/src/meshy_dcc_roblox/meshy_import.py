"""Turn a Meshy GLB into what the Studio plugin builds, and send it over.

Studio cannot import a file from disk without a dialog, so the sidecar reads
the GLB and the plugin rebuilds it with ``EditableMesh`` and
``EditableImage``. Geometry goes in chunks within EditableMesh's limits
(60,000 vertices, 20,000 triangles), each centred on its own bounds; images
are downscaled to EditableImage's 1024 px limit. Positions are converted from
glTF metres to studs. Bulk data travels as base64 pieces small enough for one
WebSocket message each.
"""

from __future__ import annotations

import base64
import io
import json
import struct
import sys
import uuid
from array import array
from pathlib import Path
from typing import Callable, Optional

STUDS_PER_METER = 1 / 0.28
MAX_VERTICES = 60_000
MAX_TRIANGLES = 20_000
MAX_TEXTURE = 1024
PIECE_CHARS = 256 * 1024
MAX_FILE_BYTES = 512 * 2**20
UNSUPPORTED = {"KHR_draco_mesh_compression", "EXT_meshopt_compression", "KHR_mesh_quantization"}
COMPONENT = {5121: "B", 5123: "H", 5125: "I", 5126: "f"}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path: Path) -> tuple:
    if path.suffix.lower() != ".glb" or not path.is_file():
        raise ValueError(f"{path} is not a .glb file")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"{path} is larger than {MAX_FILE_BYTES // 2**20} MB")
    data = path.read_bytes()
    magic, version, _length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2:
        raise ValueError(f"{path} is not a glTF 2.0 binary")
    doc, binary, offset = None, b"", 12
    while offset + 8 <= len(data):
        size, kind = struct.unpack_from("<I4s", data, offset)
        chunk = data[offset + 8 : offset + 8 + size]
        if kind == b"JSON":
            doc = json.loads(chunk)
        elif kind == b"BIN\0":
            binary = chunk
        offset += 8 + size
    if doc is None:
        raise ValueError(f"{path} has no JSON chunk")
    blocked = UNSUPPORTED & set(doc.get("extensionsUsed", []))
    if blocked:
        raise ValueError(f"{path} uses {', '.join(sorted(blocked))}; export it uncompressed")
    return doc, binary


def _view_bytes(doc: dict, binary: bytes, index: int) -> bytes:
    view = doc["bufferViews"][index]
    start = view.get("byteOffset", 0)
    return binary[start : start + view["byteLength"]]


def _accessor(doc: dict, binary: bytes, index: int) -> list:
    acc = doc["accessors"][index]
    if "sparse" in acc or "bufferView" not in acc:
        raise ValueError(f"accessor {index}: sparse or empty accessors are not supported")
    fmt = COMPONENT.get(acc["componentType"])
    width = WIDTH.get(acc["type"])
    if fmt is None or width is None or (acc.get("normalized") and fmt != "f"):
        raise ValueError(f"accessor {index}: unsupported layout {acc['componentType']}/{acc['type']}")
    view = doc["bufferViews"][acc["bufferView"]]
    item = struct.Struct("<" + fmt * width)
    stride = view.get("byteStride") or item.size
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    return [item.unpack_from(binary, start + i * stride) for i in range(acc["count"])]


def _matmul(a: list, b: list) -> list:
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def _local_matrix(node: dict) -> list:
    if "matrix" in node:
        m = node["matrix"]  # column-major
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    tx, ty, tz = node.get("translation", (0, 0, 0))
    x, y, z, w = node.get("rotation", (0, 0, 0, 1))
    sx, sy, sz = node.get("scale", (1, 1, 1))
    rot = [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]
    return [
        [rot[0][0] * sx, rot[0][1] * sy, rot[0][2] * sz, tx],
        [rot[1][0] * sx, rot[1][1] * sy, rot[1][2] * sz, ty],
        [rot[2][0] * sx, rot[2][1] * sy, rot[2][2] * sz, tz],
        [0, 0, 0, 1],
    ]


def _normal_matrix(m: list) -> tuple:
    """Inverse-transpose of the upper 3x3, and whether the transform mirrors."""
    a = [row[:3] for row in m[:3]]
    cof = [
        [
            a[(r + 1) % 3][(c + 1) % 3] * a[(r + 2) % 3][(c + 2) % 3]
            - a[(r + 1) % 3][(c + 2) % 3] * a[(r + 2) % 3][(c + 1) % 3]
            for c in range(3)
        ]
        for r in range(3)
    ]
    det = sum(a[0][c] * cof[0][c] for c in range(3))
    if abs(det) < 1e-12:
        raise ValueError("a node has a degenerate (zero-scale) transform")
    return [[cof[r][c] / det for c in range(3)] for r in range(3)], det < 0


def _mesh_instances(doc: dict) -> list:
    """(mesh index, world matrix) for every mesh node of the default scene."""
    nodes = doc.get("nodes", [])
    scenes = doc.get("scenes")
    roots = scenes[doc.get("scene", 0)].get("nodes", []) if scenes else range(len(nodes))
    identity = [[float(r == c) for c in range(4)] for r in range(4)]
    found, stack = [], [(index, identity) for index in roots]
    while stack:
        index, parent = stack.pop()
        node = nodes[index]
        world = _matmul(parent, _local_matrix(node))
        if "mesh" in node:
            found.append((node["mesh"], world))
        stack.extend((child, world) for child in node.get("children", []))
    return found


def _geometry(doc: dict, binary: bytes, scale: float, flip_v: bool, warnings: list) -> dict:
    positions, normals, uvs, triangles, materials = [], [], [], [], []
    has_normals = has_uvs = True
    for mesh_index, world in _mesh_instances(doc):
        nmat, mirrored = _normal_matrix(world)
        for prim in doc["meshes"][mesh_index]["primitives"]:
            if prim.get("mode", 4) != 4:
                warnings.append(f"mesh {mesh_index}: a non-triangle primitive was skipped")
                continue
            attrs = prim["attributes"]
            base = len(positions)
            for x, y, z in _accessor(doc, binary, attrs["POSITION"]):
                positions.append(tuple(
                    (world[r][0] * x + world[r][1] * y + world[r][2] * z + world[r][3]) * scale
                    for r in range(3)
                ))
            count = len(positions) - base
            if "NORMAL" in attrs:
                for x, y, z in _accessor(doc, binary, attrs["NORMAL"]):
                    n = [nmat[r][0] * x + nmat[r][1] * y + nmat[r][2] * z for r in range(3)]
                    length = sum(v * v for v in n) ** 0.5 or 1.0
                    normals.append(tuple(v / length for v in n))
            else:
                has_normals = False
            if "TEXCOORD_0" in attrs:
                uvs.extend((u, 1 - v if flip_v else v) for u, v in _accessor(doc, binary, attrs["TEXCOORD_0"]))
            else:
                has_uvs = False
            if "indices" in prim:
                flat = [i[0] for i in _accessor(doc, binary, prim["indices"])]
            else:
                flat = list(range(count))
            for t in range(0, len(flat) - 2, 3):
                a, b, c = (base + flat[t], base + flat[t + 1], base + flat[t + 2])
                triangles.append((a, c, b) if mirrored else (a, b, c))
            materials.append(prim.get("material"))
    if not triangles:
        raise ValueError("the GLB has no triangle meshes")
    if len(set(materials)) > 1:
        warnings.append("The GLB has several materials; textures come from the first one.")
    return {
        "positions": positions,
        "normals": normals if has_normals else None,
        "uvs": uvs if has_uvs else None,
        "triangles": triangles,
        "material": materials[0],
    }


def _pack(values: list, code: str) -> str:
    packed = array(code, values)
    if sys.byteorder != "little":
        packed.byteswap()
    return base64.b64encode(packed.tobytes()).decode("ascii")


def _chunks(geometry: dict, blobs: dict) -> list:
    """Split triangles into EditableMesh-sized chunks, each centred on its bounds."""
    groups, remap, indices = [], {}, []
    for tri in geometry["triangles"]:
        new = len({v for v in tri if v not in remap})
        if indices and (len(indices) // 3 >= MAX_TRIANGLES or len(remap) + new > MAX_VERTICES):
            groups.append((remap, indices))
            remap, indices = {}, []
        for v in tri:
            if v not in remap:
                remap[v] = len(remap)
            indices.append(remap[v])
    groups.append((remap, indices))

    chunks = []
    for number, (remap, indices) in enumerate(groups, 1):
        order = list(remap)  # source vertex index, in local order
        points = [geometry["positions"][v] for v in order]
        low = [min(p[i] for p in points) for i in range(3)]
        high = [max(p[i] for p in points) for i in range(3)]
        center = [(low[i] + high[i]) / 2 for i in range(3)]
        key = f"c{number}"
        blobs[f"{key}.positions"] = _pack([p[i] - center[i] for p in points for i in range(3)], "f")
        blobs[f"{key}.indices"] = _pack(indices, "I")
        chunk = {
            "center": center,
            "vertex_count": len(order),
            "triangle_count": len(indices) // 3,
            "positions": f"{key}.positions",
            "indices": f"{key}.indices",
        }
        for name, width in (("normals", 3), ("uvs", 2)):
            source = geometry[name]
            if source is not None:
                blobs[f"{key}.{name}"] = _pack([source[v][i] for v in order for i in range(width)], "f")
                chunk[name] = f"{key}.{name}"
        chunks.append(chunk)
    return chunks


def _textures(doc: dict, binary: bytes, material: Optional[int], max_size: int, blobs: dict, warnings: list) -> dict:
    if material is None:
        return {}
    try:
        from PIL import Image
    except ImportError:
        warnings.append("Textures were skipped: this sidecar has no Pillow to decode them.")
        return {}
    mat = doc["materials"][material]
    pbr = mat.get("pbrMetallicRoughness", {})

    def load(info: dict):
        image = doc["images"][doc["textures"][info["index"]]["source"]]
        if "bufferView" in image:
            data = _view_bytes(doc, binary, image["bufferView"])
        elif image.get("uri", "").startswith("data:"):
            data = base64.b64decode(image["uri"].split(",", 1)[1])
        else:
            raise ValueError(f"texture {image.get('uri')!r} is outside the GLB")
        return Image.open(io.BytesIO(data))

    maps = {}
    try:
        if "baseColorTexture" in pbr:
            maps["color"] = load(pbr["baseColorTexture"]).convert("RGBA")
        if "normalTexture" in mat:
            maps["normal"] = load(mat["normalTexture"]).convert("RGBA")
        if "metallicRoughnessTexture" in pbr:
            # glTF packs roughness in G and metalness in B; Roblox reads one map each (red).
            _r, green, blue = load(pbr["metallicRoughnessTexture"]).convert("RGB").split()
            maps["roughness"] = green.convert("RGBA")
            maps["metalness"] = blue.convert("RGBA")
    except (ValueError, OSError) as exc:
        warnings.append(f"Textures were skipped: {exc}")
        return {}
    textures = {}
    for role, image in maps.items():
        image.thumbnail((max_size, max_size))
        key = f"t.{role}"
        blobs[key] = base64.b64encode(image.tobytes()).decode("ascii")
        textures[role] = {"key": key, "width": image.width, "height": image.height}
    return textures


def prepare(path: Path, scale: float = STUDS_PER_METER, flip_v: bool = False, max_texture: int = MAX_TEXTURE) -> dict:
    """Read a GLB into plugin-ready chunks, images and a summary."""
    doc, binary = read_glb(path)
    warnings: list = []
    geometry = _geometry(doc, binary, scale, flip_v, warnings)
    blobs: dict = {}
    chunks = _chunks(geometry, blobs)
    textures = _textures(doc, binary, geometry["material"], min(max_texture, MAX_TEXTURE), blobs, warnings)
    material = doc["materials"][geometry["material"]] if geometry["material"] is not None else {}
    points = geometry["positions"]
    return {
        "meta": {"chunks": chunks, "textures": textures, "double_sided": bool(material.get("doubleSided"))},
        "blobs": blobs,
        "warnings": warnings,
        "source": {
            "vertices": len(points),
            "triangles": len(geometry["triangles"]),
            "chunks": len(chunks),
            "size_studs": [max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)],
            "textures": sorted(textures),
        },
    }


def send(call_host: Callable[[str, dict], dict], payload: dict, options: dict) -> dict:
    """Stage every blob in the plugin, then have it build the model once."""
    import_id = uuid.uuid4().hex
    call_host("meshy.import_begin", {"import_id": import_id})
    for key, text in payload["blobs"].items():
        pieces = [text[i : i + PIECE_CHARS] for i in range(0, len(text), PIECE_CHARS)] or [""]
        for index, data in enumerate(pieces, 1):
            call_host("meshy.import_data", {"import_id": import_id, "key": key, "index": index, "data": data})
    meta = {**payload["meta"], **options}
    result = call_host("meshy.import_finish", {"import_id": import_id, "meta": meta})
    return {**result, "source": payload["source"], "warnings": payload["warnings"]}
