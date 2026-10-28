# Changelog

## 0.1.1 (2026-10-28)

- Rebuilt on meshy-dcc-core 0.2.2: security fixes in the MCP server (rmcp 2.1) and Python bindings (PyO3 0.29), and tool calls whose deadline passes before they start are no longer run.

## 0.1.0 (2026-10-19)

First release, experimental: not yet verified in a real Roblox Studio.

- Studio plugin `MeshyDcc.lua` and a Python sidecar on `meshy_dcc_core` 0.2.x,
  joined by a loopback WebSocket on ports 13890-13893. The sidecar binds only
  the plugin of the place it was started for and refuses browser origins.
- `install --project <dir>` writes the plugin to Studio's local plugins folder
  and binds the project to its place file (or `--place-id`/`--universe-id`);
  `launch` opens the place in Studio for `meshy-dcc start-instance`.
- Skills `roblox-scene` (scene tree, inspect, create, set properties, move,
  delete, and Luau that the user must allow in Studio) and `meshy-roblox`
  (GLB import into MeshParts with a PBR SurfaceAppearance, readback; optional
  upload to the user's inventory so the model persists).
- Packages for macOS arm64 and Windows x64 with their own CPython 3.11.
