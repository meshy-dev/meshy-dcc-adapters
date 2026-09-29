# meshy-dcc-unreal

The Meshy DCC Core adapter for the Unreal Editor: a project plugin,
`MeshyDccUnreal`, with a C++ editor module and a Python layer that runs on the
editor's own Python. The Python layer serves the adapter's tools over MCP and
registers the editor with the local `meshy-dcc` registry; the C++ module adds
the native bridge some tools need (PIE input, Chaos, Fab, automation tests,
material-instance edits). Nothing is installed into the engine.

Targets Unreal Engine 5.0 and later. Verified with Unreal Engine 5.7.2 on
macOS arm64: install with the module build, `meshy-dcc start-instance`, GLB
and FBX import with PBR readback, save and reopen, a rendered capture, native
tools, safe stop, repair and uninstall. On macOS the editor needs Xcode with
the Metal toolchain installed and its license accepted; without them it exits
at startup.

## With Meshy DCC

`packaging/build_package.py` builds the Meshy DCC package:

```
plugin/MeshyDccUnreal/     the plugin: Source/ (the C++ module), Content/Python/,
                           and this adapter and meshy_dcc_core in python/
python/                    a relocatable CPython that runs the installer
bin/meshy-dcc-unreal       the installer
```

```bash
meshy-dcc install --dcc-type unreal --project /path/to/project --execute
meshy-dcc start-instance --dcc-type unreal --project /path/to/project --wait-ready --yes
```

The first command extracts the package and runs `bin/meshy-dcc-unreal install
<project> --yes --json`. It copies the plugin to `Plugins/MeshyDccUnreal`,
builds the C++ module for the project with the engine's build script (the
same build the editor runs when it offers to rebuild missing modules), and
writes `.meshy-dcc/` next to the `.uproject`: the start-instance launch plan,
`build.log`, and a receipt with the SHA-256 of every plugin file (the
directory ignores itself for version control). The `.uproject` is left alone;
project plugins are enabled by default. The engine comes from `--engine`,
`MESHY_DCC_UNREAL_ENGINE`, or the project's `EngineAssociation` looked up in
the Epic Games Launcher's install list.

Repair, upgrade and `uninstall` touch only files the receipt owns. They refuse
while the plugin folder holds anything else, apart from build output
(`Binaries/`, `Intermediate/`) and the `__pycache__` directories the editor
writes, and say which files to move out.

An editor launched by `start-instance` advertises a safe stop. Unreal quits
without asking to save, so the stop refuses while any map or asset of the
project is unsaved, or when the editor cannot tell, unless the request
carries `discard_unsaved`. Engine content that gets dirty on its own, such as
a material gaining a usage flag, is not counted and is never saved.

The `meshy-unreal` skill hands Meshy models over: import a GLB or FBX into
`/Game/Meshy/<name>`, turn Meshy's FBX texture set into a PBR material, place
the model in the level through undo, read back meshes, materials and texture
settings, and render a capture of it.

## Building the C++ module

The build needs the machine's toolchain: Visual Studio with the engine's MSVC
and Windows SDK on Windows, and on macOS an Xcode inside the engine's range,
read from `Engine/Config/Apple/Apple_SDK.json` (Unreal 5.7 accepts 15.2 to
26.9, so Xcode 27 is refused). When it fails, the install stops with exit 20,
rolls back, and the message carries the tail of `.meshy-dcc/build.log`. On
macOS a second Xcode can serve the build alone: set `DEVELOPER_DIR` to its
`Contents/Developer` for the install; the editor keeps the selected one.

Native tools checked on the real host: `unreal-automation`
`list_automation_tests` and `mcp_self_check`, `unreal-fab-assets`
`inspect_fab_session`, `unreal-materials` `set_material_instance_parameters`,
`unreal-chaos` (create and spawn a geometry collection), and `unreal-pie`
(enter, key tap, exit). `unreal-niagara` `author_niagara_system` needs Unreal
5.8 and says so on 5.7. `unreal-playtest-agent` needs a project whose PIE
session possesses a pawn. `focus_level_editor_viewport` and
`connect_material_expression_to_customized_uv` were not run.

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
