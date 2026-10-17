# Project guidance

`meshy-dcc-zbrush` is the Meshy-owned ZBrush adapter for Meshy DCC Core, a
directory of `meshy-dev/meshy-dcc-adapters`. It began as a fork of an
MIT-licensed project and has fully diverged from it. It tracks no upstream
and shares no names with one. Keep `LICENSE` and `NOTICE` intact.

- Python package `meshy_dcc_zbrush` (the sidecar that serves MCP and talks to
  ZBrush). The bridge ZBrush runs is `bridge/plugin/mcp_socket_bridge.py`;
  the wheel carries it as `meshy_dcc_zbrush/plugin/mcp_socket_bridge.py`. It
  is stdlib only: ZBrush's embedded Python cannot load Core.
- The sidecar runs on the `meshy_dcc_core` wheel; its range is in
  `pyproject.toml` and `install_lifecycle.MINIMUM_CORE`, and the Install SOP
  schema digest per Core release is in `install_contract.py`.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Not verified on a real ZBrush. Real-host checks use a test-owned project
  folder and an isolated `MESHY_DCC_REGISTRY_DIR`, `MESHY_DCC_DATA_DIR` and
  gateway port, and never touch a user's ZBrush files or settings.

Tests: install the `meshy_dcc_core` wheel and this package (`pip install
--no-deps -e .`) into a venv, then `PYTHONPATH=src:. python -m pytest tests`
and `python tools/lint_skills.py`. Package: `packaging/build_package.py`.
Local commits only; do not push or publish unless the user asks.
