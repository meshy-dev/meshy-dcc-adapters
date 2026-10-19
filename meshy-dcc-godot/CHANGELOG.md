# Changelog

## 0.1.0 (unreleased)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter:
  - the Python package is `meshy_dcc_godot`, the addon is
    `addons/meshy_dcc_godot`, and environment variables are
    `MESHY_DCC_GODOT_*`;
  - the sidecar runs on `meshy_dcc_core` 0.2.x;
  - the editor bridge defaults to port 13847.
- `install --python` accepts a venv interpreter; it no longer follows the
  symlink out of the venv. Godot 4.4 is the minimum, matching the skills.
- `packaging/build_package.py` builds the Meshy DCC package: a relocatable
  CPython with `meshy_dcc_core`, this adapter and `websockets`, plus
  `bin/meshy-dcc-godot-sidecar`. Godot needs no Python of its own.
- `install --sidecar <path>` records the project's start-instance launch plan
  and the sidecar in `.meshy-dcc/`, which ignores itself for version control.
  `--files-only` reports success without the live readiness check.
  `uninstall` removes both files. Godot is found through `--dcc-path`,
  `MESHY_DCC_GODOT_EXECUTABLE`, `PATH` or the macOS app bundle.
- Installing the same version again over a valid install leaves the addon in
  place.
- Every capability tool declares the parameters the editor or the running
  game reads for it, which of them are required, the defaults the host
  applies, and rejects any others. The tools of a skill used to share one
  schema listing every parameter of the category and accepting any other, so a
  tool did not say what it needed. `get_runtime_status` and
  `get_game_node_properties` still take the shared runtime schema.
- Arguments the open schemas let through are now refused: `setup_camera_3d`,
  `setup_lighting`, `set_material_3d`, `setup_physics_body` and
  `set_particle_material` take property values under `properties` only, not
  as top-level keys, and the fallback names `name` (for `animation` or
  `state`), `pattern` and `reference` (for `query`) and `path` (for an
  animation track's `property_path`) are gone.
- Repair and upgrade delete the previous addon copy once it is proven to hold
  nothing the project needs: the copy is unchanged since staging, and each of
  its files was owned by the old receipt or sits byte-identical in the new
  addon. Before, every repair or upgrade left the copy as a pending backup,
  and every later install stopped at exit 50 until someone removed it. A copy
  that fails the check (say, the new version replaced a user's file at one of
  its paths) is still kept, and the report says to empty and delete it.
- The EditorPlugin starts the recorded sidecar on a free bridge port per
  editor; `serve --watch-pid` makes the sidecar exit with the editor.
- `meshy-godot` skill: session with unsaved scenes and scripts, GLB scan and
  import readiness, instance through undo/redo, mesh and PBR readback.
- An editor launched by `meshy-dcc start-instance` advertises a safe stop. It
  exits when nothing is unsaved and refuses otherwise, unless the request
  carries `discard_unsaved`; an editor that cannot report unsaved state counts
  as unsaved.
- Vector properties also take `{"x": .., "y": .., "z": ..}`; that form was
  accepted and silently left the property unchanged. `update_property`
  returns the value read back from the node.
