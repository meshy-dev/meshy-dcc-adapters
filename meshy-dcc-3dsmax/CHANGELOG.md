# Changelog

## 0.1.3 (unreleased)

- Native values are no longer mistaken for methods. Every pymxs value is
  callable, so `set_object_property` and `scene_patch` refused to write a
  property whose value is a Point3 or a Name ("Refusing to overwrite a
  method"), and `get_object_properties` reported such a property as not
  readable. Only real functions are treated as methods now. The unit names in
  `get_scene_info`, `get_scene_metadata` and the context snapshot are read the
  same way as in the scene status instead of being called.
- Spline tools close and open splines with 3ds Max's own `close` and `open`.
  `draw_spline`, `curve_model`, `edit_curve` and the spline helper called
  `closeSpline` and `openSpline`, which 3ds Max does not have, so closing a
  spline failed. `draw_spline` in append or replace mode now puts the original
  shape back (knots, tangent handles, closed flag and name) when drawing fails,
  and reports `rolled_back` only after reading the restored shape back.
- `set_timeline_settings` sets the frame rate before the range, because 3ds Max
  keeps the range in ticks and a range set first lands on other frames once the
  rate changes. It reads the timeline back, fails when the host did not keep the
  values, and puts the original settings back (`restored` says whether they read
  back). A frame rate that is zero, negative or not finite is rejected.
- New tool `3dsmax-scene__set_scene_units` sets the system unit type and scale
  before modeling. It only works on an empty scene, does not rescale anything
  or touch the display units, reads the values back, and puts the original
  units back (reporting `rollback_verified`) when a write fails or does not
  stick.
- `create_camera` checks the lens it was asked for. A Physical camera is built
  with 3ds Max's own `Physical` class and its focal length is read back through
  the native getter; a target or free camera has no millimetre lens, so the
  millimetres are converted to a field of view with the scene's render aperture
  width (never an assumed 36 mm) and read back as that. A `focal_length` that is
  not a positive number, or an aperture the host cannot report, is refused
  before any node is created, and a lens that does not read back removes the
  camera and target the call created (`rolled_back`). `list_cameras` reports the
  same millimetre value.
- `create_object` verifies the final position after rotation and scale (a world
  rotation can move the node, so the position is applied last) and deletes the
  node it created when naming, rotation, scale or placement fails, so retrying
  no longer leaves orphan nodes. The result reports `rolled_back`.
- Arnold lights are bound to MAXtoA's own controls. The shape table was
  numbered 0 to 3, but MAXtoA numbers its light shapes sphere 0, distant 1,
  spot 2, quad 3, disk 4, cylinder 5, skydome 6, photometric 7, mesh 8, so a
  `quad` request wrote a sphere. The light is built with `Arnold_Light`, and the
  shape, quad size and radius go through `shapeType`, `quadX`/`quadY` and
  `lightRadius`; `list_lights` reads `on` before `enabled`.

## 0.1.2 (2026-11-03)

- Rebuild with meshy-dcc-core 0.2.3 for the corrected macOS native wheel,
  launch target isolation and managed request/lifecycle integration.

## 0.1.1 (2026-10-28)

- `3dsmax-mesh-ops` loads again: `inspect_mesh` and `pick_component` declared
  `tool_role: inspection`, which meshy-dcc-core does not accept, so the skill
  registered none of its 25 tools. Both are `read_only`. A new test loads every
  bundled skill through core's loader and checks it registers every tool its
  `tools.yaml` declares.
- `create_box` builds a box of the requested depth. It passed `depth`, which a
  3ds Max Box does not have (its third size is `length`), so every box was 25
  units long, and the result echoed the requested sizes instead of reading the
  box back.
- Rebuilt on meshy-dcc-core 0.2.2: security fixes in the MCP server (rmcp 2.1) and Python bindings (PyO3 0.29), and tool calls whose deadline passes before they start are no longer run.

## 0.1.0 (2026-10-19)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter: the Python package is `meshy_dcc_3dsmax`, environment
  variables are `MESHY_DCC_3DSMAX_*`, and it runs on `meshy_dcc_core` 0.2.x.
- `packaging/build_package.py` builds the Meshy DCC package,
  `meshy-dcc-3dsmax-windows-x64.zip` (Windows only, as 3ds Max is): the adapter
  and `meshy_dcc_core` in `payload/`, a pinned python-build-standalone CPython
  3.11.15 (SHA-256 checked) without `site-packages`, and
  `bin/meshy-dcc-3dsmax.cmd`, which runs `host_install.py` isolated (`-I`).
- `host_install.py` (standard library only) writes `meshy_dcc_3dsmax_startup.ms`
  into the user startup folder of each language the user has started that 3ds
  Max in, and `uninstall` removes it and the menu's macro files. It refuses an
  unknown 3ds Max year, a 3ds Max never started, linked folders and a startup
  script it did not write. The script carries the package path base64-encoded,
  so it stays ASCII whatever the user name.
- 3ds Max starts the adapter through `max_bootstrap.startup()`, which never
  raises into 3ds Max, and stops the server again if the main-thread pump did
  not install (tools would otherwise call `pymxs` from server threads). The default boot mode is now the in-process server
  (`server`) instead of the external sidecar, so the package needs no
  `meshy-dcc-server` binary; the server honours `MESHY_DCC_GATEWAY_PORT` and
  `MESHY_DCC_REGISTRY_DIR`.
- The sidecar mode no longer opens the unauthenticated LAN gateway by default
  (it asked for 0.0.0.0:59765); it is off unless
  `MESHY_DCC_GATEWAY_REMOTE_PORT` is set, as in meshy-dcc-core.
- Safe stop for start-instance launches: refused unless the request carries
  `discard_unsaved`; the quit (`quitMax #noPrompt`) runs on the main-thread
  queue the tool pump drains.
- Physical Material map slots also try `roughness_map` and `metalness_map`, and
  a colour emission map goes to `emit_color_map` first: the names the Meshy
  Send To plugin wires. Unverified on a real 3ds Max.
- The 3ds Max menu and its CUI ids use Meshy's own ids (`0x4D455348`), so they
  never collide with another adapter's menu.
- Removed as leftovers of the original project: release-please and renovate
  configuration, `llms.txt` / `llms-full.txt`, the documentation site, images
  and branding, the CI release-workflow scripts and the tests that read the
  GitHub workflows, and the GitHub release-asset uploader.
