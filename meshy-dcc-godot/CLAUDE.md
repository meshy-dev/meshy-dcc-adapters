# Project guidance

`meshy-dcc-godot` is the Meshy-owned Godot editor adapter for Meshy DCC Core,
kept as a local repository next to `meshy-dcc-core`. It began as a fork of an
MIT-licensed project and has fully diverged from it. It tracks no upstream
and shares no names with one. Keep `LICENSE` and `NOTICE` intact.

- Python package `meshy_dcc_godot` (the sidecar that serves MCP and bridges to
  the editor); the GDScript EditorPlugin lives under
  `src/meshy_dcc_godot/godot_addon/addons/meshy_dcc_godot` and installs into a
  project's `addons/`. The bridge defaults to `ws://127.0.0.1:13847`.
- The sidecar runs on the `meshy_dcc_core` wheel from meshy-dcc-core. Its core
  range is declared in `pyproject.toml` and `install.py` (`MIN_CORE_VERSION`,
  `MAX_CORE_VERSION`); keep them in step.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Real-host checks use a test-owned Godot project and an isolated
  `MESHY_DCC_REGISTRY_DIR`, and never touch a user's projects or editor
  settings.

Tests: install the `meshy_dcc_core` wheel and this package (`pip install
--no-deps -e .`) into a venv, then `PYTHONPATH=src:. python -m pytest tests`.
Local commits only; do not push or publish unless the user asks.
