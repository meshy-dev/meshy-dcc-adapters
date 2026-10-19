---
name: material-maker-materials
description: >-
  Build and edit Material Maker procedural material graphs (.ptex) in a
  project folder, then render them through Material Maker into PBR texture
  sets (albedo, normal, roughness/metallic/AO, height) and engine materials
  for Blender, Godot, Unity, Unreal or glTF. Use it to make tileable
  materials for Meshy models. It edits the files, not an open Material Maker
  window: before editing a graph, ask whether it is open in Material Maker
  and have the user close it; open_in_material_maker shows the result.
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
tool reads or writes outside it. Graphs are edited as files; Material Maker
itself only runs to render an export, or when `open_in_material_maker` shows a
graph to the user.

**A Material Maker window does not see these edits.** It does not reload a
file changed on disk, and saving there overwrites the file. So:

- Before changing a graph, ask the user whether it is open in Material Maker.
  If it is, ask them to close it (saving what they want to keep) and wait.
- Never edit a graph the user is still editing.
- After editing and exporting, `open_in_material_maker` opens the graph in a
  new Material Maker window for the user. To change it again, ask them to
  close that window first, then open it again when done.

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
7. `open_in_material_maker` opens the graph in Material Maker for the user and
   returns at once; the window is theirs and stays open after the instance stops.

An `image` node (`parameters: {"image": "textures/base.png"}`) brings a texture
from the project into the graph, for example a Meshy model's base color to
derive a normal or height map from.

Every edit is saved at once, so the instance never has unsaved work.
