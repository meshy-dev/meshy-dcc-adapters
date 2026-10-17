# Project guidance

`meshy-dcc-openscad` is the Meshy-owned OpenSCAD adapter for Meshy DCC Core,
one directory of the `meshy-dcc-adapters` repository. It began as a fork of an
MIT-licensed project and has fully diverged from it. It tracks no upstream and
shares no names with one. Keep `LICENSE` and `NOTICE` intact.

- Python package `meshy_dcc_openscad`. OpenSCAD has no embedded Python: the
  adapter is a standalone process that runs the `openscad` CLI, one bounded
  child process per call, and reads every artifact back
  (`docs/write-contract.md`).
- One instance per project directory. `install-project` (run by
  `meshy-dcc install`) writes `<project>/.meshy-dcc/launch-plan.json`;
  `serve` runs the adapter with the project as its first workspace root.
- Supported OpenSCAD versions live in `compat_matrix.json`; add a range only
  after a real-host run, and keep `install.md` and the SKILL compatibility
  lines in step (tests check both).
- Runs on the `meshy_dcc_core` wheel from meshy-dcc-core; the core range is in
  `pyproject.toml` and `doctor.py` (`MINIMUM_CORE_VERSION`).
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Real-host checks use a test-owned project, an isolated
  `MESHY_DCC_REGISTRY_DIR`, and `HOME` / `CFFIXED_USER_HOME` pointed at a test
  directory so OpenSCAD's preferences stay out of the user's.

Tests: install the `meshy_dcc_core` wheel into a venv with `pytest pyyaml
jsonschema`, then `PYTHONPATH=src:. python -m pytest tests` and
`python tools/lint_skills.py`. The real-OpenSCAD cases run with
`OPENSCAD_TEST_EXECUTABLE=<exe> ... -m openscad`.
Local commits only; do not push or publish unless the user asks.
