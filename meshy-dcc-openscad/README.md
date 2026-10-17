# meshy-dcc-openscad

The Meshy DCC Core adapter for OpenSCAD: write, inspect, validate, export and
render OpenSCAD models through the bounded `openscad` command line, and stand
Meshy-generated STL models on printable bases.

Verified with the OpenSCAD 2026.10.15 snapshot on macOS arm64: install,
`meshy-dcc start-instance`, writing a `.scad`, STL export with a parameter
change, PNG render, a Meshy model on a print base, calls through the gateway,
restart with read-back, and safe stop. The Windows package is built but has
not run on Windows.

## With Meshy DCC

```bash
meshy-dcc install --dcc-type openscad --project /path/to/models --execute
meshy-dcc start-instance --dcc-type openscad --project /path/to/models --wait-ready --yes
```

The package carries its own CPython with `meshy_dcc_core` and this adapter;
OpenSCAD needs no Python. `install` runs the package's `install-project`, which
checks the OpenSCAD executable (from `--dcc-path` or the usual install
location) against the supported versions and records the project's
start-instance launch plan in `.meshy-dcc/`. The instance is the adapter
process; it needs no OpenSCAD window. Its workspace root is the project
directory, and relative tool paths resolve there. See [`install.md`](install.md).

## Skills

| Skill | Tools |
|---|---|
| `openscad-pipeline` | `get_status`, `get_capabilities`, `inspect_source` (read-only); `write_model_source` (new self-contained `.scad`); `validate_model`, `export_model` (STL, 3MF, AMF, OFF, CSG, DXF, SVG, PDF), `render_preview` (PNG) |
| `meshy-openscad` | `write_print_base`: a new parametric `.scad` that imports a Meshy STL, scales it to a height in mm, centres it and stands it on a round or square base |

`validate_model`, `export_model` and `render_preview` run as jobs; poll
`jobs_get_status`. Parameter overrides are JSON values, never raw `-D`
expressions. Outputs are staged and moved into place only after OpenSCAD
succeeds, existing files are replaced only with `overwrite: true`, and every
mutating tool reads its artifact back before it reports success
([`docs/write-contract.md`](docs/write-contract.md)).

## Supported OpenSCAD

`2021.01.x`, `2026.09.x` and `2026.10.x`, declared in
`src/meshy_dcc_openscad/compat_matrix.json`. Anything else is refused with an
`openscad_host_version_*` error rather than run unverified. 2021.01 is the last
stable release and is Intel-only on macOS; Apple Silicon needs a development
snapshot from openscad.org.

## Development

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python --no-deps <meshy_dcc_core wheel>
uv pip install --python .venv/bin/python pytest pyyaml 'jsonschema>=4.18'
PYTHONPATH=src:. .venv/bin/python -m pytest tests
.venv/bin/python tools/lint_skills.py
uv run --python 3.11 --no-project python packaging/build_package.py \
    --core-wheel <wheel> --platform macos-arm64 --output-dir dist
```

`OPENSCAD_TEST_EXECUTABLE=<exe>` with `-m openscad` runs the real-OpenSCAD
cases on `examples/production_smoke.scad`.
