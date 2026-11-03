# Changelog

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
