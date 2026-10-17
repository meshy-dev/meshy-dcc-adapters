# Project guidance

`meshy-dcc-freecad` is the Meshy-owned FreeCAD adapter for Meshy DCC Core,
a directory of the `meshy-dev/meshy-dcc-adapters` repository. It began as a
fork of an MIT-licensed project and has fully diverged from it. It tracks no
upstream and shares no names with one. Keep `LICENSE` and `NOTICE` intact.

- Python package `meshy_dcc_freecad`: a standalone service (no FreeCAD GUI)
  that serves MCP, registers with the local `meshy-dcc` registry, and runs
  every tool in a fresh `FreeCADCmd` process (`--safe-mode`, throwaway user
  config) with the packaged `freecad_driver.py`. Documents are `.FCStd` files
  under the allowed roots; each mutating call saves and reads back.
- The service runs on the `meshy_dcc_core` wheel from meshy-dcc-core. Its core
  range is declared in `pyproject.toml` and `doctor.py` (`MIN_CORE_VERSION`);
  keep them in step.
- `freecad_driver.py` and the skill scripts run inside FreeCAD's own Python
  (3.11 in FreeCAD 1.0 and 1.1); the service side runs on Python 3.7+. Host
  support is `compat_matrix.json`; an unlisted FreeCAD is refused.
- Mutating tools read back what they wrote (`write_contract.py`); follow it
  when adding a write tool.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Real-host checks use a test-owned project directory, an isolated
  `MESHY_DCC_REGISTRY_DIR` and an isolated home for FreeCAD, and never touch a
  user's documents or FreeCAD preferences.

Tests: install the `meshy_dcc_core` wheel and this package (`pip install
--no-deps -e .`) into a venv with `pytest pyyaml jsonschema`, then
`python -m pytest tests -m "not freecad"`. Set `FREECAD_TEST_EXECUTABLE` to a
FreeCADCmd to run the real-host lanes (`-m freecad`).
Local commits only; do not push or publish unless the user asks.
