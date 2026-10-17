# meshy-dcc-c4d

The Meshy DCC Core adapter for Maxon Cinema 4D. It automates `.c4d` documents
through Maxon's licensed headless `c4dpy`; it does not run inside the Cinema 4D
GUI.

**Not verified on a real Cinema 4D yet; experimental.** The tests are
contract-level: they prove the adapter's own logic (path policy, staged writes,
read-back checks, process ownership), not Cinema 4D's behaviour.

## With Meshy DCC

`packaging/build_package.py` builds the Meshy DCC package: a relocatable
CPython 3.11 with `meshy_dcc_core` and this adapter, plus `bin/meshy-dcc-c4d`
(`.cmd` on Windows). Cinema 4D's own Python is only used inside `c4dpy`.

```bash
meshy-dcc install --dcc-type c4d --project /path/to/folder --execute
meshy-dcc start-instance --dcc-type c4d --project /path/to/folder --wait-ready --yes
```

A Cinema 4D project is a working folder. Install extracts the package and runs
`meshy-dcc-c4d install --project <folder> --c4dpy <c4dpy> --yes --json`, which
writes `.meshy-dcc/launch-plan.json` and `.meshy-dcc/c4d.json` (the `c4dpy`
to use) into the folder; `.meshy-dcc/` ignores itself for version control.
`c4dpy` is found in `/Applications/Maxon Cinema 4D */c4dpy.app` on macOS and
`C:/Program Files/Maxon Cinema 4D */c4dpy.exe` or
`C:/Program Files/Maxon/Cinema 4D */c4dpy.exe` on Windows; with several
releases installed, pass the one to use with `--dcc-path`. Nothing is written
into Cinema 4D or its preferences.

`start-instance` runs `python -I -m meshy_dcc_c4d serve --project <folder>`.
The service may read and write only inside that folder, starts `c4dpy` once per
operation, and keeps no document in memory, so a start-instance launch
advertises a safe stop that always stops it. A call still running when the
service stops ends with an unknown outcome; inspect the document before
retrying it.

### Uninstall

1. Stop the service: `meshy-dcc stop-instance --operation-id <id>`.
2. For each folder, run the package's
   `bin/meshy-dcc-c4d uninstall --project <folder> --yes --json`. It removes the
   two files above (and `.meshy-dcc/` when nothing else is in it) and leaves
   every document alone.
3. Delete the package folder `adapters/meshy-dcc-c4d/` and the receipt
   `installs/c4d-*.json` in the Meshy DCC data folder
   (`~/Library/Application Support/meshy-dcc/` on macOS,
   `%APPDATA%\meshy-dcc\` on Windows, or `MESHY_DCC_DATA_DIR`).

## Capabilities

- Discover and report the real Cinema 4D, Python, and API versions.
- Create, inspect, validate, and atomically copy `.c4d` documents.
- Add typed cube, sphere, cylinder, cone, torus, and plane primitives.
- Set absolute translation, HPB rotation, and scale; remove named objects safely.
- Import C4D, OBJ, FBX, glTF/GLB, STL, Alembic, Collada, and 3DS geometry when
  the installed Cinema 4D runtime provides the corresponding importer.
- Export full documents to C4D, OBJ, FBX, glTF/GLB, STL, Alembic, or Collada
  when the installed runtime provides the corresponding exporter.
- Render bounded PNG and JPEG images without a GUI.

The adapter never accepts arbitrary Python source. Every host call executes a packaged,
allowlisted driver in a fresh `c4dpy` process with bounded paths, timeouts, output streams,
and response size. Document mutations use a staged file and atomically replace the durable
document only after a successful host operation.

Format availability depends on the installed Cinema 4D: `get_capabilities` lists the
formats the adapter knows, and a missing importer or exporter fails with a
format-specific error.

## Requirements

- Cinema 4D R23 or newer with a valid license, and the `c4dpy` executable shipped
  with that installation. R21 and R22 ship `c4dpy` with Python 2.7, which cannot
  run the driver.
- Python 3.9 or newer for the service, with `meshy-dcc-core>=0.2.0,<0.3.0`.

## Two interpreters

| Side | Interpreter | Floor | Runs |
| --- | --- | --- | --- |
| Service | the Python the adapter is installed into | 3.9 | MCP server, `install`/`doctor`/`verify`, path and timeout policy, bridge |
| Host | the Python **inside `c4dpy`** | 3 | the packaged driver, which imports `c4d` and touches the document |

## Host versions and read-back

Declared support lives in `src/meshy_dcc_c4d/compat_matrix.json`, keyed on the
integer from `c4d.GetC4DVersion()`. `doctor` and `verify` embed the verdict as
`host_matrix`; a build outside the matrix is rejected explicitly.

Every mutating tool reads its change back before reporting success: document mutations
against the reopened document, exports against their format signature, renders against the
requested dimensions. A mismatch raises an error naming the tool, the check, both
values, and the Cinema 4D build.

## Development

```bash
python -m pip install --no-deps <meshy_dcc_core wheel>
python -m pip install --no-deps -e .
python -m pip install pytest pytest-xdist pyyaml jsonschema
python -m pytest tests
python tools/lint_skills.py
```

Build a package (on any machine; `uv` installs the wheels for the target):

```bash
python packaging/build_package.py --core-wheel <meshy_dcc_core wheel for the platform> \
    --platform macos-arm64 --output-dir dist
```

On a machine with a licensed Cinema 4D, the opt-in host test runs the full
create, add, transform, remove, copy, export, render, inspect and validate path:

```bash
C4D_TEST_EXECUTABLE=/path/to/c4dpy python -m pytest -m cinema4d
```

Official references: [c4dpy manual](https://developers.maxon.net/docs/py/2025_1_0/manuals/manual_py_c4dpy.html),
[Cinema 4D Python SDK](https://developers.maxon.net/docs/py/index.html).
