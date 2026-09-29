# Changelog

## 0.1.0 (unreleased)

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
