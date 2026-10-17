# Project guidance

`meshy-dcc-substance3d-painter` is the Meshy-owned Adobe Substance 3D Painter
adapter for Meshy DCC Core, one directory of the `meshy-dcc-adapters`
repository. It began as a fork of an MIT-licensed project and has fully
diverged from it. It tracks no upstream and shares no names with one. Keep
`LICENSE` and `NOTICE` intact.

- Painter runs the adapter on its own embedded Python (3.9 on Painter 8.1-10.0,
  3.11 on 10.1-11, 3.13 on 12). Keep the code importable on 3.9; the core wheel
  is abi3.
- `install_cli.py` writes a single startup loader into the user's Painter
  profile (`<Documents>/Adobe/Adobe Substance 3D Painter/python/startup/`) that
  puts the package's `plugin/python` on `sys.path`. It never touches a file it
  did not write. `packaging/build_package.py` builds the package with a pinned
  python-build-standalone CPython for the installer only.
- Painter API calls happen on the Qt main thread through
  `PainterQtDispatcher`; tools declare `affinity: main`. Unsaved state comes
  from `substance_painter.project.needs_saving()`; `_safe_stop` refuses while
  it is true or unknown.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Not verified on a real Painter yet. Say so in docs, and only document
  behavior that a test or the source confirms. Real-host checks must point
  `MESHY_DCC_SUBSTANCE3D_PAINTER_PROFILE`, `MESHY_DCC_REGISTRY_DIR` and
  `MESHY_DCC_DATA_DIR` at test-owned folders and never touch the user's
  Documents profile.

Tests: install the `meshy_dcc_core` wheel (`--no-deps`), `pytest pytest-xdist
pyyaml jsonschema` into a venv, then `PYTHONPATH=src python -m pytest tests`
and `PYTHONPATH=src python tools/lint_skills.py`.
Local commits only; do not push or publish unless the user asks.
