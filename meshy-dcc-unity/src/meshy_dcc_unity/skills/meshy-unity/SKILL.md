---
name: meshy-unity
description: >-
  Domain skill — Hand Meshy models to Unity: import and instantiate local FBX
  or OBJ files under Assets, map a keyed PBR texture set to one Standard or
  URP Lit material, read back objects and renderer materials, and save or open
  scenes. Use session to check the Editor before and after.
license: MIT
compatibility: "Unity 2018.4.25f1+ (.NET 4.x); meshy-dcc-core 0.2.x"
allowed-tools: "python"
metadata:
  meshy-dcc:
    dcc: unity
    layer: domain
    version: "0.1.0"
    search-hint: "Unity import FBX OBJ model Meshy material texture PBR instantiate renderer save scene"
    tags: "unity,meshy,import,fbx,obj,material,pbr,handoff"
    tools: tools.yaml
    depends: "dcc-diagnostics"
---

# Meshy Unity handoff

Use `session` to confirm the Editor PID, project, unsaved scenes and
source-write policy. Its focus, pause, background and frame-count fields are
diagnostics only.

Model paths must be below `Assets/`. `inspect_model` proves Unity loaded mesh
data; `instantiate_model` also creates an undoable scene object. Read that
object back with `inspect_object` and the returned `instance_id`. Instance IDs
are session-scoped: rediscover them after a reload or restart. These operations
require idle Edit Mode. GLB needs conversion to FBX or OBJ outside Unity.

A keyed FBX texture set (`material_textures`, with each file's byte count and
SHA-256) maps to one material: Standard in the Built-in pipeline, Lit in the
Universal Render Pipeline. Metallic goes to red and inverted roughness to alpha
of one packed map. The tool does not install URP or switch pipelines; other
pipelines are unsupported. Model-only imports report `geometry_only`.

`inspect_renderers` is read-only. It scans the active loaded scene, including
inactive objects, and reports missing materials, shader errors and
Standard/URP Lit pipeline mismatches. Pass `max_material_slots` after a save
and reopen to read texture bindings. Bindings are not visual proof; check a
Game View image before claiming the appearance is right.

`save_scene_as` saves only the active scene to a `.unity` path below `Assets/`
and refuses to overwrite another scene. `open_scene` refuses while any open
scene is dirty.

Never repeat a mutation whose outcome is unknown; repeat only read-only checks.
To close an Editor that `meshy-dcc start-instance` launched, use
`meshy-dcc stop-instance`. It refuses while scenes are unsaved unless the user
agreed to discard them (`--discard-unsaved`).
