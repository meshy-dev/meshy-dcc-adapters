# Project guidance

`meshy-dcc-unity` is the Meshy-owned Unity Editor adapter for Meshy DCC Core,
kept as a local repository next to `meshy-dcc-core`. It began as a fork of an
MIT-licensed project and has fully diverged from it. It tracks no upstream
and shares no names with one. Keep `LICENSE` and `NOTICE` intact.

- Python package `meshy_dcc_unity` (the sidecar that serves MCP and bridges to
  the Editor); UPM package `ai.meshy.dcc` under
  `src/meshy_dcc_unity/unity_package`. The bridge defaults to
  `ws://127.0.0.1:13852`.
- The sidecar runs on the `meshy_dcc_core` wheel from meshy-dcc-core. Its core
  range is declared in `pyproject.toml` and `install.py` (`MIN_CORE_VERSION`);
  keep them in step.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Real-host checks use a test-owned Unity project and an isolated
  `MESHY_DCC_REGISTRY_DIR`, and never touch a user's projects or Editor
  preferences.

Tests: install the `meshy_dcc_core` wheel and this package (`pip install
--no-deps -e .`) into a venv, then `PYTHONPATH=src:. python -m pytest tests`.
Local commits only; do not push or publish unless the user asks.
