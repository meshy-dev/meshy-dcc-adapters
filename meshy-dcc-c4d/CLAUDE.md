# Project guidance

`meshy-dcc-c4d` is the Meshy-owned Cinema 4D adapter for Meshy DCC Core. It
began as a fork of an MIT-licensed project and has fully diverged from it. It
tracks no upstream and shares no names with one. Keep `LICENSE` and `NOTICE`
intact.

- Python package `meshy_dcc_c4d`, dcc type `c4d`, environment variables
  `MESHY_DCC_C4D_*`.
- The adapter never runs inside the Cinema 4D GUI. Its service runs in its own
  Python on the `meshy_dcc_core` wheel and starts Maxon's licensed headless
  `c4dpy` once per operation with the packaged driver
  (`cinema4d_driver.py`), which only handles allowlisted methods. Tools work on
  `.c4d` files inside the allowed roots, not on a scene open in the GUI.
- The core range is declared in `pyproject.toml` and `install.py`
  (`MINIMUM_CORE_VERSION`); keep them in step.
- Host-specific behavior belongs here, not in meshy-dcc-core.
- Not verified on a real Cinema 4D yet. Keep the tests contract-level and say
  so; never describe a mock as host evidence.

Tests: install the `meshy_dcc_core` wheel and this package (`pip install
--no-deps -e .`) into a venv, then `python -m pytest tests` and
`python tools/lint_skills.py`. Local commits only; do not push or publish
unless the user asks.
