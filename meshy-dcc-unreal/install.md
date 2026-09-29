# Install Meshy DCC for Unreal

## Requirements

- Unreal Engine 5.0 or newer with a project (`.uproject`). The plugin needs
  the engine's Python Editor Script Plugin and Editor Scripting Utilities; it
  enables both as dependencies. A project that switches either off is refused.
- On macOS, Xcode with its license accepted and the Metal toolchain
  (`xcodebuild -downloadComponent MetalToolchain`). The editor itself needs
  them to compile shaders; the plugin compiles nothing.
- Close the project in Unreal before installing, repairing or uninstalling.

## With meshy-dcc

```bash
meshy-dcc install --dcc-type unreal --project /absolute/project --execute --json
```

This downloads the Meshy DCC package, checks its SHA-256, extracts it and runs
its installer on the project. The package carries its own Python for the
installer; the plugin runs on the editor's Python.

## The installer

```bash
bin/meshy-dcc-unreal install <project> [--engine <root>] [--yes] [--json]
bin/meshy-dcc-unreal uninstall <project> [--yes] [--json]
bin/meshy-dcc-unreal status <project> [--json]
```

`<project>` is the project directory (holding exactly one `.uproject`) or the
`.uproject` itself. Without `--yes` nothing is written and the report is a
plan.

`install`:

1. Finds the engine: `--engine`, then `MESHY_DCC_UNREAL_ENGINE`, then the
   project's `EngineAssociation` (for example `5.7`) in the Epic Games
   Launcher's install list, then the launcher's default folder. The engine's
   major and minor version must match the association.
2. Copies the plugin into a staging folder under `.meshy-dcc/`, checks every
   file against the package, then moves it to `Plugins/MeshyDccUnreal`.
3. Writes `.meshy-dcc/launch-plan.json` (the editor and
   `{project}/<name>.uproject`), `.meshy-dcc/.gitignore` and the receipt
   `.meshy-dcc/receipts/unreal.json` with the SHA-256 of every plugin file.
4. On an existing install it reports `current` (nothing to copy), `repair`
   (same version, files differ or are missing) or `upgrade`, replaces the
   plugin and deletes the old copy.

A failure while replacing restores the previous plugin, launch plan and
receipt. The `.uproject` is never changed.

`uninstall` removes the plugin, the launch plan, the receipt and the
`.gitignore`, then any folders left empty. Imported assets and levels stay.

Both refuse, without changing anything, while `Plugins/MeshyDccUnreal` holds a
file the receipt does not own or one whose content changed. Python's
`__pycache__` folders, which the editor writes, do not count. The report lists
the files; move them out and run the command again. A `Plugins/MeshyDccUnreal`
without a receipt is never touched.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Done, or planned without `--yes` |
| 10 | Preflight: no single `.uproject`, engine not found or mismatched, a required plugin disabled, or foreign files in the plugin folder |
| 30 | The change failed and was rolled back |
| 50 | Done, but the previous copy was kept because files in it changed during the install; the report names it |

`meshy-dcc` shows the installer's message from stderr when a step fails.
