# Project guidance

`meshy-dcc-unreal` is the Meshy-owned Unreal Editor adapter for Meshy DCC
Core, kept as a local repository next to `meshy-dcc-core`. It began as a fork
of an MIT-licensed project and has fully diverged from it. It tracks no
upstream and shares no names with one. Keep `LICENSE` and `NOTICE` intact.

- `unreal/plugin` is the `MeshyDccUnreal` project plugin. It is Python only:
  the descriptor declares no module, and `Content/Python/init_unreal.py`
  starts the server from `src/meshy_dcc_unreal` on the editor's Python. The
  C++ module under `unreal/plugin/Source` is kept but not built or packaged.
- `packaging/build_package.py` builds the Meshy DCC package. The plugin's
  `python/` folder carries this adapter and the `meshy_dcc_core` wheel; a
  bundled CPython runs `install_cli.py`, which copies the plugin into a
  project. Nothing goes into the engine.
- The core range is declared in `pyproject.toml` and the plugin scripts'
  `min_core_version`; keep them in step.
- Editor-thread work goes through `UnrealMainThreadDispatcher` in
  `server.py`. Unsaved state comes from `_safe_stop.dirty_packages`, which
  separates project packages from engine ones; never save engine packages.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Real-host checks use a test-owned project, an isolated
  `MESHY_DCC_REGISTRY_DIR` and `MESHY_DCC_DATA_DIR`, and a short fake home in
  both `HOME` and `CFFIXED_USER_HOME` (Unreal refuses cache paths over 119
  characters). They never touch a user's projects or editor settings.

Tests: install the `meshy_dcc_core` wheel and this package (`pip install
--no-deps -e .`) into a venv, then `python -m pytest tests`.
Local commits only; do not push or publish unless the user asks.
