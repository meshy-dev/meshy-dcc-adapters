# meshy-dcc-unity

The Meshy DCC Core adapter for the Unity Editor. It ships the UPM Editor
package `ai.meshy.dcc`, a Python sidecar that serves MCP and registers the
Editor with the local `meshy-dcc` registry, a loopback WebSocket bridge
between the two, and typed project, scene, build and diagnostic tools.

Targets Unity 2018.4.25f1 and later (the .NET 4.x Equivalent scripting runtime
is required on 2018.4). Verified with Unity 6000.4.10f1 on macOS arm64:
per-project install, `meshy-dcc start-instance`, FBX import with a PBR
material from a Meshy texture set, save and reopen, and safe stop. Other
Editor versions are untested.

## Install

```bash
pip install meshy-dcc-unity
meshy-dcc-unity install --project /path/to/UnityProject --dry-run
meshy-dcc-unity install --project /path/to/UnityProject --yes
```

Open or restart the Unity project so Package Manager compiles **Meshy DCC Unity**, then run:

```bash
meshy-dcc-unity
```

See the [installation guide](https://github.com/meshy-dev/meshy-dcc-unity/blob/main/install.md) for
JSON output, verification, upgrade, uninstall, rollback, and troubleshooting details. The legacy
`meshy-dcc-unity-install` entry point remains available during migration.

The MCP endpoint uses a free loopback port and is registered for gateway discovery. Set
`MESHY_DCC_UNITY_PORT=8765` before starting the server only when a fixed direct endpoint is needed.
The Editor package reconnects to the loopback bridge at `ws://127.0.0.1:13852`; set
`MESHY_DCC_UNITY_BRIDGE_PORT` before the MCP server and `MESHY_DCC_UNITY_BRIDGE_URL` before Unity starts
to override it. `MESHY_DCC_UNITY_BRIDGE_TIMEOUT` may increase the 60-second RPC timeout but cannot
lower it; queued Editor work expires first so timed-out mutations are not executed later.

Transport connection does not imply that Unity's Editor update loop is responsive. The adapter
probes that loop separately; when a native modal dialog blocks it, subsequent typed calls fail
quickly with recovery guidance instead of waiting for the bridge timeout. Use
`meshy-dcc ui-control` for the same instance, or search `ui-control` and load Core's `app-ui`
compatibility Skill from an MCP client. The recovery session must bind the exact Unity PID/HWND
through `dcc-cua`, dismiss one modal action, and then verify a fresh readiness probe before retrying.

The default bridge targets one Unity Editor. For concurrent Editors, run one adapter per Editor and
assign each pair a unique bridge port and URL before starting either process.

Source writes are disabled by default. An operator may set
`MESHY_DCC_UNITY_ALLOW_SOURCE_WRITES=1` before starting Unity to enable the bounded
`upsert_text_asset` tool. It accepts only allowlisted UTF-8 text extensions below `Assets`, caps
encoded content at 256 KiB, rejects JSON-unsafe control characters, requires compare-and-swap state,
rejects reparse points, and replaces files atomically. The adapter exposes no delete, arbitrary path,
shell, or code-evaluation tool.

The per-asset lock is cooperative: it serializes Meshy DCC writers but cannot stop another same-user
process from ignoring the lock or swapping a junction or symlink after path validation and before the
operating system resolves a write. That same-user race is outside this in-process boundary. If an
external replacement conflict is detected, the adapter performs no automatic rollback, preserves the
displaced bytes in a unique `.meshydcc-*.backup` conflict backup, and does not write the target again
after detection. A failed conflict job does not prove the target stayed unchanged; inspect both the
target and backup before submitting another write.

## Standalone sidecar

Hosts without an embedded Python runtime can use the PyOxidizer sidecar released with each version.
The release asset contains the executable, its adjacent `lib/` runtime, and `SHA256SUMS`. Configure
the Unity package to start it on editor load by setting `MESHY_DCC_UNITY_SIDECAR_PATH`; optionally set
`MESHY_DCC_UNITY_SIDECAR_SHA256` to the published digest. The launcher is loopback-only, passes the
Unity process id to `--watch-pid`, and uses a per-project pid file to avoid duplicate sidecars after
assembly reloads.

For local development, run `meshy-dcc-unity-standalone --bridge-port 13852 --watch-pid <unity-pid>`.

## Agent workflow

1. Load `unity-project` and call `inspect_project` before assuming project or editor state. Stop if
   the returned project is not the intended target or the Editor is compiling, updating, entering
   Play Mode, or playing.
2. Read an existing source with `read_text_asset`, then pass its SHA-256 to `upsert_text_asset`;
   use `expected_sha256: absent` only for creation. Keep the UUID `request_id` and poll
   `inspect_job` until it reports `succeeded` or `failed`.
3. Call `refresh_and_compile`, poll its job, and inspect `read_console` before entering Play Mode.
4. Load `unity-scene` and call `inspect_scene` immediately before using an instance ID. Treat IDs
   as opaque values and return them unchanged. Unity 6000.5+ emits decimal strings; older Editors
   retain integer output, and both forms are accepted as input.
5. Create GameObjects or change transforms through typed operations backed by Unity Undo, verify
   the hierarchy, then explicitly call `save_scene`.
6. In Tuanjie projects with its optional AI packages installed, load `unity-tuanjie-ai`, inspect
   the native CustomTool catalog, then submit or query only a freshly returned tool name. Native
   Codely sign-in, credits, downloads, and task recovery remain owned by Tuanjie.
6. Use `set_play_mode` before `capture_game_view`; capture requires active, unpaused Play Mode,
   focuses Game View, waits a rendered frame, and succeeds only after Unity decodes a nonzero PNG
   below `Builds/MeshyDcc/Captures`. Captures are limited to 32 MiB, 8192 pixels per axis, and
   32M pixels total.
7. `run_tests` executes the installed Unity Test Framework in EditMode or PlayMode without spawning
   another Editor. Optional filters are exact fully-qualified test or fixture names. Poll the job and
   retain its request-scoped NUnit XML, SHA-256, outcome, and counts as test evidence; zero matches
   fail closed.
8. `build_windows_player` persists an active-target switch when needed, rejects dirty enabled scenes,
   and builds exactly the saved Build Settings scenes to a new UUID directory below `Builds/MeshyDcc`.
   Poll the job and launch the reported executable as a separate acceptance gate.
9. `build_android_player` applies the same persistent scene and request boundaries to APK or AAB
   output. It fails closed when Android support or required project signing is unavailable, never
   accepts signing secrets, restores the app-bundle setting, and reports BuildReport metadata plus
   the artifact size and SHA-256.

Do not replace a timed-out job with a new UUID. Reconnect and inspect the original `request_id`;
Unity persists queued/running/succeeded/failed state across domain reloads and rejects reuse with
different parameters.

Unity 2018 reloads Editor assemblies during normal Play Mode transitions, so the loopback socket
will disconnect and reconnect. `set_play_mode` persists its waiting state before requesting the
transition; a bridge disconnect is not completion or failure. After reconnection, inspect the same
`request_id` for the observed terminal state.

No raw C# evaluation, shell command, or arbitrary filesystem write is exposed. The Editor bridge
accepts only the methods implemented in `MeshyDccCommands` and executes them on Unity's editor update
loop. One persistent mutating job runs at a time. Mutations fail closed in incompatible Editor
states. Requests, queued work, source text, scene snapshots, Console reads, and serialized responses
have explicit size or lifetime budgets.

## Tuanjie Engine

团结引擎 (Tuanjie Engine) is Unity China's localized distribution of Unity, tailored for the
Chinese market with additional platform support and AI capabilities. Meshy DCC Unity detects and
works with both standard Unity Editor builds and Tuanjie Engine builds without separate
deployment — no additional configuration is needed.

When Tuanjie's optional AI packages are installed in the project, the `unity-tuanjie-ai` tool
set becomes available. It exposes the native CustomTool catalog so agents can inspect available
tools, submit requests, and query results through Tuanjie's Codely platform. Sign-in, credits,
downloads, and task recovery remain owned by the Tuanjie runtime.

## Development

```bash
python -m pip install --no-deps <meshy_dcc_core wheel> -e .
python -m pip install "websockets>=12" "jsonschema>=4" "pytest>=8" "pyyaml>=6"
PYTHONPATH=src:. python -m pytest tests
```

Unity and the Unity cube logo are trademarks of Unity Technologies. This independent adapter is
not affiliated with or endorsed by Unity Technologies.

## License

MIT; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
