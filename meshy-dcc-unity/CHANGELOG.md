# Changelog

## 0.1.1 (2026-10-28)

- Rebuilt on meshy-dcc-core 0.2.2: security fixes in the MCP server (rmcp 2.1) and Python bindings (PyO3 0.29), and tool calls whose deadline passes before they start are no longer run.

## 0.1.0 (unreleased)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter:
  - the Python package is `meshy_dcc_unity`, the UPM package is
    `ai.meshy.dcc`, and environment variables are `MESHY_DCC_UNITY_*`;
  - the sidecar runs on `meshy_dcc_core` 0.2.x;
  - the Editor bridge defaults to port 13852.
- `install --python` accepts a venv interpreter; it no longer follows the
  symlink out of the venv.
- `packaging/build_package.py` builds the Meshy DCC package: a relocatable
  CPython with `meshy_dcc_core`, this adapter and `websockets`, plus
  `bin/meshy-dcc-unity-sidecar`. Unity needs no Python of its own.
- `install --sidecar <path>` records the project's start-instance launch plan
  (the Editor matching `ProjectVersion.txt`) and the sidecar in
  `.meshy-dcc/`, which ignores itself for version control. `--files-only`
  skips the live readiness check. `uninstall` removes both files.
- Project installs leave out the package's NUnit `Tests/`. Unity compiles an
  embedded package's tests, which fails in projects without the Unity Test
  Framework.
- The Editor package starts the recorded sidecar and gives each Editor its own
  bridge port, so several Editors can run at once.
- `meshy-unity` skill: session, model inspect and instantiate with a keyed PBR
  texture set, object and renderer readback, save and open scene.
- An Editor launched by `meshy-dcc start-instance` advertises a safe stop. It
  exits when every scene is saved and refuses otherwise, unless the request
  carries `discard_unsaved`.
