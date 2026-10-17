# Installing the OpenSCAD adapter

OpenSCAD has no embedded Python and nothing is installed into it. The adapter
is a Python process that runs the `openscad` command-line executable, one
bounded child process per call. Each project (a directory of `.scad` sources
and their outputs) gets its own adapter instance, and that directory is the
instance's workspace root.

## With Meshy DCC

```shell
meshy-dcc install --dcc-type openscad --project /path/to/models --execute
meshy-dcc start-instance --dcc-type openscad --project /path/to/models --wait-ready --yes
```

`install` downloads the package (a relocatable CPython 3.11 with
`meshy_dcc_core` and this adapter), extracts it, and runs
`bin/meshy-dcc-openscad-sidecar install-project <project> --openscad <exe>
--sidecar <launcher>`. That checks the OpenSCAD executable against the
version matrix below and writes `<project>/.meshy-dcc/launch-plan.json`
(the directory ignores itself for version control). Nothing outside the
project and the package directory is written.

OpenSCAD is found through `--dcc-path`, or the one match of the catalog's
usual install locations:

| Platform | Executable |
| --- | --- |
| macOS | `/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD` (or `~/Applications/...`) |
| Windows | `C:\Program Files\OpenSCAD\openscad.exe`; the adapter runs the sibling `openscad.com` console launcher |

`start-instance` runs `meshy-dcc-openscad-sidecar serve --project <project>
--openscad <exe>`. The instance needs no OpenSCAD window. Stop it with
`meshy-dcc stop-instance`; it holds no unsaved state.

## Supported versions

OpenSCAD versions are calendar based: `YYYY.MM` for releases and
`YYYY.MM.DD` for the dated development snapshots. The ranges are declared in
`compat_matrix.json` and enforced by `install-project` and before every
modelling call:

| Range | Example | Verified |
| --- | --- | --- |
| `2021.01.x` | `2021.01` (last stable release; Intel-only on macOS) | upstream CI on Linux |
| `2026.09.x` | `2026.09.29` snapshot | upstream CI on Linux; macOS Apple Silicon |
| `2026.10.x` | `2026.10.15` snapshot | macOS Apple Silicon, end to end through Meshy DCC |

A host outside the matrix is refused with an error code:
`openscad_host_version_unsupported` (older), `openscad_host_version_unverified`
(newer), `openscad_host_version_unlisted` (in between, for example `2024.x`) or
`openscad_host_version_unparsable`.

## Without Meshy DCC's installer

```shell
python -m pip install meshy-dcc-openscad
meshy-dcc-openscad install-project /path/to/models --openscad <exe> --sidecar "$(command -v meshy-dcc-openscad)"
meshy-dcc-openscad serve --project /path/to/models --openscad <exe>
```

`MESHY_DCC_OPENSCAD_ALLOWED_ROOTS` (path list with the platform separator)
adds workspace roots after the project, for example a folder of Meshy
downloads. `MESHY_DCC_OPENSCAD_MAX_SOURCE_BYTES` (default 4 MiB) and
`MESHY_DCC_OPENSCAD_MAX_TIMEOUT_SECS` (default 1800) bound each call.

## Diagnostics

The lifecycle verbs probe an OpenSCAD and report structured JSON with stable
exit codes (`0` usable, `10` discovery, configuration, core or version matrix,
`30` receipt, `40` runtime or capability probe):

```shell
meshy-dcc-openscad doctor --executable <exe> --json
meshy-dcc-openscad verify --executable <exe> --json
```

`install`, `status`, `upgrade` and `uninstall` manage an optional receipt
(`~/.meshy-dcc/receipts/openscad.json`, or `--receipt-path`) recording the
verified Python, core and OpenSCAD identities. Meshy DCC's own install does
not use it.

## Troubleshooting

- `openscad_host_version_*`: install an OpenSCAD inside the matrix, then run
  `meshy-dcc install` again.
- On Windows, configure `openscad.exe` or `openscad.com`; the console
  launcher is chosen automatically when it sits next to the `.exe`.
- A path outside the workspace roots is refused; copy inputs into the
  project or add a root with `MESHY_DCC_OPENSCAD_ALLOWED_ROOTS`.
- The real-OpenSCAD test runs only with an explicit executable:
  `OPENSCAD_TEST_EXECUTABLE=<exe> python -m pytest tests/test_bridge.py -m openscad -q`,
  using `examples/production_smoke.scad`.
