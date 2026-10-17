# Meshy DCC for Roblox Studio

Lets an agent working through [Meshy DCC Core](https://github.com/meshy-dev/meshy-dcc-core)
read and edit an open Roblox Studio place and put Meshy models into it.

**Status: experimental.** Not verified in a real Roblox Studio yet; the
sidecar, installer and packages are tested offline only.

## How it works

Studio plugins cannot listen on a port or start programs, so the adapter has
two parts:

- **Studio plugin** (`MeshyDcc.lua`, one Luau file in Studio's local plugins
  folder). In the edit DataModel of every place it probes ports 13890-13893 on
  127.0.0.1, opens a WebSocket to a Meshy DCC sidecar that accepts it and runs
  that sidecar's requests inside Studio as undoable steps.
- **Sidecar** (Python package `meshy_dcc_roblox`, run by the CPython bundled in
  the package). `meshy-dcc start-instance` runs it with `launch`: it takes the
  first free port of the range, opens the project's place in Studio and serves
  the Meshy DCC tools. It accepts only the plugin of that place (a local file
  by name, a published place by PlaceId) and refuses every other Studio window.

A project is a directory holding one local place file (`.rbxl` or `.rbxlx`),
or bound to a published place with `--place-id` and `--universe-id`.

## Install

```sh
meshy-dcc install --dcc-type roblox --project <directory with the place file>
```

This extracts the package and runs its installer, which:

- writes the plugin to Studio's local plugins folder
  (`~/Documents/Roblox/Plugins/MeshyDcc.lua` on macOS,
  `%LOCALAPPDATA%\Roblox\Plugins\MeshyDcc.lua` on Windows); Studio loads it at
  its next start;
- writes `.meshy-dcc/roblox.json` (the place) and `.meshy-dcc/launch-plan.json`
  in the project.

The first time the plugin reaches 127.0.0.1, Studio may ask whether it may; the
answer is kept in Studio's plugin management. `meshy-dcc-roblox uninstall
--project <dir> --plugin` removes both.

## Tools

| Skill | Tools |
|---|---|
| `roblox-scene` | `session`, `get_scene_tree`, `inspect_instance`, `create_instance`, `set_properties`, `move_instance`, `delete_instance`, `execute_luau` |
| `meshy-roblox` | `import_model`, `inspect_model` |

`execute_luau` is refused until the user clicks **Allow Luau** in Studio's
Meshy DCC toolbar.

## Limits

- **Saving.** Studio gives plugins no way to save a place or to tell whether
  it has unsaved changes. The user saves in Studio; `stop-instance` always
  needs `--discard-unsaved`, and then ends the Studio process it started.
- **Imported models.** Studio cannot import a file from disk without a
  dialog. The sidecar decodes the GLB (textures with Pillow) and the plugin
  rebuilds it with `EditableMesh` and `EditableImage` (at most 60,000 vertices
  and 20,000 triangles per MeshPart, so larger meshes are split; images at most
  1024 px). Roblox does not save editable meshes with a place, so such a model
  lasts for the Studio session. `publish: true` uploads the meshes and images to
  the logged-in user's Roblox inventory through `AssetService:CreateAssetAsync`
  (no prompt, Roblox moderation applies) and builds the model from those
  assets, which persists. No Open Cloud key is used.
- **Concurrency.** At most four places can be served at once (one port each).
- Play-test DataModels are ignored.

## Development

```sh
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python --no-deps <meshy_dcc_core wheel>
uv pip install --python .venv/bin/python --no-deps -e .
uv pip install --python .venv/bin/python pytest 'websockets>=14,<18' pillow
.venv/bin/python -m pytest tests -q
.venv/bin/python tools/lint_skills.py
python3 packaging/build_package.py --core-wheel <wheel for the platform> \
    --platform macos-arm64 --output-dir dist      # or windows-x64
```

`tests/test_plugin.py` also runs `luau-analyze` from the official Luau release
over the plugin when `LUAU_ANALYZE` points to it.

## License

MIT. See [LICENSE](LICENSE).
