# Install Meshy DCC Unity

This runbook is the contract for agent-driven installation on Windows, macOS, and Linux.
The installer plans by default and uses stable exit codes: `0` success, `10` preflight,
`20` acquire, `30` install, `40` verify, and `50` restart required.

## Requirements

- Unity Editor 2018.4.25f1 or newer (including supported Tuanjie `2022.3.*t*` releases)
- The .NET 4.x Equivalent scripting runtime when using Unity 2018.4
- Python 3.9 or newer with `meshy-dcc-core>=0.2.0,<0.3.0`
- A Unity project containing `Assets/` and `ProjectSettings/ProjectVersion.txt`

The installer supports Windows, macOS, and Linux. Use `--dcc-path` when Unity Hub is in a
nonstandard location and `--python` when the adapter belongs to a different interpreter.
Interpreter selection is `--python`, then `MESHY_DCC_INSTALL_PYTHON`, then the interpreter running
the command.

## Supported versions

The minimum host version is Unity `2018.4.25f1`. The project version is checked before any write.
Unity alpha/beta releases below that exact floor are rejected. Tuanjie `t` releases are compared
at the same stability level as Unity final releases.

## Agent quick path

Install the wheel through the pinned Meshy DCC catalog, plan the project change, then execute it:

```bash
meshy-dcc install --dcc-type unity --execute
meshy-dcc-unity install --project /path/to/UnityProject --json --dry-run
meshy-dcc-unity install --project /path/to/UnityProject --json --yes
```

The JSON schema contains `schema_version`, status and versions, selected host/interpreter,
`steps[]`, executable `next_steps[]`, `receipt_path`, and the verify-to-usable verdict. A completed
copy can return `50` until Unity has reloaded the package; execute the returned `next_steps[]` and
run `verify` again.

## Manual path

```bash
python -m pip install meshy-dcc-unity
meshy-dcc-unity install --project /path/to/UnityProject --yes
```

The package is staged and swapped into `Packages/ai.meshy.dcc`; an existing package is kept
as a rollback candidate until the new package and receipt are durable. The receipt is written to
`.meshy-dcc/receipts/unity.json` and records file digests, versions, interpreter, and touched paths.
Re-running the command converges without rewriting an already-current install.

The legacy command remains available during migration:

```bash
meshy-dcc-unity-install /path/to/UnityProject
```

Open or restart the project after installation. If `MESHY_DCC_UNITY_SIDECAR_PATH` is not configured,
start `meshy-dcc-unity` in a terminal.

## Verify

```bash
meshy-dcc-unity status --project /path/to/UnityProject --json
meshy-dcc-unity verify --project /path/to/UnityProject --json
```

`verify` checks the installed files against the receipt, imports the adapter in the selected
Python interpreter, and probes a registered Unity sidecar. Only a successful live probe produces
`directly_usable: true`; copied files alone are not reported as usable.

## Upgrade

```bash
python -m pip install --upgrade meshy-dcc-unity
meshy-dcc-unity upgrade --project /path/to/UnityProject --json --dry-run
meshy-dcc-unity upgrade --project /path/to/UnityProject --json --yes
```

The upgrade uses the same staged transaction and restores both the previous package and previous
receipt when committing the replacement fails. Close Unity and retry if the command returns `50`.

## Uninstall

```bash
meshy-dcc-unity uninstall --project /path/to/UnityProject --json --dry-run
meshy-dcc-unity uninstall --project /path/to/UnityProject --json --yes
python -m pip uninstall meshy-dcc-unity
```

Uninstall consumes the receipt and removes only its exact package path. It is idempotent when both
the package and receipt are absent, and refuses to delete an unreceipted directory. After stopping
the sidecar, remove stale Unity adapter registrations with `meshy-dcc unregister --dcc-type unity`
if your Core version exposes that command. Stale standalone pid files use the project hash and live
under the operating-system temporary directory; a dead-owner file is reclaimed on the next start.

## Troubleshooting

- **Exit `10`, not a Unity project or unsupported version:** pass the project root, not `Assets/`,
  and inspect `ProjectSettings/ProjectVersion.txt`.
- **Exit `40`, artifact/import failure:** run `status --json`; use `upgrade --yes` to repair a
  partial or modified package, and ensure `--python` names the interpreter containing the adapter.
- **Exit `40`, readiness failure:** open the project, wait for compilation, start the sidecar, and
  inspect `meshy-dcc list` before rerunning `verify`.
- **Exit `50`, restart required:** close every Unity process using the project and repeat the exact
  command. The installer does not delete a loaded tree.
- **Bridge connection failure:** keep `MESHY_DCC_UNITY_BRIDGE_PORT` and
  `MESHY_DCC_UNITY_BRIDGE_URL` consistent. The default is `ws://127.0.0.1:13852`.
- **Editor bootstrap failure:** inspect `Library/MeshyDcc/bootstrap-errors.jsonl`. Startup hooks append
  structured stage, exception type, message, and timestamp records there.
- **Concurrent Editors:** use one adapter and a unique bridge port/URL pair per Editor process.

Optional runtime controls are `MESHY_DCC_UNITY_PORT`, `MESHY_DCC_UNITY_BRIDGE_TIMEOUT`, and
`MESHY_DCC_UNITY_ALLOW_SOURCE_WRITES=1`. Tool arguments cannot enable source writes.
