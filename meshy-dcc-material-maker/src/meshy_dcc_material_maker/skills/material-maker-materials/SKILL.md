---
name: material-maker-materials
description: >-
  Build and edit Material Maker procedural material graphs (.ptex) in a
  project folder, then render them through Material Maker into PBR texture
  sets (albedo, normal, roughness/metallic/AO, height) and engine materials
  for Blender, Godot, Unity, Unreal or glTF. Use it to make tileable
  materials for Meshy models. It edits the files, not the visible editor.
license: MIT
compatibility: "Python 3.9+; Material Maker 1.7.0+; meshy-dcc-core>=0.2.0,<0.3.0"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: material-maker
    layer: domain
    version: "0.1.0"
    search-hint: "Material Maker PTEX procedural material graph texture PBR export albedo normal roughness Blender Godot Unity Unreal Meshy"
    tags: [material-maker, ptex, procedural-materials, textures, pbr, export]
    tools: tools.yaml
---

# Material Maker Materials

Each instance serves one project folder. Paths are relative to it, and no
tool reads or writes outside it. Material Maker itself only runs to render an
export; graphs are edited as files.

1. `get_status` lists the example materials, the export targets and the
   Material Maker in use.
2. `create_material` starts a new `.ptex`: `blank` (only the Material output
   node), a Material Maker example (`bricks`, `rusted_metal`, `wood`, ...), or a
   copy of another graph in the project.
3. `list_node_types` finds node types (`query: "noise"`) and gives one type's
   inputs, outputs and parameters (`node_type: "perlin"`).
4. `edit_graph` adds, removes and connects nodes and sets parameters, all or
   nothing, and saves the file. Pass the `sha256` from `get_graph` as
   `expected_sha256`. Material inputs: 0 albedo, 1 metallic, 2 roughness,
   3 emission, 4 normal, 5 ambient occlusion, 6 height, 7 opacity, 8 subsurface.
5. `get_graph` reads the nodes, parameters and connections back.
6. `export_material` renders into a new folder and reads back each file's size,
   SHA-256 and PNG dimensions. Look at the albedo PNG to judge the result.

An `image` node (`parameters: {"image": "textures/base.png"}`) brings a texture
from the project into the graph, for example a Meshy model's base color to
derive a normal or height map from.

Every edit is saved at once, so there is no unsaved state. Material Maker does
not reload a file changed on disk: if the user has the same `.ptex` open in
Material Maker, ask them to close it first, or their next save overwrites the
edit.
