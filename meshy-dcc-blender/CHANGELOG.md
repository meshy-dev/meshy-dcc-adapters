# Changelog

## 0.1.3 (unreleased)

- Readiness turns green only after a probe has actually run on Blender's
  main-thread pump. A server started without a dispatcher, such as the one the
  startup script launches, now gets one (the missing `is_background` check made
  that setup fail silently, leaving main-thread tools unable to load), and the
  pump is started with it.
- Import and export no longer report success when Blender did not finish the
  operator or wrote nothing. A cancelled import or export is an error, an export
  must leave a non-empty file, and the basic OBJ writer is used only when
  Blender has no OBJ exporter and no options were requested (it used to hide
  any exporter failure).
- `import_to_scene` fails when the import adds no objects, and
  `material_mode=skip` now clears the materials on the imported meshes (it
  raised after the objects were already in the scene).
- `append_from_blend` and `link_from_blend` report the data blocks Blender
  actually loaded, including collision suffixes, and can load node groups.
- USD import applies the texture and subdivision options under the names Blender
  uses, so textures are imported by default again.
- `pack_uvs` fails when Blender does not report FINISHED for the pack operator,
  instead of normalizing a layout nobody packed, and returns the UV state it
  found.
- Background render jobs check that a PNG frame is structurally complete (chunk
  checksums and a closing end marker), not just that it starts with the PNG
  signature. A truncated frame is re-rendered on resume and keeps the job from
  reporting completed.
- Cancelling a background render job on Windows no longer flashes a console
  window.
- Multiview receipt reads and writes retry transient Windows sharing conflicts
  for up to a second instead of 0.1 s.
- Render output settings work on Blender 5: `set_render_output`,
  `set_render_settings` and viewport capture select the media type before the
  format (multi-layer EXR was rejected), `color_depth` accepts Blender's native
  `16` and `32` (`16F` and `32F` stay as aliases), and the denoise GPU option
  and denoising pass use the property names Blender exposes. A value the host
  rejects now restores the previous output or denoise settings instead of
  leaving a half-applied batch. Blender 4.x, which has no media type, still
  takes the format directly.
- The main-thread dispatch budget is configurable instead of a fixed 30 s:
  `start_server(main_thread_timeout_ms=...)`,
  `BlenderServerOptions.main_thread_timeout_ms`, or
  `MESHY_DCC_BLENDER_MAIN_THREAD_TIMEOUT_MS` (explicit value, then the variable,
  then 30 s). It only applies to the dispatcher the adapter creates, and only to
  calls whose tool declares no `timeout_hint_secs`; a tool's own hint wins and
  the caller's deadline, which the host main-thread queue enforces, is not
  shortened or extended.

## 0.1.2 (2026-11-03)

- Rebuild with meshy-dcc-core 0.2.3 for the corrected macOS native wheel,
  launch target isolation and managed request/lifecycle integration.

## 0.1.1 (2026-10-28)

- `save_scene` reads the save back. It fails unless Blender returns `FINISHED`
  and the path Blender then reports for the scene is a regular, nonempty file
  with a fresh modification time, so a cancelled save no longer looks like a
  success because an older file sits at the path. The result's `filepath` is
  the verified file, and a failure reports `mutation_applied: null` without
  retrying.
- Rebuilt on meshy-dcc-core 0.2.2: security fixes in the MCP server (rmcp 2.1) and Python bindings (PyO3 0.29), and tool calls whose deadline passes before they start are no longer run.

## 0.1.0 (2026-10-19)

First Meshy release. Versions restart at 0.1.0 and are unrelated to the
adapter this one was forked from.

- Meshy-owned adapter:
  - Python package, extension id and environment variables are renamed to
    `meshy_dcc_blender` / `MESHY_DCC_BLENDER_*`;
  - the adapter builds against `meshy_dcc_core` 0.2.x;
  - it shows as "Meshy DCC" in Blender.
- `assemble_zip.py --core-wheel` bundles a local `meshy_dcc_core` wheel.
- A Blender launched by `meshy-dcc start-instance` advertises a
  consent-gated safe stop. It refuses to quit unless the request carries
  `discard_unsaved`, because Blender's dirty flag misses Python edits.
- `install --python` accepts a venv interpreter; it no longer follows the
  symlink out of the venv.
- Every tool declares its input schema. 42 tools (object transforms, scene,
  materials, lights, modifiers, collections, frame range, render farm)
  published only `{"type": "object"}`, so a caller had to read the script to
  learn that, say, `move_object` takes `name` while `rename_object` takes
  `object_name`. Their schemas now come from each script's signature and
  docstring.
- `delete_object`, `duplicate_object`, `move_object`, `rotate_object` and
  `scale_object` accept `object_name`, as the other object tools call it;
  `name` still works.
