# Changelog

## 0.1.0 (2026-10-19)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter: the Python package is `meshy_dcc_material_maker`, the
  dcc type is `material-maker`, environment variables are
  `MESHY_DCC_MATERIAL_MAKER_*`, and it runs on `meshy_dcc_core` 0.2.x.
- `packaging/build_package.py --platform {macos-arm64,windows-x64}` builds the
  Meshy DCC package: CPython 3.11.15 (python-build-standalone 20260504,
  digest-checked) with `meshy_dcc_core` and this adapter, plus
  `bin/meshy-dcc-material-maker-sidecar` (`.cmd` on Windows), which runs
  Python isolated (`-I`) so nothing in the project folder is imported.
- `install-project <folder>` records the folder's start-instance launch plan,
  the Material Maker executable and a receipt in `.meshy-dcc/`; it refuses
  files another adapter wrote. `uninstall-project` removes only unchanged
  files. `serve --project <folder>` binds the tools to the folder; relative
  paths resolve against it and nothing outside it is read or written.
- New tools: `create_material` (blank, a Material Maker example, or a copy),
  `get_graph`, `edit_graph` (add, remove, connect, disconnect nodes and set
  parameters, all or nothing, checked against Material Maker's node library,
  with `expected_sha256`), `list_node_types`. `image` nodes take project
  images, so a Meshy texture can feed a graph.
- Export runs Material Maker without `--headless`, which crashes Material
  Maker 1.7 on macOS. Success needs Material Maker's `Done` and real files;
  Godot's exit messages no longer fail an export, and other engine errors are
  returned as `warnings`. Targets are Material Maker's export profiles
  (`Godot/Godot 4 Standard`, `Unity/URP`, ...; `Blender`, `GLTF`, `Godot`,
  `Unity`, `Unreal` as short names), checked against the material's own
  definition; profiles that write to the clipboard (`Unreal/Unreal Engine 5`)
  are refused. Export folders are created inside the project, and PNG
  dimensions are read back.
- Graphs with `webcam` or `website:` nodes, or export nodes writing outside
  the export folder, fail validation.
- `get_status` reports the project, Material Maker's version (from the macOS
  bundle), examples, node type count and export targets; Material Maker is
  also found as `Material Maker.app` in `/Applications` or `~/Applications`
  and in the Steam folder on Windows.
- Every tool is synchronous. The skill is no longer preloaded at startup:
  agents load it with `load-skill`.
- `open_in_material_maker` opens a project graph in Material Maker's window
  for the user: a separate process that returns at once, outlives the
  instance and never touches a Material Maker the user already has open. A
  Material Maker window does not reload a graph changed on disk, so the skill
  now has agents ask whether a graph is open there (and have the user close
  it) before editing it, and never edit a graph the user is editing.
- An instance launched by `meshy-dcc start-instance` advertises a safe stop.
  Edits are saved as they are made, so it always stops.
