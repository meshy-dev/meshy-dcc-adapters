# Changelog

## Unreleased

- Packaging: `build_package.py` reuses its cached CPython only when the
  interpreter is there. An empty cache directory produced a package without
  Python, whose installer then failed.
- `import_to_scene` reports materials it lost instead of `as_authored`. The
  result's `extra.materials_lost` counts the materials the carrier declares
  minus the material nodes that reached the scene, and `status` is
  `as_authored` only when it is 0. A truncated GLB, a USD stage that will not
  open, and a USD material with no readable `UsdPreviewSurface` (Arnold or
  MaterialX surfaces, or no `diffuseColor`) are `carrier_unreadable` with a
  `material_fallback` warning; the readable materials of a partly readable
  stage are still imported. A material no node could be created for is
  `import_incomplete`.
- `import_to_scene` sets metallic, roughness and opacity on the materials it
  builds. A single value never reached the Houdini parm, so these materials
  kept Houdini's defaults and every import warned that the shader does not
  expose those parms.

## 0.1.0 (2026-10-19)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from. Not verified on a real Houdini yet.

- Meshy-owned adapter:
  - Python package and environment variables are renamed to
    `meshy_dcc_houdini` / `MESHY_DCC_HOUDINI_*`;
  - the adapter builds against `meshy_dcc_core` 0.2.x.
- `packaging/build_package.py` builds the Meshy DCC package for macOS arm64
  and Windows x64: the adapter and `meshy_dcc_core` in `lib/`, startup files
  in `houdini/`, and a pinned CPython for the registration step. The
  registration (`bin/meshy-dcc-houdini install|uninstall --dcc-path`) writes
  or removes one Houdini package file in the user preferences.
- Startup runs from `pythonX.Ylibs/uiready.py` only, in interactive sessions.
  The quickinstall's `123.py` / `456.py` hooks are gone: Houdini runs only the
  first of each on its path, so they hid a user's own scripts.
- A Houdini launched by `meshy-dcc start-instance` advertises a safe stop that
  refuses while the scene has unsaved changes unless the request carries
  `discard_unsaved`.
- The live e2e smoke runner moves to `tools/run_houdini_e2e.py`.
