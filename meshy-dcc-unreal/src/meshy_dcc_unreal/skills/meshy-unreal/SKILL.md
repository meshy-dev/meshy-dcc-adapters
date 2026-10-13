---
name: meshy-unreal
description: >-
  Domain skill — Hand Meshy models to the Unreal Editor: import a GLB or FBX
  from disk into /Game/Meshy/<name>, place it in the open level through undo,
  read back meshes, materials and textures, and render a capture. Use
  session to check the editor, the open level and unsaved maps and assets
  before and after.
license: MIT
compatibility: "Unreal Engine 5.0+; meshy-dcc-core 0.2.x"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: unreal
    layer: domain
    version: "0.1.0"
    search-hint: "Unreal import GLB FBX model Meshy material texture PBR place level readback screenshot"
    tags: "unreal,meshy,import,glb,fbx,material,pbr,handoff"
    tools: tools.yaml
---

# Meshy Unreal handoff

Use `session` to confirm the editor PID, project, open level and unsaved maps
and assets. `dirty` is `null` when Unreal cannot report unsaved state; treat
that as unsaved. `engine_unsaved` lists engine content that got dirty on its
own (a material gaining a usage flag); it is not the user's work, it does not
count as unsaved, and it must never be saved.

1. If `session` reports `level_in_project: false` (the editor opened an engine
   template map), create a project level with `unreal-level` `create_level`,
   for example `{"level_path": "/Game/Maps/Handoff", "template_path":
   "/Engine/Maps/Templates/Template_Default"}` for sky, lights and a floor.
   Never save over an engine map.
2. Download the model with `meshy` and keep it on disk. A GLB carries its
   textures. For an FBX, keep Meshy's PNGs next to it: `<name>.png`,
   `<name>_normal.png`, `<name>_metallic.png`, `<name>_roughness.png`.
3. `import_model` with `source_path` and a `name` imports into
   `/Game/Meshy/<name>` and saves those assets. A GLB keeps Unreal's glTF PBR
   material. For an FBX, the texture set (found by name, or passed as
   `textures`) becomes one PBR material `M_<name>` on every slot, because
   Unreal's FBX material would read roughness as shininess. The model is
   placed with its base at `location` (default the world origin). The tool
   refuses a folder that already holds assets. Never repeat it when the
   outcome is unknown; inspect instead.
4. `inspect_model` with `actor` set to that name reads back vertices,
   triangles, bounds, material slots and, per texture, the role it feeds, its
   sRGB, compression and green-channel flip. Unreal may build Nanite for a
   dense Meshy mesh (`nanite: true`); after the editor reloads it, vertex and
   triangle counts are the fallback mesh's, not the source's.
5. `capture_model` with the actor and a `file_name` renders
   `<project>/Saved/MeshyDcc/<file_name>.png`, also while the editor is in the
   background. Imported Meshy models face +Y, and the views are relative to
   that: `front` looks at the face, `three_quarter` from the front left.
   Bindings are not visual proof; look at the capture before claiming the
   appearance is right.
6. Save the level with `unreal-level` `save_level` only when asked, then check
   that `session` reports `dirty: false`.

To close an editor that `meshy-dcc start-instance` launched, use
`meshy-dcc stop-instance`. Unreal would quit without asking to save, so the
stop refuses while any map or asset of the project is unsaved, or when the
editor cannot tell, unless the user agreed to discard it (`--discard-unsaved`).
