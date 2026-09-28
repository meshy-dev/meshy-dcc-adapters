# Project guidance

`meshy-dcc-blender` is the Meshy-owned Blender adapter for Meshy DCC Core,
kept as a local repository next to `meshy-dcc-core`. It began as a fork of an
MIT-licensed project and has fully diverged from it. It tracks no upstream
and shares no names with one. Keep `LICENSE` and `NOTICE` intact.

- Python package `meshy_dcc_blender`; Blender extension id `meshy_dcc_blender`.
- The extension embeds the `meshy_dcc_core` wheel from meshy-dcc-core. Its
  core range is declared in `pyproject.toml`, `packaging/assemble_zip.py`,
  `src/meshy_dcc_blender/_core_compat.py` and `install.py`; keep them in step.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Real-host checks use an isolated `BLENDER_USER_RESOURCES` and
  `MESHY_DCC_REGISTRY_DIR` and never touch a user's Blender preferences or
  projects.

Tests: `PYTHONPATH=src python -m pytest tests --ignore=tests/e2e` with the
`meshy_dcc_core` wheel installed. Local commits only; do not push or publish
unless the user asks.
