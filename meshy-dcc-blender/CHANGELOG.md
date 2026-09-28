# Changelog

## Unreleased

- Meshy-owned adapter:
  - Python package, extension id and environment variables are renamed to
    `meshy_dcc_blender` / `MESHY_DCC_BLENDER_*`;
  - the adapter builds against `meshy_dcc_core` 0.2.x;
  - it shows as "Meshy DCC" in Blender.
- `assemble_zip.py --core-wheel` bundles a local `meshy_dcc_core` wheel.
- A Blender launched by `meshy-dcc start-instance` advertises a
  consent-gated safe stop. It refuses to quit unless the request carries
  `discard_unsaved`, because Blender's dirty flag misses Python edits.
