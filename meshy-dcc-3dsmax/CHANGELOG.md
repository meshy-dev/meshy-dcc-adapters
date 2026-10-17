# Changelog

## 0.1.0 (unreleased)

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
  raises into 3ds Max. The default boot mode is now the in-process server
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
