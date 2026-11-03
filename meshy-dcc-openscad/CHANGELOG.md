# Changelog

## 0.1.1 (2026-10-28)

- Rebuilt on meshy-dcc-core 0.2.2: security fixes in the MCP server (rmcp 2.1) and Python bindings (PyO3 0.29), and tool calls whose deadline passes before they start are no longer run.

## 0.1.0 (2026-10-19)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter: the Python package is `meshy_dcc_openscad`,
  environment variables are `MESHY_DCC_OPENSCAD_*`, and it runs on
  `meshy_dcc_core` 0.2.x.
- One instance per project. `install-project <project> --openscad <exe>
  --sidecar <launcher>` checks OpenSCAD against the version matrix and writes
  `<project>/.meshy-dcc/launch-plan.json`; `serve --project <dir> --openscad
  <exe>` runs the adapter with the project as its first workspace root and
  working directory.
- An instance launched by `meshy-dcc start-instance` advertises a safe stop.
  It holds no unsaved state, so a stop for that instance always proceeds.
- The registry reports the OpenSCAD version, not the adapter's.
- OpenSCAD `2026.10.x` joins the supported versions, verified with the
  2026.10.15 snapshot on macOS arm64; the 2026.09.29 snapshot passes the
  real-OpenSCAD tests there too.
- New `meshy-openscad` skill: `write_print_base` stands a Meshy STL on a
  printable base, with its height, base shape and sink depth as parameters
  `export_model` and `render_preview` can override.
- `packaging/build_package.py` builds the macOS arm64 and Windows x64
  packages: a pinned CPython 3.11.15 with `meshy_dcc_core` and this adapter,
  plus `bin/meshy-dcc-openscad-sidecar` (`.cmd` on Windows).
