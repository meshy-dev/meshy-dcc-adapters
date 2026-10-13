# Install Meshy DCC for Godot

## Requirements

- Windows 10/11, macOS 12+, or a current Linux distribution.
- Godot 4.4 or newer. The adapter does not download or cache Godot; install it
  from the official Godot distribution or your operating-system package manager.
- Python 3.9 or newer and `meshy-dcc-core` 0.2.x.
- A Godot project containing `project.godot`.

The Python interpreter runs the adapter outside Godot. The bundled GDScript
EditorPlugin is installed into one project and all Godot API calls remain on the
editor main thread.

## Supported host locations

Automatic discovery checks `godot4` and `godot` on `PATH`. Use `--dcc-path`
for any other installation. Common paths include:

- Windows: `C:\Program Files\Godot\Godot_v4.x-stable_win64.exe`
- macOS: `/Applications/Godot.app/Contents/MacOS/Godot`
- Linux: `/usr/bin/godot4`, `/usr/local/bin/godot`, or an operator-managed AppImage

## Agent quick path

Install the released wheel into the Python environment that will run the
adapter:

```bash
python -m pip install meshy-dcc-godot
```

Plan first. Replace the example paths with the target project, Godot executable,
and Python interpreter:

```bash
meshy-dcc-godot install /path/to/project --dcc-path /path/to/godot --python /path/to/python --dry-run --json
meshy-dcc-godot install /path/to/project --dcc-path /path/to/godot --python /path/to/python --yes --json
```

The installer validates the host, Python, Core, and project before mutation. It
stages a complete addon replacement, updates the `[editor_plugins]` entry, and
writes `.meshy-dcc/receipts/godot.json`. Exit 50 is expected until the adapter and
Godot editor are running. Follow the JSON `next_steps` exactly, then verify:

```bash
meshy-dcc-godot serve
meshy-dcc-godot verify /path/to/project --json
```

`verify` imports the adapter in the recorded interpreter, waits for Godot/Core
readiness, loads the typed project skill, calls `get_project_info`, and confirms
that the responding editor owns the requested project. A copied addon alone is
never reported as directly usable.

When several Godot editors are registered, `verify` probes them independently
and accepts only the matching project. An operator may narrow the same check
with `--instance-id <uuid>`; project-path readback is still mandatory.

## With Meshy DCC

`meshy-dcc install --dcc-type godot --project <root> --execute` runs this
installer from the Meshy DCC package with `--sidecar <path> --files-only`.
`--sidecar` records `.meshy-dcc/launch-plan.json` (read by `meshy-dcc
start-instance`) and `.meshy-dcc/godot.json` (read by the EditorPlugin to
start the sidecar); `--files-only` returns exit 0 once files are in place and
leaves readiness to `start-instance`. Set `MESHY_DCC_GODOT_EXECUTABLE` when
Godot is neither on `PATH` nor in `/Applications`.

## Manual path

The supported agent path above is preferred. If policy requires manual file
placement, copy the packaged `godot_addon/addons/meshy_dcc_godot` directory to
`<project>/addons/meshy_dcc_godot`, enable
`res://addons/meshy_dcc_godot/plugin.cfg` in the project's `[editor_plugins]`
section, start `meshy-dcc-godot serve`, and run `verify`. Manual installs have no
receipt and therefore cannot use the receipt-owned uninstall command; repair
with the standard installer first.

## Status and repair

```bash
meshy-dcc-godot status /path/to/project --json
meshy-dcc-godot install /path/to/project --dcc-path /path/to/godot --python /path/to/python --yes --json
```

`status` distinguishes absent, partial, and receipt-complete installs without
claiming live readiness. Re-running `install` repairs a partial install only
when the typed receipt still proves ownership; an unknown or tampered addon
root fails closed instead of being overwritten. Locked files fail closed; exit
50 means close or restart Godot and repeat the same command.

The plugin writes bounded startup state to
`<project>/.godot/meshy_dcc_godot_bootstrap.json`. `starting` without `ready`, a
missing file, or an editor error indicates a bootstrap failure. This file is a
diagnostic only; live typed readiness remains authoritative.

## Upgrade

Upgrade the wheel, then transactionally replace the project addon:

```bash
python -m pip install --upgrade meshy-dcc-godot
meshy-dcc-godot upgrade /path/to/project --dcc-path /path/to/godot --python /path/to/python --dry-run --json
meshy-dcc-godot upgrade /path/to/project --dcc-path /path/to/godot --python /path/to/python --yes --json
```

The staged replacement removes previously owned files no longer shipped by the
new version, preserves files outside the receipt-owned set, and rolls back to
the previous tree if the transaction fails.

## Uninstall

```bash
meshy-dcc-godot uninstall /path/to/project --dry-run --yes --json
meshy-dcc-godot uninstall /path/to/project --yes --json
python -m pip uninstall meshy-dcc-godot
```

Uninstall requires the project receipt, validates its version, project and
destination identity, regular-file paths, and SHA-256 values, then removes only
the exact adapter-owned files and plugin configuration it created. Extra files,
other plugins, comments, line endings, and unrelated project settings are
preserved. Traversal, stale content, symlinks/reparse points, and malformed
receipts fail closed before deletion.

## JSON and exit codes

Every lifecycle verb emits one JSON result (`--json` remains an accepted
compatibility flag); mutating verbs also accept `--yes` and `--dry-run`.
Dry-runs perform bounded host, Python, and receipt ownership preflight while
remaining zero-write. `--dcc-path` and `--python` override discovery. Results
follow Install SOP schema version 1 and use these stable exits:

| Exit | Meaning |
| ---: | --- |
| 0 | The requested plan, status, uninstall, or live verification succeeded. |
| 10 | Preflight or explicit confirmation failed. |
| 20 | Payload acquisition failed. The Godot adapter currently acquires no external payload. |
| 30 | Install, repair, receipt, or uninstall failed. |
| 40 | Target import, live readiness, typed ping, or project binding failed. |
| 50 | Files are locked or the newly installed plugin requires a host restart/load. |

## Troubleshooting

- **Godot was not found:** pass the real editor binary with `--dcc-path`; the
  adapter never scrapes or downloads a latest host build.
- **Exit 10 for Core or Python:** run the command from the intended Python
  environment and upgrade `meshy-dcc-core` before retrying.
- **Status is partial:** keep the project closed and rerun `install --yes`; the
  staged transaction converges the addon, plugin entry, and receipt.
- **Exit 40 at readiness:** start `meshy-dcc-godot serve` and the target Godot
  project with the same `MESHY_DCC_GODOT_BRIDGE_PORT`, then rerun `verify`.
- **Target binding failed:** more than one Godot editor may be registered. Stop
  unrelated instances and verify the requested project again.
- **Bootstrap did not become ready:** inspect
  `.godot/meshy_dcc_godot_bootstrap.json` and the Godot editor Output panel. Fix
  the reported script/import problem, reload the plugin, and rerun `verify`.
- **Exit 50 for locked files:** close Godot, repeat the exact lifecycle command,
  then restart the editor. The previous addon remains recoverable until the
  staged replacement commits.
