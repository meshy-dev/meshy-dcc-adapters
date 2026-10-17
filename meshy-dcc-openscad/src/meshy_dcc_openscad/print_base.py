"""Stand a Meshy STL on a printable base: a new parametric ``.scad`` that imports it.

The mesh is measured here (OpenSCAD cannot report an imported mesh's bounds),
and the measured bounds are written into the source so the model can be scaled
to a target height, centred, and set on a round or square plate. Every value
is a top-level variable, so ``export_model`` and ``render_preview`` can change
it with ``parameters`` without rewriting the file.
"""

from __future__ import annotations

import json
import math
import os
import struct
from pathlib import Path

from .bridge import _within, get_bridge
from .source_authoring import write_model_source

UP_AXES = ("z", "y")
BASE_SHAPES = ("round", "square", "none")

_SOURCE = """\
// Meshy model on a print base, written by meshy_openscad__write_print_base.
// Change the values below, or pass them as export_model / render_preview parameters.
mesh_file = {mesh_file};
target_height = {target_height}; // model height in mm; 0 keeps the mesh's own size
up_axis = {up_axis}; // "y" stands a Y-up mesh (glTF convention) upright
base_shape = {base_shape}; // "round", "square" or "none"
base_height = {base_height};
base_margin = {base_margin};
sink = {sink}; // how far the model sinks into the base, in mm

// Mesh bounds measured when this file was written: as stored (Z up) and stood up from Y up.
z_up_min = {z_up_min};
z_up_max = {z_up_max};
y_up_min = {y_up_min};
y_up_max = {y_up_max};
mesh_min = up_axis == "y" ? y_up_min : z_up_min;
mesh_max = up_axis == "y" ? y_up_max : z_up_max;

mesh_size = mesh_max - mesh_min;
s = target_height > 0 ? target_height / mesh_size[2] : 1;
footprint = [mesh_size[0] * s, mesh_size[1] * s];
lift = base_shape == "none" ? 0 : base_height - sink;

module model() {{
  translate([0, 0, lift])
    scale(s)
      translate([-(mesh_min[0] + mesh_max[0]) / 2, -(mesh_min[1] + mesh_max[1]) / 2, -mesh_min[2]])
        rotate(up_axis == "y" ? [90, 0, 0] : [0, 0, 0])
          import(mesh_file);
}}

module base() {{
  if (base_shape == "round")
    cylinder(h = base_height, r = norm(footprint) / 2 + base_margin, $fn = 96);
  else if (base_shape == "square")
    translate([-footprint[0] / 2 - base_margin, -footprint[1] / 2 - base_margin, 0])
      cube([footprint[0] + 2 * base_margin, footprint[1] + 2 * base_margin, base_height]);
}}

union() {{
  model();
  base();
}}
"""


def stl_bounds(path: Path) -> "tuple[list[float], list[float]]":
    """Min and max corner of an STL's vertices (binary or ASCII)."""
    data = path.read_bytes()
    points = []
    if len(data) >= 84:
        (count,) = struct.unpack_from("<I", data, 80)
        if len(data) == 84 + 50 * count:
            for record in struct.iter_unpack("<12x9f2x", memoryview(data)[84:]):
                points.extend((record[0:3], record[3:6], record[6:9]))
    if not points:
        for line in data.decode("ascii", "replace").splitlines():
            fields = line.split()
            if len(fields) == 4 and fields[0].lower() == "vertex":
                points.append(tuple(float(value) for value in fields[1:]))
    if not points or not all(math.isfinite(value) for point in points for value in point):
        raise ValueError("%s has no readable STL vertices" % path.name)
    low = [min(point[axis] for point in points) for axis in range(3)]
    high = [max(point[axis] for point in points) for axis in range(3)]
    return low, high


def _y_up(low: list, high: list) -> "tuple[list[float], list[float]]":
    # rotate([90, 0, 0]) maps (x, y, z) to (x, -z, y).
    return [low[0], -high[2], low[1]], [high[0], -low[2], high[1]]


def _vector(values: list) -> str:
    return json.dumps([round(value, 6) + 0.0 for value in values])  # no -0.0


def _number(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("%s must be a finite number of 0 or more" % name)
    return value


def write_print_base(
    output_path: str,
    mesh_path: str,
    target_height: float = 0,
    up_axis: str = "z",
    base_shape: str = "round",
    base_height: float = 3,
    base_margin: float = 4,
    sink: float = 0.5,
) -> dict:
    if up_axis not in UP_AXES:
        raise ValueError("up_axis must be one of %s" % ", ".join(UP_AXES))
    if base_shape not in BASE_SHAPES:
        raise ValueError("base_shape must be one of %s" % ", ".join(BASE_SHAPES))
    numbers = {
        "target_height": _number("target_height", target_height),
        "base_height": _number("base_height", base_height),
        "base_margin": _number("base_margin", base_margin),
        "sink": _number("sink", sink),
    }
    if numbers["sink"] > numbers["base_height"]:
        raise ValueError("sink must not exceed base_height")
    mesh = Path(mesh_path).expanduser()
    if not mesh.is_absolute() or mesh.suffix.lower() != ".stl":
        raise ValueError("mesh_path must be an absolute .stl path")
    mesh = mesh.resolve()
    if not mesh.is_file() or not _within(mesh, get_bridge().allowed_roots):
        raise ValueError("mesh_path must be an existing file inside the workspace roots")
    z_up = stl_bounds(mesh)
    y_up = _y_up(*z_up)
    low, high = y_up if up_axis == "y" else z_up
    if high[2] - low[2] <= 0:
        raise ValueError("the mesh has no height along the up axis")
    output = Path(output_path).expanduser()
    try:
        reference = os.path.relpath(str(mesh), str(output.parent.resolve()))
    except ValueError:  # another Windows drive
        reference = str(mesh)
    source = _SOURCE.format(
        mesh_file=json.dumps(reference.replace(os.sep, "/")),
        up_axis=json.dumps(up_axis),
        base_shape=json.dumps(base_shape),
        z_up_min=_vector(z_up[0]),
        z_up_max=_vector(z_up[1]),
        y_up_min=_vector(y_up[0]),
        y_up_max=_vector(y_up[1]),
        **{name: repr(value) for name, value in numbers.items()},
    )
    result = write_model_source(output_path, source, self_contained=False)
    size = [high[axis] - low[axis] for axis in range(3)]
    scale = numbers["target_height"] / size[2] if numbers["target_height"] else 1.0
    result.update(
        mesh_path=str(mesh),
        mesh_reference=reference.replace(os.sep, "/"),
        mesh_min=low,
        mesh_max=high,
        scale=scale,
        model_size=[value * scale for value in size],
        parameters=dict(numbers, up_axis=up_axis, base_shape=base_shape),
    )
    return result
