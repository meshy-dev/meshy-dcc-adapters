---
name: meshy-maya
description: |-
  Pipeline stage — hand Meshy models to Maya. Import a Meshy FBX or OBJ from
  disk under a new group, rebuild its PBR material as a standardSurface from
  Meshy's texture set (sRGB colour, Raw data maps, glTF channel order for a
  packed metallic-roughness map), and read back meshes, bounds, materials and
  texture colour spaces.
license: MIT
compatibility: "Maya 2025 and 2026; meshy-dcc-core 0.2.x"
allowed-tools: Bash Read
metadata:
  meshy-dcc:
    dcc: maya
    layer: domain
    stage: pipeline
    version: 0.1.0
    tags:
    - maya
    - meshy
    - import
    - fbx
    - material
    - pbr
    search-hint: |-
      import Meshy model, Meshy FBX, PBR material, standardSurface texture
      set, base color normal metallic roughness, color space Raw sRGB,
      read back imported model, handoff
    tools: tools.yaml
    groups: groups.yaml
---
# meshy-maya (Pipeline stage)

Not verified on a real Maya yet: the tools are covered by unit tests with a
stand-in `maya.cmds` only.

1. Check the scene first with `maya-scene` `get_session_info`
   (`scene_file`, `scene_modified`).
2. Download the model with `meshy` as FBX and keep it on disk. Maya has no
   built-in glTF importer. Keep Meshy's maps next to the FBX:
   `<name>.png`, `<name>_normal.png`, `<name>_metallic.png`,
   `<name>_roughness.png`, and `<name>_emission.png` when there is one
   (`.jpg` works too), or pass them as `textures`. The material points at
   these files where they are; do not delete them.
3. `import_model` with `source_path` and a `name` imports the file, puts
   everything it added under a new group `name`, and, when there are maps,
   builds one `standardSurface` `<name>_mat` and assigns it to every
   imported mesh. It refuses a name that already exists. The whole import
   is one undo step. Never repeat it when the outcome is unknown; use
   `inspect_model` instead.
4. `inspect_model` with `node` set to the group reads back vertex, face and
   triangle counts, world bounds (in the scene's linear unit), and per
   material input the file, whether it exists, its colour space and the
   channel used. Data maps should read `Raw`, colour maps `sRGB`, and a
   packed metallic-roughness map `outColorB` for metalness and `outColorG`
   for roughness.
5. The scene is left unsaved. Save with `maya-scene` `save_scene` only when
   asked, then check that `get_session_info` reports
   `scene_modified: false`.

## Scripts

`scripts/import_model.py` and `scripts/inspect_model.py` call
`meshy_dcc_maya.meshy_import` on Maya's main thread.
