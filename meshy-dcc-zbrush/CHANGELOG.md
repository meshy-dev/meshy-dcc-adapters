# Changelog

## 0.1.3 (2026-11-09)

- A call whose connection resets, closes or times out after the request was
  sent, or whose reply is empty or unreadable, is reported as `-32002` with
  `execution_state: unknown` and `retryable: false`, and is never replayed.
  A failure before the connection is made is still reported as unreachable,
  and a reset after the connection was accepted makes the health probe report
  `blocked`. A blocked verdict on reconnect is no longer reported as "not
  available".
- Requests carry a deadline. A request that waited in the bridge's queue past
  it is refused with `ZBRUSH_REQUEST_EXPIRED` (`executed: false`, safe to
  retry) instead of starting late.
- The ZBrush version is the SDK version number alone. `zbrush_info(1)` is the
  edition (Demo, Beta or Full), which `get_session_info` now reports as
  `zbrush_edition`, with the executable's `zbrush_product_version`. A Full
  edition ZBrush was reported as version `.2`. `verify` now compares the SDK's
  year and the executable's full ProductVersion, so the edition no longer makes
  it fail.
- Rebuild with meshy-dcc-core 0.2.4. A sidecar of the same Core version no
  longer takes over a running gateway, a call that may already have reached
  the app is never replayed, and tools no longer receive an empty `_meta`.

## 0.1.2 (2026-11-03)

- Rebuild with meshy-dcc-core 0.2.3 for the corrected macOS native wheel,
  launch target isolation and managed request/lifecycle integration.

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
