# Project guidance

`meshy-dcc-unreal` is the Meshy-owned Unreal Editor adapter for Meshy DCC
Core, kept as a local repository next to `meshy-dcc-core`. It began as a fork
of an MIT-licensed project and has fully diverged from it. It tracks no
upstream and shares no names with one. Keep `LICENSE` and `NOTICE` intact.

- `unreal/plugin` is the `MeshyDccUnreal` project plugin: the C++ editor
  module in `Source/` and `Content/Python/init_unreal.py`, which starts the
  server from `src/meshy_dcc_unreal` on the editor's Python. Unreal runs that
  file rather than importing it; it registers itself as
  `meshy_dcc_unreal_init`, so never `import init_unreal`.
- `packaging/build_package.py` builds the Meshy DCC package. The plugin ships
  its C++ source, and its `python/` folder carries this adapter and the
  `meshy_dcc_core` wheel; a bundled CPython runs `install_cli.py`, which copies
  the plugin into a project and builds the module there with the engine's
  build script. Nothing goes into the engine.
- Tools marked `affinity: any` run off the editor thread and must not call
  `unreal` APIs directly; hand those to the dispatcher.
- The core range is declared in `pyproject.toml` and the plugin scripts'
  `min_core_version`; keep them in step.
- Editor-thread work goes through `UnrealMainThreadDispatcher` in
  `server.py`. Unsaved state comes from `_safe_stop.dirty_packages`, which
  separates project packages from engine ones; never save engine packages.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Real-host checks use a test-owned project, an isolated
  `MESHY_DCC_REGISTRY_DIR` and `MESHY_DCC_DATA_DIR`, and a short fake home in
  both `HOME` and `CFFIXED_USER_HOME` (Unreal refuses cache paths over 119
  characters). They never touch a user's projects or editor settings. The Mac
  here has Xcode 27, which Unreal 5.7 refuses to build with; module builds for
  tests go through a test-only Xcode.app whose Info.plist reports 26.9 and whose
  `Developer` links to Xcode 27, via `DEVELOPER_DIR`. Never ship or document
  that as a user path.

Tests: install the `meshy_dcc_core` wheel and this package (`pip install
--no-deps -e .`) into a venv, then `python -m pytest tests`.
Local commits only; do not push or publish unless the user asks.
