---
name: meshy-godot
description: >-
  Domain skill — Hand Meshy models to Godot: scan a self-contained GLB copied
  below res://assets/meshy/, instance it in the open scene through undo/redo,
  and read back meshes, PBR materials and transforms. Use session to check the
  editor, import readiness and unsaved scenes and scripts before and after.
license: MIT
compatibility: "Godot 4.4+; meshy-dcc-core 0.2.x"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: godot
    layer: domain
    version: "0.1.0"
    search-hint: "Godot import GLB model Meshy material texture PBR instance scene readback"
    tags: "godot,meshy,import,glb,material,pbr,handoff"
    tools: tools.yaml
    depends: "dcc-diagnostics"
---

# Meshy Godot handoff

Use `session` to confirm the editor PID, project, open scene and unsaved
scenes and scripts. `dirty` is `null` when this Godot cannot report unsaved
state; treat that as unsaved.

1. Put one self-contained GLB (textures embedded, as Meshy's GLB download is)
   below `<project>/assets/meshy/`. Godot imports GLB natively; convert other
   formats before copying.
2. Call `prepare_asset` with its `res://assets/meshy/...` path, then poll
   `session` with `asset_path` until `asset_ready` is true. The import runs in
   the background; the scan may report the editor busy, so retry only
   `prepare_asset` calls that returned `scan_started: false`.
3. Open or create a 3D scene with `godot-scene-management` (`create_scene`
   with `root_type: Node3D` and `open: true`, or `open_scene`).
4. `import_model` instances the GLB once in the active scene. It does not
   save. Never repeat it when the outcome is unknown; read the scene instead.
5. `inspect_model` with the node's name (or a path relative to the scene root)
   reads back mesh, surface and vertex counts, PBR material values, texture
   bindings and transforms. With `path` instead, it inspects the imported GLB
   without touching the scene.
6. Save with `godot-scene-management` `save_scene`, then check that `session`
   reports `dirty: false`. Reopen and inspect again before claiming the result
   persisted. Bindings are not visual proof; take an editor screenshot
   (`godot-editor`) before claiming the appearance is right.

Meshy models face +Z; Godot cameras look down −Z, so a default camera sees
the model's back.

To close an editor that `meshy-dcc start-instance` launched, use
`meshy-dcc stop-instance`. It refuses while anything is unsaved, or when the
editor cannot tell, unless the user agreed to discard it
(`--discard-unsaved`).
