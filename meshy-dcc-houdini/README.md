# meshy-dcc-houdini

The Meshy DCC Core adapter for SideFX Houdini 20.5 and later. It runs inside
an interactive Houdini session on Houdini's own Python, registers the session
with the local `meshy-dcc` registry, and exposes 43 bundled skills (296 tools:
scene and node graph, parameters, geometry and mesh operations, import and
export, materials and MaterialX, lookdev, Karma and ROP rendering, animation,
simulation, PDG, HDAs) that agents call through the `meshy-dcc` CLI.

Not verified on a real Houdini yet; experimental. The unit tests run without
Houdini, against stand-ins for `hou`. Nothing below has been checked in a
Houdini session.

## With Meshy DCC

`packaging/build_package.py` builds one zip per platform
(`meshy-dcc-houdini-macos-arm64.zip`, `meshy-dcc-houdini-windows-x64.zip`):

```
houdini/                   joins HOUDINI_PATH: pythonX.Ylibs/uiready.py, toolbar/meshy_dcc.shelf
lib/                       joins PYTHONPATH: this adapter and meshy_dcc_core
python/                    a relocatable CPython that only runs the registration step
bin/meshy-dcc-houdini      registers or removes the package (.cmd on Windows)
```

```bash
meshy-dcc install --dcc-type houdini --execute            # --dcc-path <houdini> when several are installed
meshy-dcc start-instance --dcc-type houdini --wait-ready --yes
```

The install extracts the zip and runs `bin/meshy-dcc-houdini install
--dcc-path <houdini> --json`, which writes one Houdini package file,
`meshy_dcc_houdini.json`, into the preferences of that Houdini version
(`~/Library/Preferences/houdini/<X.Y>/packages` on macOS,
`$HOME/houdini<X.Y>/packages` on Windows, where Houdini's `$HOME` is the
Documents folder unless `HOME` is set; `HOUDINI_USER_PREF_DIR` overrides
both). Nothing is installed into the Houdini application or its Python. See
[install.md](install.md) for the manual path, upgrade and uninstall.

When the UI is ready, `uiready.py` starts the adapter; `123.py` and `456.py`
are not used, so a user's own startup scripts keep running. Background
render and cook processes, and `MESHY_DCC_HOUDINI_AUTOSTART=0`, start
nothing.

A Houdini launched by `start-instance` advertises a safe stop. It reads
`hou.hipFile.hasUnsavedChanges()` on the main thread and refuses while the
scene is unsaved, or when Houdini cannot tell, unless the request carries
`discard_unsaved`; it then exits without the save prompt.

## Requirements

- Houdini 20.5+ on macOS Apple Silicon or Windows x64.
- `meshy-dcc-core >= 0.2.0,<0.3.0` (bundled in the package).

## Development

```bash
uv pip install --no-deps <meshy_dcc_core wheel> -e .
python -m pytest tests
python tools/lint_skills.py
uv run --python 3.11 --no-project python packaging/build_package.py \
    --platform macos-arm64 --core-wheel <meshy_dcc_core wheel> --output-dir dist
```

`tools/run_houdini_e2e.py` is a live smoke test to run inside a licensed
Houdini. `install.md` also describes the older developer install into
`hython`.

## License

MIT source; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
