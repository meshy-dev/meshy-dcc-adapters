# Changelog

## 0.1.0 (unreleased)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter:
  - the Python package is `meshy_dcc_unreal`, the plugin is `MeshyDccUnreal`,
    and environment variables are `MESHY_DCC_UNREAL_*`;
  - the plugin runs on `meshy_dcc_core` 0.2.x.
- The plugin keeps its C++ editor module and ships it as source; the
  installer builds it for each project. It depends on the Python Editor Script
  Plugin and Editor Scripting Utilities.
- `packaging/build_package.py` builds the Meshy DCC package: the plugin, with
  this adapter and `meshy_dcc_core` in its `python/` folder, and a relocatable
  CPython for `bin/meshy-dcc-unreal`, the installer. Nothing is installed into
  the engine. The package leaves out `direct_url.json`, which would record
  local build paths.
- New installer (`meshy-dcc-unreal install | uninstall | status`): copies the
  plugin into `Plugins/MeshyDccUnreal`, builds the module with the engine's
  build script as the editor's rebuild prompt would (exit 20 and a rollback
  when the toolchain cannot), records the start-instance launch plan, the
  build log and a file receipt in `.meshy-dcc/`, and leaves the `.uproject`
  alone. The engine comes from `--engine`, `MESHY_DCC_UNREAL_ENGINE` or the
  project's `EngineAssociation` in the Epic Games Launcher's install list.
  Repair, upgrade and uninstall touch only receipted files and refuse while
  the plugin folder holds anything else, apart from build output and
  `__pycache__`. It replaces the upstream installer, which installed wheels
  into the engine's Python.
- The startup script no longer adds a project's `src/` or a sibling
  `meshy-dcc-core` checkout to the editor's `sys.path`.
- The startup script registers itself as `meshy_dcc_unreal_init`. Unreal runs
  `init_unreal.py` rather than importing it, so `import init_unreal` (the
  menu commands, `mcp_self_check`) ran the file again: a second tick callback
  and server start, and from `mcp_self_check`'s worker thread an engine
  assertion that crashed the editor. `mcp_self_check` also reads the engine's
  identity on the editor thread now.
- An editor launched by `meshy-dcc start-instance` advertises a safe stop.
  Unreal quits without asking to save, so the stop refuses while any map or
  asset of the project is unsaved, or when the editor cannot tell, unless the
  request carries `discard_unsaved`. Engine content that gets dirty on its own
  does not count.
- `unreal-level` `save_level` with `save_all_dirty` no longer saves engine
  packages, and `create_level` takes `template_path` to copy a level such as
  `/Engine/Maps/Templates/Template_Default`.
- The registry row reports the adapter version as the server version.
- `meshy-unreal` skill: session with the open level and unsaved packages;
  GLB, glTF and FBX import into `/Game/Meshy/<name>`, with Meshy's FBX texture
  set turned into one PBR material; placement through undo with the model's
  base at the given location; mesh, material and texture readback (role,
  sRGB, compression, green-channel flip, Nanite); and a scene-capture render
  that works with the editor in the background.
