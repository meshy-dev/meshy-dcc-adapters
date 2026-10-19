# Project guidance

`meshy-dcc-3dsmax` is the Meshy-owned 3ds Max adapter for Meshy DCC Core, a
directory of the `meshy-dcc-adapters` repository. It began as a fork of an
MIT-licensed project and has fully diverged from it. It tracks no upstream and
shares no names with one. Keep `LICENSE` and `NOTICE` intact.

- 3ds Max runs only on Windows. The adapter runs on 3ds Max's own Python
  (`pymxs`); `meshy_dcc_core` is a cp38-abi3 wheel, so 3ds Max 2023 or newer
  (Python 3.9+) can load it. The target is 3ds Max 2025/2026 (Python 3.11).
- `src/meshy_dcc_3dsmax/max_bootstrap.py` starts the adapter inside 3ds Max:
  an in-process MCP server that registers with the `meshy-dcc` gateway, plus a
  Qt-timer pump that runs tools on the main thread. Exactly one consumer
  drains the main-thread queue; never add a second thread or timer that pulls
  from it. `pymxs` is only touched on the main thread.
- `packaging/build_package.py` builds the Windows package: the adapter and
  `meshy_dcc_core` in `payload/`, a bundled CPython for the installer, and
  `bin/meshy-dcc-3dsmax.cmd`. `src/meshy_dcc_3dsmax/host_install.py` (stdlib
  only) writes or removes the startup script in the 3ds Max user startup
  folders; nothing goes into the 3ds Max install directory.
- `install_cli.py` and `packaging/assemble_mzp.py` are the pip and drag-and-drop
  installers carried over from the original project. They expect
  `meshy-dcc-core` and `meshy-dcc-server` on PyPI, which Meshy does not
  publish, so the Meshy package does not use them.
- The core range is declared in `pyproject.toml`, `install_cli.py` and the
  MAXScript templates; keep them in step.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Checked in one real 3ds Max, 2027: install, start, Meshy FBX import with a
  Physical material, save, safe stop, reopen, uninstall. 3ds Max 2027 uses
  OCIO colour management by default. Mark anything else as read from source.

Tests: install the `meshy_dcc_core` wheel (`--no-deps`) and `pytest
pytest-xdist pytest-mock packaging pyyaml jsonschema build hatchling pip` into
a venv, then `PYTHONPATH=src:tests python -m pytest tests -n 2 -o addopts=""
-m 'not e2e and not packaging and not integration'`.
Local commits only; do not push or publish unless the user asks.
