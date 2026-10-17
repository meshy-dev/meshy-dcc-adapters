---
name: meshy-openscad
description: >-
  Domain skill — Stand a Meshy-generated STL on a printable base in OpenSCAD:
  write a new parametric .scad that imports the mesh, scales it to a target
  height in mm, centres it and sets it on a round or square plate, then export
  the print-ready STL and a PNG preview with openscad-pipeline.
license: MIT
compatibility: "Python 3.8+; OpenSCAD 2021.01.x, 2026.09.x or 2026.10.x; meshy-dcc-core 0.2.0+"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: openscad
    layer: domain
    version: "0.1.0"
    tags: [openscad, meshy, 3d-printing, stl, base, import]
    search-hint: >-
      Meshy STL 3D print base stand pedestal plate import mesh scale height
      millimetres OpenSCAD union printable
    tools: tools.yaml
---

# Meshy model on a print base

1. Get the model as STL (Meshy's 3D-print download, or `meshy-cli` with STL
   output) and copy it into the instance's project directory: every path must
   be inside the workspace roots (`get_status` lists them).
2. `write_print_base` writes a **new** `.scad` (it never replaces a file). It
   measures the mesh and writes its bounds into the source, so OpenSCAD can
   scale the model to `target_height` mm, centre it and stand it on the base.
   Meshy's GLB-derived meshes are often Y-up; pass `up_axis: "y"` when the
   model lies on its back in the preview.
3. Export with `openscad-pipeline` `export_model` (`.stl` or `.3mf`) and look at
   it with `render_preview`. Imported scans are rarely clean 2-manifolds, so
   pass `strict: false` when OpenSCAD only warns.
4. To change the size or base, pass `parameters` to `export_model` /
   `render_preview` (`target_height`, `base_shape`, `base_height`,
   `base_margin`, `sink`, `up_axis`) instead of writing another file.
