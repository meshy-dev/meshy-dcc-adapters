# meshy-dcc-unreal

The Meshy DCC Core adapter for the Unreal Editor. It is a Python-only project
plugin, `MeshyDccUnreal`, that runs on the editor's own Python: it serves the
adapter's tools over MCP and registers the editor with the local `meshy-dcc`
registry. Nothing is compiled and nothing is installed into the engine.

Targets Unreal Engine 5.0 and later. Verified with Unreal Engine 5.7.2 on
macOS arm64: install, `meshy-dcc start-instance`, GLB and FBX import with PBR
readback, save and reopen, a rendered capture, safe stop, repair and
uninstall. On macOS the editor needs Xcode with the Metal toolchain installed
and its license accepted; without them it exits at startup.

## With Meshy DCC

`packaging/build_package.py` builds the Meshy DCC package:

```
plugin/MeshyDccUnreal/     the plugin, with this adapter and meshy_dcc_core in python/
python/                    a relocatable CPython that runs the installer
bin/meshy-dcc-unreal       the installer
```

```bash
meshy-dcc install --dcc-type unreal --project /path/to/project --execute
meshy-dcc start-instance --dcc-type unreal --project /path/to/project --wait-ready --yes
```

The first command extracts the package and runs `bin/meshy-dcc-unreal install
<project> --yes --json`. It copies the plugin to `Plugins/MeshyDccUnreal` and
writes `.meshy-dcc/` next to the `.uproject`: the start-instance launch plan
and a receipt with the SHA-256 of every plugin file (the directory ignores
itself for version control). The `.uproject` is left alone; project plugins
are enabled by default. The engine comes from `--engine`,
`MESHY_DCC_UNREAL_ENGINE`, or the project's `EngineAssociation` looked up in
the Epic Games Launcher's install list.

Repair, upgrade and `uninstall` touch only files the receipt owns. They refuse
while the plugin folder holds anything else, apart from the `__pycache__`
directories the editor writes, and say which files to move out.

An editor launched by `start-instance` advertises a safe stop. Unreal quits
without asking to save, so the stop refuses while any map or asset of the
project is unsaved, or when the editor cannot tell, unless the request
carries `discard_unsaved`. Engine content that gets dirty on its own, such as
a material gaining a usage flag, is not counted and is never saved.

The `meshy-unreal` skill hands Meshy models over: import a GLB or FBX into
`/Game/Meshy/<name>`, turn Meshy's FBX texture set into a PBR material, place
the model in the level through undo, read back meshes, materials and texture
settings, and render a capture of it.

## Not in this build

The upstream plugin also has a C++ editor module, kept under
`unreal/plugin/Source` but not built or shipped: compiling it needs Xcode
within the engine's supported range (Unreal 5.7 accepts up to 26.9). Tools
that need it report that the native bridge is unavailable:

- `unreal-pie` and `unreal-playtest-agent` (Play In Editor input and tests);
- `unreal-chaos` geometry collections;
- `unreal-automation` `list_automation_tests`;
- `unreal-fab-assets`;
- `unreal-level` `focus_level_editor_viewport`;
- `unreal-materials` `set_material_instance_parameters` and
  `connect_material_expression_to_customized_uv`;
- `unreal-niagara` `author_niagara_system`.

## Development

```bash
python -m pip install --no-deps <meshy_dcc_core wheel> -e .
python -m pip install pytest pytest-mock pyyaml "jsonschema>=4.18" packaging
python -m pytest tests
python tools/lint_skills.py
```

Unreal and Unreal Engine are trademarks of Epic Games, Inc. This independent
adapter is not affiliated with or endorsed by Epic Games.

## License

MIT; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
