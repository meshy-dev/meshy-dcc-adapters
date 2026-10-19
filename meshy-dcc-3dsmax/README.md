# meshy-dcc-3dsmax

The Meshy DCC Core adapter for Autodesk 3ds Max. It runs inside 3ds Max on the
host's own Python (`pymxs`), registers the session with the local `meshy-dcc`
gateway, and exposes scene, import, material, render and save tools that
agents call through the `meshy-dcc` CLI.

Supports 3ds Max 2023 to 2027. 3ds Max runs only on Windows, so there is only
a Windows x64 package.

## With Meshy DCC

`packaging/build_package.py` builds `meshy-dcc-3dsmax-windows-x64.zip`:

```
payload/                   meshy_dcc_3dsmax and meshy_dcc_core, loaded by 3ds Max's Python
python/                    CPython 3.11 that runs the installer
bin/meshy-dcc-3dsmax.cmd   the installer (payload/meshy_dcc_3dsmax/host_install.py)
```

```bat
meshy-dcc install --dcc-type 3dsmax --execute
meshy-dcc start-instance --dcc-type 3dsmax --wait-ready --yes
```

`install` extracts the package into the Meshy DCC data directory and runs
`bin\meshy-dcc-3dsmax.cmd install --dcc-path <3dsmax.exe> --yes --json`. The
3ds Max comes from `--dcc-path` or the single match of
`C:\Program Files\Autodesk\3ds Max *\3dsmax.exe`. The installer writes one
MAXScript, `meshy_dcc_3dsmax_startup.ms`, into
`%LOCALAPPDATA%\Autodesk\3dsMax\<year> - 64bit\<language>\scripts\startup`
for every language this user has started that 3ds Max in. Nothing goes into
the 3ds Max install directory and nothing is pip-installed. Close 3ds Max
before installing or upgrading: a running 3ds Max keeps the package's files
open.

- `<year>` comes from the install folder name (`3ds Max 2026`). A 3ds Max
  installed elsewhere is refused with `dcc_version_unknown`.
- A 3ds Max this user has never started has no language folder yet; the
  installer refuses with `host_never_started`. Start it once, then install.
- A `meshy_dcc_3dsmax_startup.ms` the installer did not write is never
  overwritten (`startup_script_foreign`).

Remove the adapter with 3ds Max closed:

```bat
"%APPDATA%\meshy-dcc\adapters\meshy-dcc-3dsmax\meshy-dcc-3dsmax-windows-x64\bin\meshy-dcc-3dsmax.cmd" uninstall --dcc-path "C:\Program Files\Autodesk\3ds Max 2026\3dsmax.exe" --json
```

It deletes the startup script (only one carrying the adapter's marker) and the
`Meshy DCC-MeshyDcc3dsmax_*.mcr` macro files the adapter's menu created in each
language's `usermacros`. The package folder and the install record in the
Meshy DCC data directory are core's to delete.

## In 3ds Max

At startup the script puts `payload\` on `sys.path` and calls
`meshy_dcc_3dsmax.max_bootstrap.startup()`. It starts the MCP server in the
3ds Max process (instance port chosen by the OS), registers with the gateway
on `MESHY_DCC_GATEWAY_PORT` (19765 unless set), adds a "Meshy DCC" menu, and
runs every tool on the main thread through one Qt timer pump. A failure is
printed to the MAXScript Listener and never stops 3ds Max from starting.

- `MESHY_DCC_3DSMAX_BOOT_MODE=sidecar` starts an external `meshy-dcc-server`
  sidecar instead (`MESHY_DCC_SERVER_BIN`); the default is the in-process
  server, as for Blender.
- A 3ds Max launched by `start-instance` advertises a safe stop. 3ds Max
  quits without asking to save, and whether its dirty flag sees `pymxs` edits
  is unchecked, so the stop is refused unless the request carries
  `discard_unsaved`. A 3ds Max the user opened is never stopped this way.

## Other installers

`meshy-dcc-3dsmax` (`install_cli.py`, pip into 3ds Max's Python) and
`packaging/assemble_mzp.py` (a drag-and-drop `.mzp`) come from the project
this adapter was forked from. Both fetch `meshy-dcc-core` and
`meshy-dcc-server` from PyPI, which Meshy does not publish, so the Meshy
package does not use them.

## Build and test

```sh
python packaging/build_package.py --core-wheel <meshy_dcc_core win_amd64 wheel> --platform windows-x64 --output-dir dist
PYTHONPATH=src:tests python -m pytest tests -n 2 -o addopts="" -m 'not e2e and not packaging and not integration'
```

## License

MIT source; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
