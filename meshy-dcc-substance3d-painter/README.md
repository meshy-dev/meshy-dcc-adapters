# meshy-dcc-substance3d-painter

The Meshy DCC Core adapter for Adobe Substance 3D Painter. A startup plugin
runs on Painter's own embedded Python, serves the adapter's tools over MCP,
and registers Painter with the local `meshy-dcc` registry; host calls run on
Painter's Qt main thread.

**Experimental: not verified on a real Painter yet.** Everything below is
written from the source and from Adobe's documentation, and checked only with
unit tests, a fake-host contract test, and an install of the package through
`meshy-dcc install` into a throwaway profile. Targets Painter 8.1 and later
(Python 3.9+; Painter 10.1 and 11 run Python 3.11, Painter 12 Python 3.13)
on macOS Apple silicon and Windows x64.

## With Meshy DCC

`packaging/build_package.py` builds the Meshy DCC package for one platform:

```
plugin/python/                      this adapter and meshy_dcc_core (what Painter imports)
python/                             a relocatable CPython 3.11 that runs the installer
bin/meshy-dcc-substance3d-painter   the installer (bin/meshy-dcc-substance3d-painter.cmd on Windows)
```

```bash
meshy-dcc install --dcc-type substance3d_painter --execute
meshy-dcc start-instance --dcc-type substance3d_painter --project /path/to/work --wait-ready --yes
```

The install extracts the package into the Meshy DCC data directory and runs
`bin/meshy-dcc-substance3d-painter install --yes --json`. That writes one
file, the startup loader
`<Documents>/Adobe/Adobe Substance 3D Painter/python/startup/meshy_dcc_substance3d_painter_plugin.py`.
Painter loads every module in that folder when it starts; the loader puts the
package's `plugin/python` folder on `sys.path` and starts the adapter. Nothing
is installed into Painter itself. On Windows, Documents is the shell's
Documents folder, so a OneDrive-redirected one is followed.
`MESHY_DCC_SUBSTANCE3D_PAINTER_PROFILE` points the installer at another
Painter profile (tests use it).

`install`, `uninstall` and `status` only report a plan without `--yes`. The
installer never overwrites or deletes a file of that name that it did not
write (exit 10).

### Without the installer

Painter also reads plugins from `SUBSTANCE_PAINTER_PLUGINS_PATH`. Point it at
`plugin/python/meshy_dcc_substance3d_painter/painter` (the folder holding
`startup/`) and add `plugin/python` to `PYTHONPATH` before starting Painter.

### Uninstall

```bash
<package>/bin/meshy-dcc-substance3d-painter uninstall --yes
```

removes the loader (and the bytecode Painter's Python left next to it). The
package itself lives under the Meshy DCC data directory,
`meshy-dcc/adapters/meshy-dcc-substance3d-painter/` (macOS:
`~/Library/Application Support`, Windows: `%APPDATA%`); delete that folder
after the loader is gone. Without the package, deleting the loader file by
hand is the whole uninstall. Painter picks up either change at its next start.

### Safe stop

A Painter launched by `start-instance` advertises a safe stop. It reads the
open project's state and refuses while the project needs saving, or when
Painter cannot tell, unless the request carries `discard_unsaved`; then it
closes Painter with `substance_painter.application.close()`. A Painter the
user opened is never stopped this way.

## Skills

- `painter-project`: create a project from a mesh, open, save, save as,
  close a clean project, reload the mesh; inspect the project, texture sets
  and layer stack; fill, textured and paint layers, masks, generators, smart
  materials; import resources; bake mesh maps as a job; build an export preset
  and export textures with readback; `execute_materialized_script` for a
  script materialized by core.
- `painter-material`: per-layer channel inventory and uniform channel values.
- `painter-compositing`: layer visibility, opacity, blending mode.
- `painter-lighting`: environment map, exposure and rotation (Painter has no
  light objects).
- `painter-diagnostics`: `ping`, which proves the main-thread bridge answers.

Every mutation reads the value back from Painter before it reports success.

## Development

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python --no-deps <meshy_dcc_core wheel>
uv pip install --python .venv/bin/python pytest pytest-xdist pyyaml 'jsonschema>=4.18'
PYTHONPATH=src .venv/bin/python -m pytest tests -n 2
PYTHONPATH=src .venv/bin/python tools/lint_skills.py
uv run --python 3.11 --no-project python packaging/build_package.py \
    --core-wheel <meshy_dcc_core wheel for the platform> --platform macos-arm64 --output-dir dist
```

`--platform windows-x64` builds the Windows package on any machine with the
`win_amd64` core wheel. Both downloads of python-build-standalone CPython
3.11.15 (release 20260504) are checked against pinned SHA-256 digests.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
