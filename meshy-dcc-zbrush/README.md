# meshy-dcc-zbrush

The Meshy DCC Core adapter for Maxon ZBrush 2026.1 and later. It ships a
bridge that runs inside ZBrush and puts every `zbrush.commands` call on the
ZBrush main thread, an external Python sidecar that serves MCP and registers
ZBrush with the local `meshy-dcc` registry, and typed tools for subtools, OBJ
import and export, saving and opening projects and tools, map baking,
brushes and turntable captures.

**Status: experimental.** Not verified on a real ZBrush yet: the install step
was checked against a ZBrush 2026.2 installation (version and Maxon signature)
without launching it, and the launch, call, save, reopen and stop path was run
end to end against a stand-in for ZBrush. Everything that needs a running
ZBrush (that `-script` keeps the bridge serving, the import, save and open
buttons, the macOS main-thread pump) is untested.

## Requirements

- ZBrush 2026.1 or newer (its Python SDK and `-script` command line) on macOS
  arm64 or Windows x64.
- `meshy-dcc-core >= 0.2.0, < 0.3.0`. The Meshy DCC package bundles CPython
  3.11 and Core, so no Python install is needed.

## With Meshy DCC

The adapter installs per project folder; the folder holds the work (models to
import, saved `.zpr` and `.ztl` files):

```bash
meshy-dcc install --dcc-type zbrush --project /path/to/folder --execute
meshy-dcc start-instance --dcc-type zbrush --project /path/to/folder --wait-ready
```

`install` extracts the package and runs `meshy-dcc-zbrush setup-project`,
which checks ZBrush (version and Maxon signature) and writes
`<folder>/.meshy-dcc/launch-plan.json`. `start-instance` then starts
`ZBrush -script <bridge>`; the bridge listens on a free loopback port and
starts the sidecar from the package's Python with that port and a per-launch
token. Nothing is written into the ZBrush installation or ZBrush's own
settings, so a ZBrush opened by hand does not load the bridge.

See [install.md](install.md) for the commands the package runs, the manual
path and troubleshooting.

## How it works

```
Agent → meshy-dcc gateway → sidecar (package Python, meshy_dcc_zbrush serve)
      → loopback TCP, token → bridge inside ZBrush → zbrush.commands (main thread)
```

The bridge serves one SDK request at a time; a second one gets a retryable
busy answer, and `ping` is answered without touching the SDK. A request still
running when the 600 s bridge timeout ends is reported as still running, not
retried. On Windows the bridge drains requests from a UI-thread timer; on
macOS it pumps them from a loop that keeps calling `zbc.update`.

## Tools

| Skill | Tools |
|-------|-------|
| `zbrush-scripting` | `execute_python`, `get_session_info` |
| `zbrush-scene` | `get_scene_info`, `list_subtools` |
| `zbrush-subtool` | `select_subtool`, `get_subtool_status`, `inspect_active_mesh`, `refine_active_subtool`, `remesh_active_subtool`, `bake_active_subtool_map` |
| `zbrush-brush` | `create_wrinkle_brush`, `load_wrinkle_brush` |
| `zbrush-viewport` | `capture_turntable` |
| `zbrush-interchange` | `export_active_subtool_obj` |
| `zbrush-import-to-scene` | `import_to_scene` (OBJ only) |
| `zbrush-file` | `save_project`, `save_tool`, `open_project` |

ZBrush imports OBJ without a dialog; FBX opens an interactive importer and is
refused, and ZBrush has no GLB importer. An OBJ face with more than four
vertices would open a blocking Note, so the import refuses it first. ZBrush
cannot report unsaved changes, so `meshy-dcc stop-instance` is refused unless
the user agreed to `--discard-unsaved`; save with `zbrush-file` first.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MESHY_DCC_ZBRUSH_SOCKET_PORT` | free port (19876 for a bridge without a package) | Bridge port |
| `MESHY_DCC_ZBRUSH_BRIDGE_TOKEN` | per launch | Token the bridge requires; set the same value for a hand-started sidecar |
| `MESHY_DCC_ZBRUSH_EXECUTABLE` | | ZBrush for `setup-project` when `--dcc-path` is not given |
| `MESHY_DCC_ZBRUSH_BRIDGE_LOG` | | File the bridge appends startup notes to |
| `MESHY_DCC_ZBRUSH_PORT` | free port | Fixed MCP port for the sidecar |
| `MESHY_DCC_GATEWAY_PORT` | `19765` | Gateway port |
| `MESHY_DCC_MINIMAL` | `1` | Load only `zbrush-scripting` and `zbrush-scene` at start |

## Development

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python --no-deps <meshy_dcc_core wheel> -e .
uv pip install --python .venv/bin/python pytest pytest-xdist pytest-mock 'jsonschema>=4.18' pyyaml
PYTHONPATH=src:. .venv/bin/python -m pytest tests -q
.venv/bin/python tools/lint_skills.py
python packaging/build_package.py --core-wheel <wheel> --platform macos-arm64 --output-dir dist
```

The earlier receipt-driven installer into a ZBrush Asset Directory
(`meshy-dcc-zbrush install|status|verify|uninstall|upgrade --asset-dir …`),
`tools/pack_plugin.py` and `tools/bootstrap_agent_install.py` are still in the
tree but are not part of the Meshy DCC path and are untested here.

## License

MIT; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
