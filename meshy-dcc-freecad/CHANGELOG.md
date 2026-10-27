# Changelog

## Unreleased

- A tool that writes a document or an export (`create_document`, `save_copy`,
  `export_geometry` and every editing tool) no longer publishes the file when
  the FreeCAD child exits non-zero after writing its result. The call fails
  with the exit code and the child's stderr, the user's file is untouched, and
  the call is not replayed. Read-only calls still report `exit_code` as before.

## 0.1.0 (2026-10-19)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter: the Python package is `meshy_dcc_freecad`, the command
  is `meshy-dcc-freecad`, and environment variables are `MESHY_DCC_FREECAD_*`.
- Runs on `meshy_dcc_core` 0.2.x.
- `packaging/build_package.py --platform {macos-arm64,windows-x64}` builds the
  Meshy DCC package: CPython 3.11.15 (python-build-standalone 20260504, pinned
  by digest) with `meshy_dcc_core` and this adapter, plus
  `bin/meshy-dcc-freecad` (`.cmd` on Windows).
- `install --project <dir> --dcc-path <FreeCAD>` finds FreeCADCmd from the app
  bundle, `FreeCAD.exe` or FreeCADCmd, runs `verify` against it and writes the
  project's start-instance launch plan to `.meshy-dcc/` (which ignores itself);
  `uninstall` removes it. It refuses a project whose launch plan belongs to
  another adapter.
- `serve --project <dir> --freecad <FreeCADCmd>` makes the project the only
  allowed root and registers the FreeCAD version. On Windows the service runs
  on `pythonw.exe`, so it opens no console.
- A service launched by `meshy-dcc start-instance` advertises a safe stop.
  Every call saves, so there is no unsaved work; a stop is refused while a
  FreeCAD call runs unless it carries `discard_unsaved`, which cancels the call
  before it replaces its document. The service exits once no call is running,
  and refuses new FreeCAD calls meanwhile.
- `import_geometry` takes GLB (what Meshy exports): it lands as a mesh in
  millimetres and Z-up, without materials, and is checked against the file's
  triangle count. `.gltf` is refused, since its side files could sit outside
  the allowed roots.
- `render_view` refuses on macOS with `render_host_limited`, and
  `get_capabilities` reports it `host_limited` there: Qt's offscreen platform
  has no OpenGL context on macOS, and FreeCADCmd crashed instead of rendering.
