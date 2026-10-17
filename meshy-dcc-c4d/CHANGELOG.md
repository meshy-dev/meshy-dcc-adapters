# Changelog

## 0.1.0 (unreleased)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter: the Python package is `meshy_dcc_c4d`, the command is
  `meshy-dcc-c4d`, environment variables are `MESHY_DCC_C4D_*`, and the
  adapter registers only as dcc type `c4d`.
- Runs on `meshy_dcc_core` 0.2.x. The lifecycle commands record the
  `meshy-dcc-server` distribution only when it is installed; the Meshy package
  does not ship it.
- `packaging/build_package.py --platform {macos-arm64,windows-x64}` builds
  `meshy-dcc-c4d-<platform>.zip` on any machine: CPython 3.11.15 from
  python-build-standalone 20260504 (checked against the release's SHA-256),
  with `meshy_dcc_core` and this adapter installed for the target platform,
  plus `bin/meshy-dcc-c4d` (`.cmd` on Windows).
- `install --project <folder> --c4dpy <c4dpy>` sets a folder up for
  `meshy-dcc start-instance`: `.meshy-dcc/launch-plan.json` starts
  `python -I -m meshy_dcc_c4d serve --project <folder>` with the package's
  Python, and `.meshy-dcc/c4d.json` records `c4dpy`. It refuses a folder whose
  launch plan belongs to another adapter. `uninstall --project` removes only
  those files.
- `serve --project <folder>` restricts paths to the folder and runs the
  recorded `c4dpy`. A start-instance launch advertises a safe stop; the service
  keeps no document in memory, so it always stops.
- The registered version is the Cinema 4D release read from `c4dpy`'s file
  metadata, not the adapter version.
- Fixed: on macOS, reading `c4dpy.app`'s bundle metadata raised
  `AttributeError`, so `doctor`, `verify` and `install` failed for every
  Cinema 4D there.
- Fixed: the OBJ export read-back rejected files that start with `mtllib`,
  `o`, `g`, `s` or `usemtl` before the first vertex, which the OBJ format
  allows.
