# Project guidance

`meshy-dcc-maya` is the Meshy-owned Autodesk Maya adapter for Meshy DCC Core,
a directory of the `meshy-dev/meshy-dcc-adapters` repository. It began as a
fork of an MIT-licensed project and has fully diverged from it. It tracks no
upstream and shares no names with one. Keep `LICENSE` and `NOTICE` intact.

- Python package `meshy_dcc_maya`; Maya plug-in `meshy_dcc_maya_plugin`
  (`maya/plugin/`); module-scoped `maya/userSetup.py`, which loads the
  plug-in when Maya starts; dcc type `maya`.
- `packaging/build_package.py` builds the Meshy DCC package: a Maya module
  (`module/plug-ins`, `module/scripts`, and this adapter with
  `meshy_dcc_core` in `module/python`), a pinned CPython for the installer,
  and `bin/meshy-dcc-maya`, which runs `module_install.py`. That installer is
  standard-library only and writes or removes one file,
  `meshy_dcc_maya.mod`, in the user's Maya modules folder. Never touch the
  user's own `userSetup.py`, `Maya.env` or preferences.
- The core range is `meshy-dcc-core>=0.2.0,<0.3.0`, declared in
  `pyproject.toml`, `install.py` (`MIN_CORE_VERSION`, `MAX_CORE_VERSION`) and
  the setup skill; keep them in step. `tests/test_core_dependency_contract.py`
  checks the documents.
- Maya calls run on Maya's main thread; tools declare `affinity: main`.
- Defaults that would change every Maya session the artist starts stay
  opt-in: the sidecar (`MESHY_DCC_MAYA_SIDECAR=1`), turning AutoSave off
  (`MESHY_DCC_MAYA_DISABLE_AUTOSAVE=1`) and commandPort hygiene
  (`MESHY_DCC_MAYA_COMMANDPORT_HYGIENE=1`).
- Host-specific behavior belongs here, not in meshy-dcc-core.

Not verified on a real Maya yet. Tests run against stand-ins for `maya.cmds`:
install the `meshy_dcc_core` wheel and this package (`pip install --no-deps
-e .`) into a venv, then `python -m pytest tests` and
`python tools/lint_skills.py`. Point `HOME`, `MESHY_DCC_REGISTRY_DIR`,
`MESHY_DCC_DATA_DIR` and `MESHY_DCC_GATEWAY_PORT` at test-owned places first:
the tests start servers, write logs and job stores, and join gateway
elections. Local commits only; do not push or publish unless the user asks.
