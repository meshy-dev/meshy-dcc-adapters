# Changelog

## 0.1.0 (2026-10-19)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from. Not verified on a real Maya yet.

- Meshy-owned adapter:
  - the Python package is `meshy_dcc_maya`, the plug-in
    `meshy_dcc_maya_plugin`, and environment variables are
    `MESHY_DCC_MAYA_*`;
  - the adapter runs on `meshy_dcc_core` 0.2.x and Python 3.8+.
- `packaging/build_package.py --platform {macos-arm64,windows-x64}` builds
  the Meshy DCC package: a Maya module (plug-in, a module-scoped
  `userSetup.py`, and this adapter with `meshy_dcc_core` and `packaging` on
  its `PYTHONPATH`), a pinned python-build-standalone CPython 3.11.15 (its
  SHA-256 checked) for the installer, and `bin/meshy-dcc-maya`. It replaces
  the module-ZIP assembly, which downloaded core from PyPI, and its
  install scripts, which edited the user's `userSetup.py`.
- `bin/meshy-dcc-maya install` writes one file, `meshy_dcc_maya.mod`, into
  the user's Maya modules folder (`$MAYA_APP_DIR/modules`, or the per-user
  default; on Windows the Documents known folder); `uninstall` removes it,
  only if Meshy DCC wrote it.
- A Maya launched by `meshy-dcc start-instance` advertises a safe stop. It
  quits with `cmds.quit(force=True)` only when the scene is saved or the
  request carries `discard_unsaved`; a main thread that does not answer
  in 30 s counts as unsaved.
- New `meshy-maya` skill: `import_model` imports a Meshy FBX or OBJ under a
  new group and builds a `standardSurface` from Meshy's texture set (colour
  maps sRGB, data maps Raw, a packed metallic-roughness map read as glTF:
  green roughness, blue metalness); `inspect_model` reads it back.
- Off by default, since the module loads in every Maya session the user
  starts: the `meshy-dcc-server` sidecar and its LAN listener
  (`MESHY_DCC_MAYA_SIDECAR=1`), turning AutoSave off
  (`MESHY_DCC_MAYA_DISABLE_AUTOSAVE=1`), and closing the default
  commandPort and turning off its security warning
  (`MESHY_DCC_MAYA_COMMANDPORT_HYGIENE=1`).
- Job history: the default store is core's per-process database; a shared
  `<data>/meshy-dcc-maya/jobs.db` let only one Maya session start. An
  explicit `job_storage_path` or `MESHY_DCC_MAYA_JOB_STORAGE` now reaches
  core, and `""` turns persistence off.
