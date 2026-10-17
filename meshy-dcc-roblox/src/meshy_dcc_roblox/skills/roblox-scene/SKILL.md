---
name: roblox-scene
description: >-
  Domain skill — Read and edit the open Roblox Studio place: the instance tree
  under Workspace and other services, with class, path, position and size;
  create, set properties of, move and delete instances as undoable steps; and,
  only when the user has switched it on in Studio, run Luau. Use session first
  to see which place this instance serves.
license: MIT
compatibility: "Roblox Studio with the Meshy DCC plugin; meshy-dcc-core 0.2.x"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: roblox
    layer: domain
    version: "0.1.0"
    search-hint: "Roblox Studio place Workspace explorer instance part model create move delete property Luau"
    tags: "roblox,studio,scene,instance,luau"
    tools: tools.yaml
---

# Roblox Studio place

Instances are addressed by path: names from the DataModel down, joined with
`/`, such as `Workspace/Castle/Gate`. A path whose step matches two siblings is
refused as ambiguous; rename one of them first. Positions are in studs
(about 0.28 m each), `[x, y, z]` with +Y up.

1. `session` names the place, Studio's version and whether Luau is allowed.
   `dirty` is always `null`: Studio cannot tell a plugin about unsaved changes.
2. `get_scene_tree` lists instances below `root` (default `Workspace`) to
   `depth` levels; `inspect_instance` reads one instance's common properties,
   pivot and attributes.
3. `create_instance` (`class_name`, `parent`, `name`, `properties`),
   `set_properties`, `move_instance` (`position`, optional `rotation` in
   degrees) and `delete_instance` each make one Studio undo step and return a
   readback. Property values are JSON: numbers, strings, booleans, `[x, y, z]`
   for Vector3, `[r, g, b]` (0-1) or `"#rrggbb"` for Color3, and the item name
   for an Enum, such as `"Neon"` for `Material`. A new name must be free among
   its siblings.
4. `execute_luau` runs code in the edit DataModel at plugin level and returns
   what it printed and returned. It is off until the user clicks **Allow
   Luau** in Studio's Meshy DCC toolbar; never ask for it as a workaround for
   a tool that exists. It is one undo step; an error rolls its changes back.

Saving: a plugin cannot save a place. When the work should be kept, ask the
user to save in Studio (File > Save to File, or Publish to Roblox).
