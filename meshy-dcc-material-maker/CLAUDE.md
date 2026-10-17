# Project guidance

`meshy-dcc-material-maker` is the Meshy-owned Material Maker adapter for Meshy
DCC Core, a directory of the `meshy-dev/meshy-dcc-adapters` repository. It
began as a fork of an MIT-licensed project and has fully diverged from it. It
tracks no upstream and shares no names with one. Keep `LICENSE` and `NOTICE`
intact.

- Python package `meshy_dcc_material_maker`, dcc type `material-maker`. Material
  Maker has no plug-in interface: the package is a standalone sidecar (bundled
  CPython, `packaging/build_package.py`) bound to one project folder. It edits
  `.ptex` graphs itself (`graph.py`) and exports through Material Maker's
  `--export-material` command line (`bridge.py`). No `--headless`: Material
  Maker 1.7 crashes with it on macOS.
- `install-project` (`project_install.py`) writes the folder's `.meshy-dcc/`
  launch plan, config and receipt; the catalog's `project_steps` run it.
- Core range `meshy-dcc-core>=0.2.0,<0.3.0` in `pyproject.toml`, `install.py`
  (`MIN_CORE_VERSION`) and the skill's `compatibility`; keep them in step.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Real-host checks use a test-owned folder, an isolated `HOME` /
  `CFFIXED_USER_HOME` (Material Maker writes `~/Library/Application
  Support/material_maker_2`), and isolated `MESHY_DCC_*` registry, data and
  gateway port.

Tests: install the `meshy_dcc_core` wheel and this package (`pip install
--no-deps -e .`) into a venv, then `PYTHONPATH=src:. python -m pytest tests`
and `python tools/lint_skills.py`. Local commits only; do not push or publish
unless the user asks.
