# Project guidance

`meshy-dcc-roblox` is the Meshy-owned Roblox Studio adapter for Meshy DCC
Core, a directory of `meshy-dev/meshy-dcc-adapters`. It was written for Meshy
and derives from no other project.

- Python package `meshy_dcc_roblox` is the sidecar: it serves the Meshy DCC
  tools and bridges to the Studio plugin `plugin/MeshyDcc.lua` over a loopback
  WebSocket on ports 13890-13893 (`PORTS` in `bridge.py` and the plugin must
  match). The plugin is one Luau file installed into Studio's local plugins
  folder; it holds every Studio API call.
- The sidecar runs on the `meshy_dcc_core` wheel from meshy-dcc-core; its range
  is declared in `pyproject.toml`.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Never copy credentials from other Roblox integrations; the adapter uses no
  Open Cloud key. Uploads happen only through `publish: true`.
- Real-host checks need the user's logged-in Studio and write the plugin into
  their plugins folder; ask first, use a test-owned place file, remove the
  plugin afterwards unless the user keeps it.

Tests: install the `meshy_dcc_core` wheel and this package (`pip install
--no-deps -e .`) plus `pytest websockets pillow` into a venv, then
`python -m pytest tests` and `python tools/lint_skills.py`.
Local commits only; do not push or publish unless the user asks.
