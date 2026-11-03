# Changelog

## 0.1.1 (2026-10-28)

- Rebuilt on meshy-dcc-core 0.2.2: security fixes in the MCP server (rmcp 2.1) and Python bindings (PyO3 0.29), and tool calls whose deadline passes before they start are no longer run.

## 0.1.0 (2026-10-19)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from. Experimental: not verified on a real ZBrush.

- Meshy-owned adapter: the Python package is `meshy_dcc_zbrush`, environment
  variables are `MESHY_DCC_ZBRUSH_*`, and the sidecar runs on
  `meshy_dcc_core` 0.2.x. A hand-copied bridge listens on 19876.
- `setup-project <folder> --dcc-path <ZBrush>` checks ZBrush (2026.1+,
  signed by Maxon) and writes `<folder>/.meshy-dcc/launch-plan.json`, which
  starts `ZBrush -script` with the packaged bridge. Nothing is written into
  the ZBrush installation or its settings.
- The bridge takes a free loopback port, starts the sidecar from the package's
  Python (`serve --watch-pid <ZBrush> --socket-port <port>`), and requires a
  per-launch token in every request. The sidecar exits with ZBrush.
- The sidecar runs tools inline: the bridge already puts every SDK call on the
  ZBrush main thread. Before, every tool failed with
  `THREAD_AFFINITY_UNAVAILABLE` on meshy-dcc-core 0.2.
- New `zbrush-file` skill: `save_project` (.zpr), `save_tool` (.ztl) and
  `open_project`. Saves refuse an existing file unless `overwrite` is set and
  put the old file back when ZBrush writes nothing.
- Safe stop for `start-instance` launches: ZBrush cannot report unsaved
  changes, so a stop needs `discard_unsaved`; it then ends the watched ZBrush.
- `packaging/build_package.py` builds `meshy-dcc-zbrush-<platform>.zip` for
  macOS arm64 and Windows x64 with CPython 3.11.15 (python-build-standalone
  20260504) and `bin/meshy-dcc-zbrush`.
