# Project guidance

`meshy-dcc-houdini` is the Meshy-owned SideFX Houdini adapter for Meshy DCC
Core, a directory of the `meshy-dev/meshy-dcc-adapters` repository. It began
as a fork of an MIT-licensed project and has fully diverged from it. It tracks
no upstream and shares no names with one. Keep `LICENSE` and `NOTICE` intact.

- Python package `meshy_dcc_houdini`; dcc type `houdini`; environment
  variables `MESHY_DCC_HOUDINI_*`.
- Not verified on a real Houdini yet: say so wherever support is described,
  and only describe behavior read from the source or SideFX documentation.
- The release package (`packaging/build_package.py`) carries the adapter and
  the `meshy_dcc_core` wheel from meshy-dcc-core in `lib/`, startup files in
  `houdini/`, and a CPython that only runs the registration step
  (`src/meshy_dcc_houdini/houdini_package.py`, standard library only). The
  registration writes one Houdini package file into the user preferences;
  nothing goes into the Houdini installation.
- The core range is `>=0.2.0,<0.3.0` in `pyproject.toml`,
  `packaging/build_package.py`, `src/meshy_dcc_houdini/_installer.py` and the
  skills' `compatibility`; keep them in step.
- Startup uses `pythonX.Ylibs/uiready.py` only. Do not ship `123.py` or
  `456.py`: Houdini runs the first one on its path, which would hide the
  user's own.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Real-host checks use an isolated `HOUDINI_USER_PREF_DIR`,
  `MESHY_DCC_REGISTRY_DIR` and `MESHY_DCC_DATA_DIR` and never touch a user's
  Houdini preferences or scenes.

Tests: `python -m pytest tests` with the `meshy_dcc_core` wheel and this
directory (`pip install --no-deps -e .`) installed; `python tools/lint_skills.py` for the bundled skills. Local commits
only; do not push or publish unless the user asks.
