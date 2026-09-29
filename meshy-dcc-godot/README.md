# meshy-dcc-godot

The Meshy DCC Core adapter for the Godot 4 editor. It ships a GDScript
`EditorPlugin`, an `EngineDebugger` runtime peer, a Python sidecar that serves
MCP and registers the editor with the local `meshy-dcc` registry, a loopback
WebSocket bridge between the two, 163 on-demand tools and a tested 2D
arena-roguelike skill.

Targets Godot 4.4 and later. Verified with Godot 4.7.2 on macOS arm64:
install, `meshy-dcc start-instance`, GLB import with PBR readback, save and
reopen, and safe stop.

## With Meshy DCC

`packaging/build_package.py` builds the Meshy DCC package: a relocatable
CPython with `meshy_dcc_core`, this adapter and `websockets`, plus
`bin/meshy-dcc-godot-sidecar`. Godot needs no Python of its own.

```bash
meshy-dcc install --dcc-type godot --project /path/to/project --execute
meshy-dcc start-instance --dcc-type godot --project /path/to/project --wait-ready --yes
```

The first command extracts the package and runs its installer with
`--sidecar <path> --files-only`: the addon goes into `addons/`, the plugin is
enabled in `project.godot`, and `.meshy-dcc/` receives the start-instance
launch plan and the sidecar path (it ignores itself for version control;
Godot does not scan dot directories). The installer finds Godot through
`--dcc-path`, `MESHY_DCC_GODOT_EXECUTABLE`, `godot4` or `godot` on `PATH`, or
`Godot.app` in `/Applications` or `~/Applications`.

When the editor loads the plugin it starts the recorded sidecar on a free
bridge port, so several editors can run at once; the sidecar exits with the
editor. An editor launched by `start-instance` advertises a safe stop: it
exits when no scene or script is unsaved and refuses otherwise, unless the
request carries `discard_unsaved`.

The `meshy-godot` skill hands Meshy models over: scan a self-contained GLB
below `res://assets/meshy/`, wait for the import, instance it through undo/redo
and read back meshes, PBR materials and transforms.

## Install

The lifecycle is documented in [`install.md`](install.md): plan-first JSON,
staged project updates, receipts, repair, live verification, upgrade and
receipt-owned uninstall.

```bash
pip install meshy-dcc-godot
meshy-dcc-godot install /path/to/project --dcc-path /path/to/godot --dry-run --json
meshy-dcc-godot install /path/to/project --dcc-path /path/to/godot --yes --json
```

Start the adapter, then open the project in Godot:

```bash
meshy-dcc-godot serve
```

Each adapter instance uses an OS-assigned MCP port and registers it for
`meshy-dcc` discovery through the gateway at `http://127.0.0.1:19765/mcp`; set
`MESHY_DCC_GODOT_PORT` only when a fixed direct endpoint is required. The plugin
connects to the loopback bridge at `ws://127.0.0.1:13847`; override the bridge
port with `MESHY_DCC_GODOT_BRIDGE_PORT` before starting both processes.

Agents drive the editor through the `meshy-dcc` CLI:

```bash
meshy-dcc list
meshy-dcc search --query "<task>" --dcc-type godot
meshy-dcc load-skill <skill-name> --dcc-type godot
meshy-dcc call <tool-slug> --json '{"key":"value"}'
```

For release packaging, load `godot-build-optimization` after choosing the
target export preset. It scans the project, generates a version-aware
`custom.py` and optional `.gdbuild` profile in a staging directory, and records
artifact sizes and SHA-256 digests. Generated disable flags remain hypotheses
until the packaged build is launched and smoke-tested.

## Agent workflow

1. Search skills for the required domain, such as `Godot animation`, `Godot runtime`, or
   `Godot TileMap`.
2. Load only the returned domain skill. Tools remain deferred until their skill is loaded.
3. Inspect the project or scene before mutating it, then save and validate the result.
4. Load `godot-runtime`, `godot-input`, or `godot-testing-qa` after starting the game when
   live inspection, input simulation, or QA assertions are required.

The original `godot-project`, `godot-scene`, and `godot-roguelike` skills remain available.

## Capability skills

The adapter groups 164 fine-grained tools into 23 independently loadable domains:

| Domains | Tools |
| --- | ---: |
| Project, scene management, node, script, editor | 47 |
| Input and runtime | 27 |
| Animation and AnimationTree | 14 |
| 3D scene, physics, particles, navigation, audio | 29 |
| TileMap, Theme/UI, shader, resource | 24 |
| Batch/refactor, analysis, testing/QA, profiling, export | 23 |

Runtime tools use the official `EditorDebuggerPlugin` and `EngineDebugger` channel, so input
events and game-node operations run in the game process rather than the editor process. Enabling
the plugin registers the bundled runtime peer as an autoload; disabling it removes the autoload.

Scene edits use Godot's undo manager and file operations are restricted to `res://` with size and
extension checks. `execute_editor_script` only calls a method on an existing `@tool` project
script. The compatibility tool execute_game_script is not an allowlist: it is a broad public-method
call on an existing runtime node. It must not be used for playtest or RL control, and neither broad
tool accepts raw source for immediate evaluation.

For bounded playtest control, use `execute_typed_action`. It accepts only the strict
`input_action` and exact script-digest-bound `set_property` variants declared in the fixed
`res://.meshy-dcc/playtest-actions.v1.json` project manifest. Calls bind the project, session,
process-unique redacted runtime ID, authority, manifest ID, and manifest SHA-256; replacement,
identity drift, reparse points, extra fields, exhausted budgets, and rate limits fail closed.
The host verifies the exact setter effect and script digest on both sides of mutation. Rejected or
cancelled actions do not consume authority; a cancelled or orphaned claimed mutation is rolled
back before its reservation expires. The editor forwards a typed mutation only after an exact
request-digest authorization handshake; a timeout that wins before authorization leaves a
terminal fence, so a delayed WebSocket commit is rejected before reaching the runtime.
Read [Typed playtest actions](docs/playtest-actions.md) before enabling this path. This foundation
does not provide episodes, rewards, trajectories, NPC control, an RL trainer, or another recorder.

### Main-thread work budgets

`get_game_scene_tree`, `get_game_node_properties`, and `find_ui_elements` accept opaque `cursor`
values returned as `next_cursor`. Their `max_nodes` or `max_properties` limits are clamped to 128,
and the default page is 64 items. Each read reports its measured `elapsed_ms`, requested/clamped
`budget_ms` (1–50, default 40), and `budget_exceeded`. When the budget is exhausted the response
is an incomplete page; continue with the returned cursor and never infer a complete snapshot. Do
not construct or retain a second host-side job. Legacy calls without a cursor still return the
original top-level fields, plus the first bounded page and continuation metadata.

`get_game_screenshot` reads the viewport and copies its RGB8/RGBA8 bytes on the Godot runtime
thread. The existing adapter execution thread then encodes and atomically replaces the requested
PNG; `include_base64=true` also encodes that PNG there. No Godot `Image` resource crosses threads.

`get_editor_screenshot` and `capture_frames` use the same immutable raw-pixel handoff; PNG encoding
is never performed on the editor or game thread. `capture_frames` may return fewer frames than
requested when its budget is exhausted; resume with `start_index=next_index`.

`execute_editor_script` accepts `budget_ms` from 1 to 50 and reports `elapsed_ms` plus
`budget_exceeded`; this is an observational contract and cannot preempt GDScript. With
`chunked=true`, the existing method must return `{done: bool, next_cursor?: value}`. An incomplete
chunk returns a machine-executable `next_step` that calls the same path and method with the next
cursor. The adapter does not add a script executor, timer, thread, or job registry.

## Live smoke

`tests/live_godot_smoke.py` starts the packaged MCP server and EditorPlugin
against a real Godot editor, sends `load_skill`, paginated `tools/list`,
`tools/call` and `jobs_get_status`, creates and edits a scene, starts the game,
verifies the runtime scene tree, then runs the generated gameplay simulation and
requires `ROGUELIKE_SMOKE_OK`.

```bash
python tools/download_latest_godot.py --output .godot-bin   # optional
python tests/live_godot_smoke.py --godot /path/to/Godot
```

## Development

```bash
python -m pip install --no-deps <meshy_dcc_core wheel> -e .
python -m pip install "websockets>=12" "pytest>=8"
PYTHONPATH=src:. python -m pytest tests
python tools/lint_skills.py
```

Godot and the Godot logo are trademarks of the Godot Foundation. This
independent adapter is not affiliated with or endorsed by the Godot Foundation.

## License

MIT; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
