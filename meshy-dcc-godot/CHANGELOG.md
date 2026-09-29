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
  place instead of parking the previous copy as a pending backup.
- The EditorPlugin starts the recorded sidecar on a free bridge port per
  editor; `serve --watch-pid` makes the sidecar exit with the editor.
- `meshy-godot` skill: session with unsaved scenes and scripts, GLB scan and
  import readiness, instance through undo/redo, mesh and PBR readback.
- An editor launched by `meshy-dcc start-instance` advertises a safe stop. It
  exits when nothing is unsaved and refuses otherwise, unless the request
  carries `discard_unsaved`; an editor that cannot report unsaved state counts
  as unsaved.
